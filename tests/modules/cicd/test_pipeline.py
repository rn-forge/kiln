"""The `ci.yml` pipeline for each archetype: plan, test, integration, release, docs."""

from __future__ import annotations
import pytest
import re
import subprocess
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.pins import load_pins
from rn_forge.kiln.modules.cicd.config import GENERATED_JOBS
from rn_forge.kiln.modules.core import cycle
from tests.conftest import requires
from tests.modules.cicd import workflows
from tests.modules.cicd.support import (
    CALL,
    KILN_DOCTOR_FULL_EXPRESSION,
    RELEASE_PERMISSIONS,
    UPSTREAM_PINS,
    _ci_jobs,
    _ci_tasks_text_of,
    _lib_jobs,
    _lib_root,
    _pypi_root,
    _release_steps,
    _rendered,
    _root,
    _with_ci,
)


PLAN_KEYS = (
    "release-order",
    "packages",
    "integration",
    "smoke",
    "suites",
    "pytest-args",
    "docs",
)


def test_python_lib_jobs_and_validate_steps(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    assert list(jobs) == [
        "validate",
        "dependency-review",
        "secret-scan",
        "plan",
        "test",
        "integration",
        "smoke",
        "suites",
        "sonar",
        "release",
        "verify-release",
        "docs",
        "checks-ok",
        "ci-ok",
    ]
    runs = [step.get("run") for step in jobs["validate"]["steps"]]  # type: ignore[attr-defined]
    for command in ("task setup", "task lint", "task ci:adapters", "task docs:build"):
        assert command in runs, command
    lint = next(s for s in jobs["validate"]["steps"] if s.get("run") == "task lint")  # type: ignore[attr-defined]
    assert lint["env"]["KILN_DOCTOR_FULL"] == KILN_DOCTOR_FULL_EXPRESSION
    no_sonar = list(_lib_jobs(tmp_path / "n", sonar=False))
    assert "sonar" not in no_sonar
    no_release = list(_lib_jobs(tmp_path / "r", release="none"))
    assert "release" not in no_release
    no_docs = _lib_jobs(tmp_path / "d", profile="none")
    assert "task docs:build" not in [s.get("run") for s in no_docs["validate"]["steps"]]  # type: ignore[attr-defined]


def test_plan_job(tmp_path: Path) -> None:
    plan = _lib_jobs(tmp_path)["plan"]
    assert plan["permissions"] == {"contents": "read", "actions": "read"}
    assert plan["outputs"] == {
        key: f"${{{{ steps.plan.outputs.{key} }}}}" for key in PLAN_KEYS
    }
    checkout = plan["steps"][0]  # type: ignore[index]
    assert checkout["with"]["fetch-depth"] == 0
    step = next(s for s in plan["steps"] if s.get("id") == "plan")  # type: ignore[attr-defined]
    assert step["run"] == 'task ci:plan >> "$GITHUB_OUTPUT"'
    assert set(step["env"]) == {"GH_TOKEN", "EVENT_NAME", "BASE"}
    assert step["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert step["env"]["EVENT_NAME"] == "${{ github.event_name }}"
    assert step["env"]["BASE"] == (
        "${{ github.event_name == 'pull_request' && "
        "github.event.pull_request.base.sha || '' }}"
    )


def test_test_job(tmp_path: Path) -> None:
    test = _lib_jobs(tmp_path)["test"]
    assert test["needs"] == ["validate", "plan"]
    assert test["if"] == (
        "${{ !cancelled() && needs.validate.result == 'success' && "
        "needs.plan.outputs.packages != '[]' }}"
    )
    assert test["strategy"] == {
        "fail-fast": False,
        "matrix": {"include": "${{ fromJSON(needs.plan.outputs.packages) }}"},
    }
    assert test["name"] == "test (${{ matrix.name }})"
    runs = [s.get("run") for s in test["steps"]]  # type: ignore[attr-defined]
    assert "task setup" in runs
    step = next(s for s in test["steps"] if s.get("run", "").startswith("task ci:test"))  # type: ignore[attr-defined]
    assert step["run"] == "task ci:test -- ${{ matrix.name }}"
    assert step["env"] == {
        "PACKAGE_DIR": "${{ matrix.dir }}",
        "PYTEST_ARGS": "${{ needs.plan.outputs.pytest-args }}",
    }


def test_sonar_waits_for_test(tmp_path: Path) -> None:
    sonar = _lib_jobs(tmp_path)["sonar"]
    assert sonar["needs"] == ["validate", "test", "integration", "smoke", "suites"]
    assert str(sonar["if"]).startswith(
        "${{ !cancelled() && !contains(needs.*.result, 'failure') && "
        "github.actor != 'dependabot[bot]' && ("
    )
    assert "head.repo.full_name == github.repository" in str(sonar["if"])


def test_other_archetypes_keep_the_plain_pipeline(tmp_path: Path) -> None:
    for archetype in ("python-app", "python-tool"):
        jobs = _ci_jobs(_root(tmp_path / archetype, archetype))
        assert list(jobs) == [
            "validate",
            "dependency-review",
            "secret-scan",
            "plan",
            "test",
            "integration",
            "smoke",
            "suites",
            "sonar",
            "release",
            "verify-release",
            "docs",
            "checks-ok",
            "ci-ok",
        ], archetype


def test_declared_jobs_follow_test(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    names = list(jobs)
    assert names[names.index("test") + 1 : names.index("test") + 4] == [
        "integration",
        "smoke",
        "suites",
    ]
    for name, key in (
        ("integration", "integration"),
        ("smoke", "smoke"),
        ("suites", "suites"),
    ):
        job = jobs[name]
        assert job["needs"] == ["validate", "plan"], name
        assert job["if"] == (
            "${{ !cancelled() && needs.validate.result == 'success' && "
            f"needs.plan.outputs.{key} != '[]' }}}}"
        ), name
        assert job["strategy"] == {  # type: ignore[comparison-overlap]
            "fail-fast": False,
            "matrix": {"include": f"${{{{ fromJSON(needs.plan.outputs.{key}) }}}}"},
        }, name


def test_integration_is_generated(tmp_path: Path) -> None:
    assert "integration" in GENERATED_JOBS
    extra = f'\n[[ci.jobs]]\nname = "integration"\nuses = "{CALL}"\n'
    root = _with_ci(_root(tmp_path, "python-lib"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_attest_step(tmp_path: Path) -> None:
    steps = _release_steps(_pypi_root(tmp_path / "pypi"))
    names = [step.get("name") for step in steps]
    index = names.index("Attest PyPI publish")
    assert names[index - 1] == "Generate provenance"
    assert names[index + 1] == "Publish releases"
    assert steps[index]["if"] == "steps.build.outputs.built != '0'"
    assert steps[index]["run"] == "task ci:release:sign"
    plain = _release_steps(_lib_root(tmp_path / "plain"))
    assert "Attest PyPI publish" not in [step.get("name") for step in plain]


def test_smoke_job_does_not_sync(tmp_path: Path) -> None:
    steps = _lib_jobs(tmp_path)["smoke"]["steps"]  # type: ignore[assignment]
    runs = [s.get("run") for s in steps]  # type: ignore[attr-defined]
    assert "task setup" not in runs
    step = steps[runs.index("task ci:smoke -- ${{ matrix.name }}")]  # type: ignore[index]
    assert step["env"] == {"EXTRA": "${{ matrix.extra }}"}


def test_suites_job(tmp_path: Path) -> None:
    job = _lib_jobs(tmp_path)["suites"]
    assert job["name"] == "suite (${{ matrix.name }})"
    steps = job["steps"]  # type: ignore[assignment]
    runs = [s.get("run") for s in steps]  # type: ignore[attr-defined]
    assert runs.index("task setup") < runs.index("task ci:suites")
    assert steps[runs.index("task ci:suites")]["env"] == {  # type: ignore[index]
        "SUITE_ARGS": "${{ matrix.args }}"
    }


def test_ci_ok_and_sonar_need_the_declared_jobs(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    assert jobs["sonar"]["needs"] == [
        "validate",
        "test",
        "integration",
        "smoke",
        "suites",
    ]
    assert {"integration", "smoke", "suites"} <= set(jobs["checks-ok"]["needs"])  # type: ignore[arg-type]


def _marker_steps(job: dict[str, object]) -> list[dict[str, object]]:
    return job["steps"][-2:]  # type: ignore[index,return-value]


def test_check_jobs_end_with_marker_steps(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    markers = {
        "test": "${{ matrix.name }}.test",
        "integration": "${{ matrix.marker }}",
        "smoke": "${{ matrix.marker }}",
    }
    for name, marker in markers.items():
        touch, upload = _marker_steps(jobs[name])
        assert touch["run"] == f'mkdir ok && touch "ok/{marker}"', name
        assert str(upload["uses"]).startswith("actions/upload-artifact@"), name
        assert upload["with"] == {  # type: ignore[comparison-overlap]
            "name": f"ok-{marker}",
            "path": "ok/",
            "retention-days": 1,
        }, name


def test_python_lib_release_job(tmp_path: Path) -> None:
    release = _lib_jobs(tmp_path)["release"]
    assert "strategy" not in release
    assert release["permissions"] == RELEASE_PERMISSIONS
    steps = release["steps"]  # type: ignore[assignment]
    assert str(steps[0]["uses"]).startswith("actions/checkout@")  # type: ignore[index]
    assert steps[1]["uses"] == "./.github/actions/setup"  # type: ignore[index]
    download = steps[2]  # type: ignore[index]
    assert str(download["uses"]).startswith("actions/download-artifact@")
    assert download["with"] == {
        "pattern": "ok-*",
        "merge-multiple": True,
        "path": "ok/",
    }
    env = {
        "GH_TOKEN": "${{ github.token }}",
        "SELECTED": "${{ needs.plan.outputs.release-order }}",
    }
    assert steps[3]["run"] == "task ci:release:build"  # type: ignore[index]
    assert steps[3]["env"] == env  # type: ignore[index]
    assert steps[5]["run"] == "task ci:release:publish"  # type: ignore[index]
    assert steps[5]["env"] == env  # type: ignore[index]
    assert len(steps) == 6  # type: ignore[arg-type]


def test_release_task_is_pykit_s_script(tmp_path: Path) -> None:
    tasks = _ci_tasks_text(tmp_path)["tasks"]
    script = "\n".join(
        "\n".join(tasks[name]["cmds"])  # type: ignore[index]
        for name in ("release:build", "release:publish")
    )
    for text in (
        "releasable ok",
        "release-publish",
        "{{.DEVOPS}}",
        "uv build",
        "uv version",
    ):
        assert text in script, text
    assert "uv run rn-forge-devops" not in script


def test_verify_release(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    job = jobs["verify-release"]
    assert job["needs"] == ["release"]
    assert job["if"] == (
        "${{ !cancelled() && needs.release.result == 'success' && "
        "github.event_name == 'push' && github.ref_name == 'main' }}"
    )
    steps = job["steps"]  # type: ignore[assignment]
    assert steps[0]["with"] == {  # type: ignore[index]
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    last = steps[-1]  # type: ignore[index]
    assert last["run"] == "task ci:verify-release"
    assert last["env"] == {
        "REPOSITORY_URL": "${{ github.server_url }}/${{ github.repository }}"
    }
    assert "verify-release" in jobs["ci-ok"]["needs"]  # type: ignore[operator]
    script = "\n".join(
        _ci_tasks_text(tmp_path)["tasks"]["verify-release"]["cmds"]  # type: ignore[index]
    )
    assert script == "{{.DEVOPS}} verify-release --source git {{.CLI_ARGS}}"


def _ci_tasks_text(tmp_path: Path) -> dict[str, object]:
    return _ci_tasks_text_of(_root(tmp_path / "tasks", "python-lib"))


def test_artifact_actions_are_pinned() -> None:
    pins = load_pins()
    assert pins["upload-artifact"] == {
        "uses": "actions/upload-artifact",
        "sha": "cf430e030ddbb5b0abf93d22962f4752f3646cd9",
        "version": "v7.0.2",
    }
    assert pins["download-artifact"] == {
        "uses": "actions/download-artifact",
        "sha": "9000827ccba6bdab643e8b6fd33ac0654aef8333",
        "version": "v8.0.2",
    }
    assert {"upload-artifact", "download-artifact"} <= set(UPSTREAM_PINS)


def test_other_archetypes_keep_the_per_package_release_steps(
    tmp_path: Path,
) -> None:
    for archetype in ("python-app", "python-tool"):
        steps = _release_steps(_root(tmp_path / archetype, archetype))
        names = [s.get("name") for s in steps]
        assert "Generate provenance" in names
        assert "Publish GitHub Release" in names


def test_test_passes_the_matrix_dir_through_env(
    tmp_path: Path,
) -> None:
    jobs = _lib_jobs(tmp_path)
    for name, task in (("test", "ci:test"),):
        assert jobs[name]["name"] == f"{name} (${{{{ matrix.name }}}})"
        step = next(
            s
            for s in jobs[name]["steps"]
            if s.get("run", "").startswith(f"task {task}")  # type: ignore[attr-defined]
        )
        assert step["run"] == f"task {task} -- ${{{{ matrix.name }}}}"
        assert step["env"]["PACKAGE_DIR"] == "${{ matrix.dir }}"


@requires("actionlint")
def test_actionlint_passes_on_the_libs_fixture(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            '["packages/alpha", "packages/beta"]', '["libs/alpha"]'
        ),
        encoding="utf-8",
    )
    cycle.apply(root, home=tmp_path / "home")
    result = subprocess.run(
        ["actionlint", ".github/workflows/ci.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_python_lib_docs_job(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    names = list(jobs)
    assert names[names.index("release") :] == [
        "release",
        "verify-release",
        "docs",
        "checks-ok",
        "ci-ok",
    ]
    docs = jobs["docs"]
    assert docs["needs"] == ["checks-ok", "plan", "release", "verify-release"]
    assert docs["if"] == (
        "${{ !cancelled() && needs.checks-ok.result == 'success' && "
        "!contains(needs.*.result, 'failure') && "
        "!contains(needs.*.result, 'cancelled') && "
        "needs.plan.outputs.docs == 'true' && "
        "github.event_name == 'push' && github.ref_name == 'main' }}"
    )
    assert docs["concurrency"] == {"group": "pages", "cancel-in-progress": False}
    assert docs["permissions"] == {
        "contents": "write",
        "pages": "write",
        "id-token": "write",
    }
    steps = docs["steps"]  # type: ignore[assignment]
    assert str(steps[0]["uses"]).startswith("actions/checkout@")  # type: ignore[index]
    assert steps[0]["with"] == {  # type: ignore[index]
        "fetch-depth": 0,
        "persist-credentials": True,
    }
    assert steps[1]["uses"] == "./.github/actions/setup"  # type: ignore[index]
    publish = next(s for s in steps if s.get("run") == "task ci:docs:publish")  # type: ignore[attr-defined]
    assert publish["env"] == {"SITE_DIR": "${{ runner.temp }}/site"}
    uses = [str(s.get("uses", "")) for s in steps]  # type: ignore[attr-defined]
    upload = next(u for u in uses if u.startswith("actions/upload-pages-artifact@"))
    deploy = next(u for u in uses if u.startswith("actions/deploy-pages@"))
    assert uses.index(upload) < uses.index(deploy)
    assert "docs" in jobs["ci-ok"]["needs"]  # type: ignore[operator]
    assert "docs" not in _lib_jobs(tmp_path / "n", profile="none")
    no_release = _lib_jobs(tmp_path / "r", release="none")
    assert no_release["docs"]["needs"] == ["checks-ok", "plan"]
    assert "needs.release" not in str(no_release["docs"]["if"])


def test_python_lib_renders_no_docs_yml(tmp_path: Path) -> None:
    rendered = _rendered(_root(tmp_path, "python-lib"))
    assert ".github/workflows/docs.yml" not in rendered
    assert ".github/workflows/ci.yml" in rendered


def test_other_archetypes_deploy_docs_from_ci(
    tmp_path: Path,
) -> None:
    for archetype in ("python-app", "python-tool"):
        rendered = _rendered(_root(tmp_path / archetype, archetype))
        assert ".github/workflows/docs.yml" not in rendered, archetype
        assert "docs" in workflows.jobs(rendered), archetype


@requires("actionlint")
def test_actionlint_passes_on_the_docs_job(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    cycle.apply(root, home=tmp_path / "home")
    result = subprocess.run(
        ["actionlint", ".github/workflows/ci.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


RELEASE_IF = (
    "${{ !cancelled() && needs.checks-ok.result == 'success' && "
    "needs.plan.outputs.release-order != '[]' && "
    "github.event_name == 'push' && github.ref == 'refs/heads/main'%s }}"
)


def test_release_needs_every_check_and_sonar(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    assert jobs["release"]["needs"] == ["plan", "checks-ok"]
    assert jobs["checks-ok"]["needs"] == [
        "validate",
        "dependency-review",
        "plan",
        "test",
        "integration",
        "smoke",
        "suites",
        "sonar",
        "secret-scan",
    ]


def test_release_runs_on_a_default_branch_push_only(tmp_path: Path) -> None:
    release = _lib_jobs(tmp_path)["release"]
    assert release["if"] == RELEASE_IF % ""
    assert "pull_request" not in str(release["if"])
    assert "workflow_dispatch" not in str(release["if"])


def test_release_waits_on_sonar_only_where_sonar_renders(
    tmp_path: Path,
) -> None:
    jobs = _lib_jobs(tmp_path, sonar=False)
    release = jobs["release"]
    assert release["needs"] == ["plan", "checks-ok"]
    assert "sonar" not in jobs["checks-ok"]["needs"]  # type: ignore[operator]
    assert release["if"] == RELEASE_IF % ""
    assert "sonar" not in str(release)


def test_release_has_no_publish_switch(tmp_path: Path) -> None:
    text = _rendered(_root(tmp_path, "python-lib"))[".github/workflows/ci.yml"]
    assert "PUBLISH" not in text
    tasks = _ci_tasks_text(tmp_path)["tasks"]
    script = "\n".join(
        "\n".join(tasks[name]["cmds"])  # type: ignore[index]
        for name in ("release:build", "release:publish")
    )
    assert "PUBLISH" not in script
    assert "release-publish" in script


def test_smoke_takes_an_empty_extra_row_unchanged(tmp_path: Path) -> None:
    smoke = _lib_jobs(tmp_path)["smoke"]
    assert smoke["strategy"]["matrix"] == {  # type: ignore[index]
        "include": "${{ fromJSON(needs.plan.outputs.smoke) }}"
    }
    row = {"name": "alpha", "extra": "", "marker": "alpha.smoke"}
    steps = smoke["steps"]  # type: ignore[assignment]
    command = "task ci:smoke -- ${{ matrix.name }}"
    run = next(s for s in steps if s.get("run") == command)  # type: ignore[attr-defined]
    assert run["env"] == {"EXTRA": "${{ matrix.extra }}"}
    # Every key the job reads from the matrix is on the empty-extra row.
    used = set(re.findall(r"matrix\.(\w+)", str(smoke)))
    assert used <= set(row)


def test_ci_ok_needs_every_job_and_tolerates_a_skipped_release(
    tmp_path: Path,
) -> None:
    jobs = _lib_jobs(tmp_path)
    ci_ok = jobs["ci-ok"]
    covered = {*jobs["checks-ok"]["needs"], *ci_ok["needs"]}  # type: ignore[misc]
    assert covered == set(jobs) - {"ci-ok"}
    (step,) = ci_ok["steps"]  # type: ignore[misc]
    failed = "contains(needs.*.result, 'failure')"
    cancelled = "contains(needs.*.result, 'cancelled')"
    assert step["if"] == f"{failed} || {cancelled}"


@pytest.mark.parametrize("release", ["tag-exists", "pypi"])
@requires("actionlint")
def test_actionlint_passes_on_the_python_lib_workflows(
    tmp_path: Path, release: str
) -> None:
    for name, kwargs in (("on", {}), ("off", {"sonar": False})):
        root = _root(tmp_path / name, "python-lib", release=release, **kwargs)  # type: ignore[arg-type]
        cycle.apply(root, home=tmp_path / name / "home")
        result = subprocess.run(
            ["actionlint", ".github/workflows/ci.yml"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, name + result.stdout + result.stderr
