"""S4.3.4 — the `cicd` module's artifacts: workflows, the setup action, Sonar.

Also proves the five properties every F4.3 story owes its module
(`docs/specs/epics/E4-generator/F4.3-concern-modules.md`).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from rn_forge.commons.exceptions import AppException
from rn_forge.tooling.generation import Action, ArtifactKind

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd import CICD
from rn_forge.kiln.modules.cicd.artifacts import load_pins
from rn_forge.kiln.modules.core import cycle

ARCHETYPES = ("python-app", "python-tool", "python-lib")

CI_KEYS = (
    ".github/actions/setup/action.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/docs.yml",
    "sonar-project.properties",
)
WORKFLOWS = (".github/workflows/ci.yml", ".github/workflows/docs.yml")

CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "{archetype}"

[docs]
profile = "{profile}"

[ci]
provider = "{provider}"
sonar = {sonar}
release = "{release}"
"""

PACKAGES = """
[archetype."python-lib"]
packages = ["packages/alpha", "packages/beta"]
"""


def _root(
    tmp_path: Path,
    archetype: str = "python-tool",
    profile: str = "mkdocs",
    sonar: bool = True,
    release: str = "tag-exists",
    provider: str = "github",
) -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    text = CONFIG.format(
        archetype=archetype,
        profile=profile,
        sonar=str(sonar).lower(),
        release=release,
        provider=provider,
    )
    if archetype == "python-lib":
        text += PACKAGES
    config.write_text(text, encoding="utf-8")
    return tmp_path


def _rendered(root: Path) -> dict[str, str]:
    return {a.path: a.content for a in CICD.artifacts(KilnConfig.load(root), root)}


def _actions(root: Path, tmp_path: Path) -> dict[str, Action]:
    return {
        change.key: change.action
        for change in cycle.plan(root, home=tmp_path / "home").changes
    }


def _codes(root: Path) -> list[str]:
    return sorted(f.code for f in CICD.checks(KilnConfig.load(root), root))


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_4_property1_renders_exactly_the_module_s_template_inventory_rows(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    artifacts = CICD.artifacts(KilnConfig.load(root), root)
    assert [(a.path, a.kind) for a in artifacts] == [
        (path, ArtifactKind.MANAGED) for path in CI_KEYS
    ]


def test_s4_3_4_property1_without_mkdocs_or_sonar_renders_two_rows(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, profile="none", sonar=False)
    assert list(_rendered(root)) == list(CI_KEYS[:2])


def test_s4_3_4_property1_ado_is_reserved(tmp_path: Path) -> None:
    root = _root(tmp_path, provider="ado")
    with pytest.raises(AppException, match="E8"):
        _rendered(root)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_4_property2_into_an_empty_directory_only_creates(
    tmp_path: Path, archetype: str
) -> None:
    actions = _actions(_root(tmp_path, archetype), tmp_path)
    assert {actions[key] for key in CI_KEYS} == {Action.CREATE}


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_4_property3_a_second_apply_is_unchanged(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    actions = _actions(root, tmp_path)
    assert {actions[key] for key in CI_KEYS} == {Action.UNCHANGED}


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_4_property5_checks_pass_on_the_rendered_output(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    assert _codes(root) == []


def test_s4_3_4_property5_entrypoint_fails_on_a_direct_uv_call(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    ci = root / ".github" / "workflows" / "ci.yml"
    ci.write_text(
        ci.read_text(encoding="utf-8").replace("run: task setup", "run: uv sync"),
        encoding="utf-8",
    )
    assert "ci.entrypoint" in _codes(root)


@pytest.mark.parametrize("archetype", ARCHETYPES)
@pytest.mark.parametrize("sonar", [True, False])
def test_s4_3_4_1_actionlint_passes_on_every_rendered_workflow(
    tmp_path: Path, archetype: str, sonar: bool
) -> None:
    if shutil.which("actionlint") is None:
        pytest.skip("actionlint is not on PATH")
    root = _root(tmp_path, archetype, sonar=sonar)
    cycle.apply(root, home=tmp_path / "home")
    result = subprocess.run(
        ["actionlint", *WORKFLOWS],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_s4_3_4_2_ci_pins_passes_on_the_rendered_output(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    cycle.apply(root, home=tmp_path / "home")
    assert not [c for c in _codes(root) if c.startswith("ci.")]


def test_s4_3_4_3_sonar_off_renders_no_sonar_job_and_release_needs_validate(
    tmp_path: Path,
) -> None:
    on = _rendered(_root(tmp_path / "on"))
    off = _rendered(_root(tmp_path / "off", sonar=False))
    assert "sonar-project.properties" not in off
    jobs = yaml.safe_load(off[".github/workflows/ci.yml"])["jobs"]
    assert set(jobs) == {"validate", "release", "ci-ok"}
    assert jobs["release"]["needs"] == ["validate"]
    assert (
        "sonar"
        not in off[".github/workflows/ci.yml"]
        .split("jobs:", 1)[1]
        .split("release:", 1)[0]
    )
    # Everything else keeps its bytes.
    on_ci = on[".github/workflows/ci.yml"]
    sonar_job = on_ci[on_ci.index("\n  sonar:") : on_ci.index("\n  release:")]
    expected = (
        on_ci.replace(sonar_job, "")
        .replace("needs: [validate, sonar]", "needs: [validate]")
        .replace("needs: [validate, sonar, release]", "needs: [validate, release]")
    )
    assert off[".github/workflows/ci.yml"] == expected


def test_s4_3_4_3_release_none_renders_no_release_job(tmp_path: Path) -> None:
    rendered = _rendered(_root(tmp_path, release="none"))
    jobs = yaml.safe_load(rendered[".github/workflows/ci.yml"])["jobs"]
    assert set(jobs) == {"validate", "sonar", "ci-ok"}


def test_s4_3_4_4_ci_entrypoint_passes_on_the_rendered_workflows(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    assert "ci.entrypoint" not in _codes(root)


def test_s4_3_4_4_ci_entrypoint_fails_on_a_fixture_calling_uv(repo) -> None:
    root = repo(
        **{
            ".github__workflows__ci.yml": (
                "jobs:\n  a:\n    permissions: {}\n    steps:\n      - run: uv sync\n"
            )
        }
    )
    assert _codes(root) == ["ci.entrypoint"]


WEB_CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "{archetype}"

[docs]
profile = "none"

[archetype."{archetype}"]
backend = "fastapi"
{extra}
"""


def _web_root(tmp_path: Path, archetype: str, extra: str = "") -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        WEB_CONFIG.format(archetype=archetype, extra=extra), encoding="utf-8"
    )
    return tmp_path


def test_s5_1_2_only_python_web_app_s_setup_action_sets_up_pnpm_and_node(
    tmp_path: Path,
) -> None:
    api = _rendered(_web_root(tmp_path / "api", "python-web-api"))
    app = _rendered(
        _web_root(tmp_path / "app", "python-web-app", extra='frontend = "angular"')
    )
    api_action = api[".github/actions/setup/action.yml"]
    app_action = app[".github/actions/setup/action.yml"]
    assert "pnpm/action-setup" not in api_action
    assert "actions/setup-node" not in api_action
    assert "pnpm/action-setup" in app_action
    assert "actions/setup-node" in app_action
    assert "cache: pnpm" in app_action


def test_s5_1_2_sonar_properties_web_api_uses_api_dir(tmp_path: Path) -> None:
    rendered = _rendered(_web_root(tmp_path, "python-web-api"))
    properties = rendered["sonar-project.properties"]
    assert "sonar.sources=apps/api/src" in properties
    assert "sonar.tests=apps/api/tests" in properties


def test_s5_1_2_sonar_properties_web_app_adds_web_dir_to_sources(
    tmp_path: Path,
) -> None:
    rendered = _rendered(
        _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    )
    properties = rendered["sonar-project.properties"]
    assert "sonar.sources=apps/api/src,apps/web/src" in properties
    assert "sonar.tests=apps/api/tests" in properties


def test_s5_1_2_ci_pins_passes_on_the_web_app_setup_action(tmp_path: Path) -> None:
    root = _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    cycle.apply(root, home=tmp_path / "home")
    assert not [c for c in _codes(root) if c.startswith("ci.")]


@pytest.mark.parametrize("sonar", [True, False])
def test_s5_1_2_actionlint_passes_on_web_app_workflows(
    tmp_path: Path, sonar: bool
) -> None:
    if shutil.which("actionlint") is None:
        pytest.skip("actionlint is not on PATH")
    root = _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    text = root.joinpath(".rn-forge/kiln/config.toml").read_text(encoding="utf-8")
    text = text.replace(
        "[repository]", f"[ci]\nsonar = {str(sonar).lower()}\n\n[repository]"
    )
    root.joinpath(".rn-forge/kiln/config.toml").write_text(text, encoding="utf-8")
    cycle.apply(root, home=tmp_path / "home")
    result = subprocess.run(
        ["actionlint", ".github/workflows/ci.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


SETUP_ACTION = "./.github/actions/setup"


def _assert_checks_out_first(workflow: str, where: str) -> None:
    jobs = yaml.safe_load(workflow)["jobs"]
    for name, job in jobs.items():
        steps = job["steps"]
        for index, step in enumerate(steps):
            if step.get("uses") != SETUP_ACTION:
                continue
            assert index > 0, f"{where}: {name} sets up before checking out"
            previous = steps[index - 1]
            assert str(previous.get("uses", "")).startswith("actions/checkout@"), (
                f"{where}: {name}'s setup step does not follow a checkout"
            )
            if name == "sonar":
                assert previous.get("with", {}).get("fetch-depth") == 0, where


def test_s4_4_5_1_every_job_checks_out_before_the_setup_action(
    tmp_path: Path,
) -> None:
    roots = [_root(tmp_path / archetype, archetype) for archetype in ARCHETYPES] + [
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"'),
    ]
    for root in roots:
        for path, content in _rendered(root).items():
            if path in WORKFLOWS:
                _assert_checks_out_first(content, f"{root.name}:{path}")


def test_s4_4_5_2_setup_action_has_no_checkout(tmp_path: Path) -> None:
    action = _rendered(_root(tmp_path))[".github/actions/setup/action.yml"]
    assert "actions/checkout@" not in action
    assert "fetch-depth" not in action
    parsed = yaml.safe_load(action)
    assert "fetch-depth" not in parsed["inputs"]


def test_s4_4_5_3_kiln_and_rendered_repos_check_out_first(
    rendered: Callable[[str], Path],
) -> None:
    repo = Path(__file__).resolve().parents[3]
    roots = [repo, *(rendered(archetype) for archetype in ARCHETYPES)]
    for root in roots:
        for workflow in sorted((root / ".github" / "workflows").glob("*.yml")):
            _assert_checks_out_first(
                workflow.read_text(encoding="utf-8"), f"{root.name}/{workflow.name}"
            )


def test_s6_3_1_every_job_has_a_timeout(tmp_path: Path) -> None:
    roots = [_root(tmp_path / archetype, archetype) for archetype in ARCHETYPES] + [
        _web_root(tmp_path / "api", "python-web-api"),
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"'),
    ]
    for root in roots:
        workflows = {
            path: content
            for path, content in _rendered(root).items()
            if path.startswith(".github/workflows/")
        }
        assert workflows
        for path, content in workflows.items():
            for name, job in yaml.safe_load(content)["jobs"].items():
                timeout = job.get("timeout-minutes")
                assert isinstance(timeout, int), f"{root.name}:{path}:{name}"


def _ci_ok_roots(tmp_path: Path) -> list[Path]:
    return [_root(tmp_path / archetype, archetype) for archetype in ARCHETYPES] + [
        _root(tmp_path / "nosonar", sonar=False),
        _root(tmp_path / "norelease", release="none"),
        _web_root(tmp_path / "api", "python-web-api"),
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"'),
    ]


def _ci_jobs(root: Path) -> dict[str, dict[str, object]]:
    return yaml.safe_load(_rendered(root)[".github/workflows/ci.yml"])["jobs"]


def test_s6_3_2_ci_ok_needs_every_other_job(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        jobs = _ci_jobs(root)
        assert list(jobs)[-1] == "ci-ok", root.name
        assert set(jobs["ci-ok"]["needs"]) == set(jobs) - {"ci-ok"}, root.name  # type: ignore[arg-type]
        assert jobs["ci-ok"]["if"] == "always()", root.name


def test_s6_3_2_ci_ok_has_no_permissions(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        assert _ci_jobs(root)["ci-ok"]["permissions"] == {}, root.name


def test_s6_3_2_ci_ok_fails_on_failure_or_cancel(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        steps = _ci_jobs(root)["ci-ok"]["steps"]
        assert len(steps) == 1  # type: ignore[arg-type]
        step = steps[0]  # type: ignore[index]
        assert "contains(needs.*.result, 'failure')" in step["if"]
        assert "contains(needs.*.result, 'cancelled')" in step["if"]
        assert step["run"] == "exit 1"


def _sonar_steps(root: Path) -> list[dict[str, object]]:
    return _ci_jobs(root)["sonar"]["steps"]  # type: ignore[return-value]


def test_s6_3_3_scan_passes_the_target_branch_arg(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        if root.name == "nosonar":
            continue
        steps = _sonar_steps(root)
        names = [step["name"] for step in steps]
        target = next(i for i, step in enumerate(steps) if step.get("id") == "target")
        assert target < names.index("Test with coverage"), root.name
        scan = next(step for step in steps if step["name"] == "SonarQube scan")
        assert (
            "${{ steps.target.outputs.branch-arg }}" in scan["with"]["args"]  # type: ignore[index]
        ), root.name


def test_s6_3_3_ref_text_reaches_run_only_through_env(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        if root.name == "nosonar":
            continue
        for step in _sonar_steps(root):
            run = str(step.get("run", ""))
            assert "github.ref_name" not in run, root.name
            assert "github.head_ref" not in run, root.name


def _release_steps(root: Path) -> list[dict[str, object]]:
    return _ci_jobs(root)["release"]["steps"]  # type: ignore[return-value]


def _release_roots(tmp_path: Path) -> list[Path]:
    return [
        _root(tmp_path / archetype, archetype)
        for archetype in ARCHETYPES
        if archetype != "python-lib"
    ]


def _step_index(steps: list[dict[str, object]], name: str) -> int:
    return next(i for i, step in enumerate(steps) if step.get("name") == name)


def test_s6_3_4_check_step_outputs_the_tag_state(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        check = next(step for step in steps if step.get("id") == "check")
        run = str(check["run"])
        for output in ("should-release=", "tagged=", "draft="):
            assert f"{output}" in run, root.name
            assert "$GITHUB_OUTPUT" in run


def test_s6_3_4_checkout_of_the_tag_precedes_build(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        index = _step_index(steps, "Check out the tagged source")
        assert steps[index]["if"] == "steps.check.outputs.tagged == 'true'"
        check = next(i for i, s in enumerate(steps) if s.get("id") == "check")
        assert check < index < _step_index(steps, "Build"), root.name


def test_s6_3_4_draft_is_deleted_before_publish(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        index = _step_index(steps, "Delete the leftover draft")
        assert steps[index]["if"] == "steps.check.outputs.draft == 'true'"
        assert (
            _step_index(steps, "Build")
            < index
            < _step_index(steps, "Publish GitHub Release")
        ), root.name


def test_s6_3_4_publish_targets_the_source_commit(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        publish = steps[_step_index(steps, "Publish GitHub Release")]
        assert (
            publish["with"]["target_commitish"]  # type: ignore[index]
            == "${{ steps.source.outputs.sha }}"
        )
        assert any(step.get("id") == "source" for step in steps)


def test_s6_3_6_release_uploads_wheels_and_sdists_only(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        publish = steps[_step_index(steps, "Publish GitHub Release")]
        files = publish["with"]["files"]  # type: ignore[index]
        assert files == "dist/*.whl\ndist/*.tar.gz\n", root.name
        assert "dist/*" not in files.splitlines(), root.name


UPSTREAM_PINS = {
    "setup-uv": ("c18668ad3cf93ea998bef934396af7bb5c839dc7", "v10.2.0"),
    "sonarqube-scan": ("d209202bc7d53ff1cc128f7f907dac145c9d6ae9", "v8.3.0"),
    "deploy-pages": ("368f82528645a54fb793d4d04e342629a3f51346", "v5.0.1"),
    "upload-artifact": ("cf430e030ddbb5b0abf93d22962f4752f3646cd9", "v7.0.2"),
    "download-artifact": ("9000827ccba6bdab643e8b6fd33ac0654aef8333", "v8.0.2"),
    "pnpm-setup": ("0ebf47130e4866e96fce0953f49152a61190b271", "v6.0.9"),
    "setup-node": ("820762786026740c76f36085b0efc47a31fe5020", "v7.0.0"),
}


def test_s6_3_5_setup_uv_enables_the_cache(tmp_path: Path) -> None:
    action = yaml.safe_load(
        _rendered(_root(tmp_path))[".github/actions/setup/action.yml"]
    )
    install = next(
        step for step in action["runs"]["steps"] if step["name"] == "Install uv"
    )
    assert install["with"]["enable-cache"] is True


def test_s6_3_5_pins_match_the_upstream_versions() -> None:
    pins_file = Path(sys.modules[CICD.__module__].__file__ or "").parent / "pins.toml"
    pins = tomllib.loads(pins_file.read_text(encoding="utf-8"))
    for key, (sha, version) in UPSTREAM_PINS.items():
        assert (pins[key]["sha"], pins[key]["version"]) == (sha, version), key


KILN_DOCTOR_FULL_EXPRESSION = (
    "${{ ((github.event_name == 'push' && github.ref_name == "
    "github.event.repository.default_branch) || "
    "github.event_name == 'workflow_dispatch') && '1' || '' }}"
)


def test_s4_6_4_2_ci_sets_the_variable_on_default_branch_pushes(
    tmp_path: Path,
) -> None:
    for archetype in ARCHETYPES:
        root = _root(tmp_path / archetype, archetype)
        jobs = yaml.safe_load(_rendered(root)[".github/workflows/ci.yml"])["jobs"]
        step = next(s for s in jobs["validate"]["steps"] if s["name"] == "Validate")
        assert step["run"] == (
            "task lint" if archetype == "python-lib" else "task validate"
        )
        assert step["env"]["KILN_DOCTOR_FULL"] == KILN_DOCTOR_FULL_EXPRESSION, archetype


def _lib_jobs(tmp_path: Path, **kwargs: object) -> dict[str, dict[str, object]]:
    return _ci_jobs(_root(tmp_path, "python-lib", **kwargs))  # type: ignore[arg-type]


PLAN_KEYS = (
    "release-order",
    "packages",
    "postgres",
    "smoke",
    "suites",
    "pytest-args",
    "cov-args",
    "test-paths",
    "sonar-sources",
    "sonar-tests",
    "sonar",
    "docs",
)


def test_s6_4_2_4_python_lib_jobs_and_validate_steps(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    assert list(jobs) == [
        "validate",
        "plan",
        "verify",
        "postgres",
        "smoke",
        "suites",
        "sonar",
        "release",
        "external-install",
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


def test_s6_4_2_5_plan_job(tmp_path: Path) -> None:
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


def test_s6_4_2_6_verify_job(tmp_path: Path) -> None:
    verify = _lib_jobs(tmp_path)["verify"]
    assert verify["needs"] == ["validate", "plan"]
    assert verify["if"] == (
        "${{ !cancelled() && needs.validate.result == 'success' && "
        "needs.plan.outputs.packages != '[]' }}"
    )
    assert verify["strategy"] == {
        "fail-fast": False,
        "matrix": {"include": "${{ fromJSON(needs.plan.outputs.packages) }}"},
    }
    assert verify["name"] == "verify (${{ matrix.name }})"
    runs = [s.get("run") for s in verify["steps"]]  # type: ignore[attr-defined]
    assert "task setup" in runs
    step = next(
        s for s in verify["steps"] if s.get("run", "").startswith("task ci:verify")
    )  # type: ignore[attr-defined]
    assert step["run"] == "task ci:verify -- ${{ matrix.name }}"
    assert step["env"] == {
        "PACKAGE_DIR": "${{ matrix.dir }}",
        "PYTEST_ARGS": "${{ needs.plan.outputs.pytest-args }}",
    }


def test_s6_4_2_6_sonar_waits_for_verify(tmp_path: Path) -> None:
    sonar = _lib_jobs(tmp_path)["sonar"]
    assert sonar["needs"] == ["validate", "verify", "postgres", "smoke"]
    assert str(sonar["if"]).startswith(
        "${{ !cancelled() && !contains(needs.*.result, 'failure') && ("
    )
    assert "head.repo.full_name == github.repository" in str(sonar["if"])


def test_s6_4_2_8_other_archetypes_keep_the_plain_pipeline(tmp_path: Path) -> None:
    for archetype in ("python-app", "python-tool"):
        jobs = _ci_jobs(_root(tmp_path / archetype, archetype))
        assert list(jobs) == ["validate", "sonar", "release", "ci-ok"], archetype


def test_s6_4_3_2_declared_jobs_follow_verify(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    names = list(jobs)
    assert names[names.index("verify") + 1 : names.index("verify") + 4] == [
        "postgres",
        "smoke",
        "suites",
    ]
    for name, key in (
        ("postgres", "postgres"),
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


def test_s6_4_3_3_postgres_job(tmp_path: Path) -> None:
    job = _lib_jobs(tmp_path)["postgres"]
    assert job["services"] == {
        "postgres": {
            "image": "postgres:17",
            "env": {
                "POSTGRES_USER": "ci",
                "POSTGRES_PASSWORD": "ci",
                "POSTGRES_DB": "ci",
            },
            "ports": ["5432:5432"],
            "options": (
                '--health-cmd "pg_isready -U ci" --health-interval 5s '
                "--health-timeout 5s --health-retries 10"
            ),
        }
    }
    steps = job["steps"]  # type: ignore[assignment]
    runs = [s.get("run") for s in steps]  # type: ignore[attr-defined]
    assert runs.index("task setup") < runs.index(
        "task ci:postgres -- ${{ matrix.name }}"
    )
    step = steps[runs.index("task ci:postgres -- ${{ matrix.name }}")]  # type: ignore[index]
    assert step["env"] == {
        "PACKAGE_DIR": "${{ matrix.dir }}",
        "DSN_VAR": "${{ matrix.env }}",
        "PYTEST_ARGS": "${{ needs.plan.outputs.pytest-args }}",
    }


def test_s6_4_3_4_smoke_job_does_not_sync(tmp_path: Path) -> None:
    steps = _lib_jobs(tmp_path)["smoke"]["steps"]  # type: ignore[assignment]
    runs = [s.get("run") for s in steps]  # type: ignore[attr-defined]
    assert "task setup" not in runs
    step = steps[runs.index("task ci:smoke -- ${{ matrix.name }}")]  # type: ignore[index]
    assert step["env"] == {"EXTRA": "${{ matrix.extra }}"}


def test_s6_4_3_5_suites_job(tmp_path: Path) -> None:
    job = _lib_jobs(tmp_path)["suites"]
    assert job["name"] == "suite (${{ matrix.name }})"
    steps = job["steps"]  # type: ignore[assignment]
    runs = [s.get("run") for s in steps]  # type: ignore[attr-defined]
    assert runs.index("task setup") < runs.index("task ci:suite")
    assert steps[runs.index("task ci:suite")]["env"] == {  # type: ignore[index]
        "SUITE_ARGS": "${{ matrix.args }}"
    }


def test_s6_4_3_6_ci_ok_and_sonar_need_the_declared_jobs(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    assert jobs["sonar"]["needs"] == ["validate", "verify", "postgres", "smoke"]
    assert set(jobs["ci-ok"]["needs"]) == set(jobs) - {"ci-ok"}  # type: ignore[arg-type]
    assert {"postgres", "smoke", "suites"} <= set(jobs["ci-ok"]["needs"])  # type: ignore[arg-type]


def _marker_steps(job: dict[str, object]) -> list[dict[str, object]]:
    return job["steps"][-2:]  # type: ignore[index,return-value]


def test_s6_4_4_1_check_jobs_end_with_marker_steps(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    markers = {
        "verify": "${{ matrix.name }}.verify",
        "postgres": "${{ matrix.name }}.postgres",
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


def test_s6_4_4_2_python_lib_release_job(tmp_path: Path) -> None:
    release = _lib_jobs(tmp_path)["release"]
    assert "strategy" not in release
    assert release["needs"] == ["validate", "plan", "verify", "postgres", "smoke"]
    assert release["if"] == (
        "${{ !cancelled() && needs.validate.result == 'success' && "
        "needs.plan.outputs.release-order != '[]' }}"
    )
    assert release["permissions"] == {"contents": "write"}
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
    assert steps[3]["run"] == "task ci:release"  # type: ignore[index]
    assert steps[3]["env"] == {  # type: ignore[index]
        "GH_TOKEN": "${{ github.token }}",
        "PUBLISH": "${{ github.event_name == 'push' && github.ref_name == 'main' }}",
        "SELECTED": "${{ needs.plan.outputs.release-order }}",
    }
    assert len(steps) == 4  # type: ignore[arg-type]


def test_s6_4_4_3_release_task_is_pykit_s_script(tmp_path: Path) -> None:
    script = "\n".join(
        _ci_tasks_text(tmp_path)["tasks"]["release"]["cmds"]  # type: ignore[index]
    )
    for text in (
        "releasable ok",
        "--verify-tag",
        "gh release delete",
        "{{.DEVOPS}}",
        "uv build",
        "uv version",
    ):
        assert text in script, text
    assert "uv run rn-forge-devops" not in script


def test_s6_4_4_4_external_install(tmp_path: Path) -> None:
    jobs = _lib_jobs(tmp_path)
    job = jobs["external-install"]
    assert job["needs"] == ["release"]
    assert job["if"] == (
        "${{ !cancelled() && needs.release.result == 'success' && "
        "github.event_name == 'push' && github.ref_name == 'main' }}"
    )
    steps = job["steps"]  # type: ignore[assignment]
    assert steps[0]["with"] == {"fetch-depth": 0}  # type: ignore[index]
    last = steps[-1]  # type: ignore[index]
    assert last["run"] == "task ci:external-install"
    assert last["env"] == {
        "REPOSITORY_URL": "${{ github.server_url }}/${{ github.repository }}"
    }
    assert "external-install" in jobs["ci-ok"]["needs"]  # type: ignore[operator]
    script = "\n".join(
        _ci_tasks_text(tmp_path)["tasks"]["external-install"]["cmds"]  # type: ignore[index]
    )
    assert "{{.DEVOPS}} released" in script
    assert "$REPOSITORY_URL" in script


def _ci_tasks_text(tmp_path: Path) -> dict[str, object]:
    root = _root(tmp_path / "tasks", "python-lib")
    from rn_forge.kiln.modules.tasks import TASKS

    rendered = {a.path: a.content for a in TASKS.artifacts(KilnConfig.load(root), root)}
    return yaml.safe_load(rendered["tasks/ci.yml"])


def test_s6_4_4_5_artifact_actions_are_pinned() -> None:
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


def test_s6_4_4_6_other_archetypes_keep_the_per_package_release_steps(
    tmp_path: Path,
) -> None:
    for archetype in ("python-app", "python-tool"):
        steps = _release_steps(_root(tmp_path / archetype, archetype))
        assert any(s.get("name") == "Publish GitHub Release" for s in steps)


def test_s6_4_6_1_verify_and_postgres_pass_the_matrix_dir_through_env(
    tmp_path: Path,
) -> None:
    jobs = _lib_jobs(tmp_path)
    for name, task in (("verify", "ci:verify"), ("postgres", "ci:postgres")):
        assert jobs[name]["name"] == f"{name} (${{{{ matrix.name }}}})"
        step = next(
            s
            for s in jobs[name]["steps"]
            if s.get("run", "").startswith(f"task {task}")  # type: ignore[attr-defined]
        )
        assert step["run"] == f"task {task} -- ${{{{ matrix.name }}}}"
        assert step["env"]["PACKAGE_DIR"] == "${{ matrix.dir }}"


def test_s6_4_6_4_actionlint_passes_on_the_libs_fixture(tmp_path: Path) -> None:
    if shutil.which("actionlint") is None:
        pytest.skip("actionlint is not on PATH")
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
        ["actionlint", *WORKFLOWS],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
