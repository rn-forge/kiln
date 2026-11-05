"""S4.3.4 — the `cicd` module's artifacts: workflows, the setup action, Sonar.

Also proves the five properties every F4.3 story owes its module
(`docs/specs/epics/E4-generator/F4.3-concern-modules.md`).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.lang.models import ModelValidationError
from rn_forge.commons.generation import Action, ArtifactKind

from rn_forge.kiln import __version__, archetypes, checks, commands
from rn_forge.kiln.modules.cicd.checks import hooks as hooks_check
from rn_forge.kiln.modules.cicd.checks import pins as pins_check
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd import CICD
from rn_forge.kiln.modules.cicd.artifacts import load_pins
from rn_forge.kiln.modules.cicd.config import GENERATED_JOBS
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.docs import generate
from rn_forge.kiln.modules.tasks import TASKS

ARCHETYPES = ("python-app", "python-tool", "python-lib")

CI_KEYS = (
    ".github/actions/setup/action.yml",
    ".github/workflows/ci.yml",
    ".github/dependabot.yml",
    "sonar-project.properties",
)
WORKFLOWS = (".github/workflows/ci.yml",)


def _keys(archetype: str, keys: tuple[str, ...] = CI_KEYS) -> tuple[str, ...]:
    """The rows `archetype` renders: the same for every archetype since S15.8.6."""
    return keys


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
    release: str | None = None,
    provider: str = "github",
) -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    text = CONFIG.format(
        archetype=archetype,
        profile=profile,
        sonar=str(sonar).lower(),
        release=release or ("nx-dispatch" if archetype == "node-lib" else "tag-exists"),
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
        (path, ArtifactKind.MANAGED) for path in _keys(archetype)
    ]


def test_s4_3_4_property1_without_mkdocs_or_sonar_renders_three_rows(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, profile="none", sonar=False)
    assert list(_rendered(root)) == list(CI_KEYS[:3])


def test_s4_3_4_property1_ado_is_reserved(tmp_path: Path) -> None:
    root = _root(tmp_path, provider="ado")
    with pytest.raises(AppException, match="E8"):
        _rendered(root)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_4_property2_into_an_empty_directory_only_creates(
    tmp_path: Path, archetype: str
) -> None:
    actions = _actions(_root(tmp_path, archetype), tmp_path)
    assert {actions[key] for key in _keys(archetype)} == {Action.CREATE}


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_4_property3_a_second_apply_is_unchanged(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    actions = _actions(root, tmp_path)
    assert {actions[key] for key in _keys(archetype)} == {Action.UNCHANGED}


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
        ["actionlint", *_keys(archetype, WORKFLOWS)],
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
    jobs = YamlUtils.load(off[".github/workflows/ci.yml"])["jobs"]
    assert set(jobs) == {
        "validate",
        "dependency-review",
        "secret-scan",
        "plan",
        "test",
        "integration",
        "smoke",
        "suites",
        "release",
        "verify-release",
        "docs",
        "checks-ok",
        "ci-ok",
    }
    assert jobs["release"]["needs"] == ["plan", "checks-ok"]
    assert "\n  sonar:" not in off[".github/workflows/ci.yml"]
    # Everything else keeps its bytes.
    on_ci = on[".github/workflows/ci.yml"]
    sonar_job = on_ci[on_ci.index("\n  sonar:") : on_ci.index("\n  release:")]
    expected = on_ci.replace(sonar_job, "").replace(
        "needs: [validate, dependency-review, plan, test, integration, smoke, suites, sonar, secret-scan]",
        "needs: [validate, dependency-review, plan, test, integration, smoke, suites, secret-scan]",
    )
    assert off[".github/workflows/ci.yml"] == expected


def test_s4_3_4_3_release_none_renders_no_release_job(tmp_path: Path) -> None:
    rendered = _rendered(_root(tmp_path, release="none"))
    jobs = YamlUtils.load(rendered[".github/workflows/ci.yml"])["jobs"]
    assert set(jobs) == {
        "validate",
        "dependency-review",
        "secret-scan",
        "plan",
        "test",
        "integration",
        "smoke",
        "suites",
        "sonar",
        "docs",
        "checks-ok",
        "ci-ok",
    }


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
    jobs = YamlUtils.load(workflow)["jobs"]
    for name, job in jobs.items():
        steps = job.get("steps", [])
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
    parsed = YamlUtils.load(action)
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
            for name, job in YamlUtils.load(content)["jobs"].items():
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
    return YamlUtils.load(_rendered(root)[".github/workflows/ci.yml"])["jobs"]


def test_s6_3_2_ci_ok_needs_every_other_job(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        jobs = _ci_jobs(root)
        assert list(jobs)[-1] == "ci-ok", root.name
        covered = {*jobs["checks-ok"]["needs"], *jobs["ci-ok"]["needs"]}  # type: ignore[misc]
        assert covered == set(jobs) - {"ci-ok"}, root.name
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


def test_s6_7_4_1_the_target_step_is_a_task_call(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        if root.name == "nosonar":
            continue
        step = next(s for s in _sonar_steps(root) if s.get("id") == "target")
        assert step["name"] == "Resolve the analysis target", root.name
        assert step["env"] == {
            "EVENT_NAME": "${{ github.event_name }}",
            "REF_TYPE": "${{ github.ref_type }}",
            "REF_NAME": "${{ github.ref_name }}",
        }, root.name
        assert step["run"] == 'task ci:sonar-target >> "$GITHUB_OUTPUT"', root.name


def test_s6_3_8_sonar_runs_only_on_a_pull_request_or_main(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        if root.name == "nosonar":
            continue
        condition = " ".join(str(_ci_jobs(root)["sonar"]["if"]).split())
        assert (
            "(github.event_name == 'pull_request' && "
            "github.event.pull_request.head.repo.full_name == github.repository) || "
            "(github.event_name != 'pull_request' && github.ref == 'refs/heads/main')"
        ) in condition, root.name


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


def test_s6_7_5_6_the_release_job_is_task_calls(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        assert [s["name"] for s in steps] == [
            "Checkout",
            "Set up the toolchain",
            "Check whether this version has been released",
            "Check out the release source",
            "Build",
            "Generate provenance",
            "Publish GitHub Release",
        ], root.name
        for step in steps:
            assert "\n" not in str(step.get("run", "")), (root.name, step["name"])


def test_s6_3_4_check_step_outputs_the_tag_state(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        check = next(step for step in steps if step.get("id") == "check")
        assert check["env"] == {"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}, root.name
        assert check["run"] == 'task ci:release-state >> "$GITHUB_OUTPUT"', root.name


def test_s6_3_4_checkout_of_the_tag_precedes_build(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        index = _step_index(steps, "Check out the release source")
        step = steps[index]
        assert step["id"] == "source"
        assert step["if"] == "steps.check.outputs.should-release == 'true'"
        assert step["env"] == {"TAG": "${{ steps.check.outputs.tag }}"}
        assert step["run"] == 'task ci:release-source >> "$GITHUB_OUTPUT"'
        check = next(i for i, s in enumerate(steps) if s.get("id") == "check")
        assert check < index < _step_index(steps, "Build"), root.name


def test_s6_3_4_draft_is_deleted_before_publish(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        names = [s["name"] for s in steps]
        assert "Delete the leftover draft" not in names, root.name
        publish = steps[_step_index(steps, "Publish GitHub Release")]
        assert publish["run"] == "task ci:release-publish", root.name
        assert _step_index(steps, "Build") < names.index("Publish GitHub Release")


def test_s6_3_4_publish_targets_the_source_commit(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        publish = steps[_step_index(steps, "Publish GitHub Release")]
        assert (
            publish["env"]["SOURCE_SHA"]  # type: ignore[index]
            == "${{ steps.source.outputs.sha }}"
        )
        assert any(step.get("id") == "source" for step in steps)


def test_s6_3_6_release_uploads_distributions_and_sbom_only(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        publish = steps[_step_index(steps, "Publish GitHub Release")]
        assert publish["run"] == "task ci:release-publish", root.name
        tasks = _ci_tasks_text_of(root)["tasks"]
        run = " ".join(tasks["release-publish"]["cmds"])  # type: ignore[index]
        assert "dist/*.whl dist/*.tar.gz dist/*.cdx.json" in run, root.name
        assert "dist/*" not in run.split(), root.name


UPSTREAM_PINS = {
    "setup-uv": ("1c37ad07a6a961277cf70c0d37d6f313000f5884", "v10.3.0"),
    "sonarqube-scan": ("d209202bc7d53ff1cc128f7f907dac145c9d6ae9", "v8.3.0"),
    "deploy-pages": ("368f82528645a54fb793d4d04e342629a3f51346", "v5.0.1"),
    "upload-artifact": ("cf430e030ddbb5b0abf93d22962f4752f3646cd9", "v7.0.2"),
    "download-artifact": ("9000827ccba6bdab643e8b6fd33ac0654aef8333", "v8.0.2"),
    "pnpm-setup": ("0ebf47130e4866e96fce0953f49152a61190b271", "v6.0.9"),
    "setup-node": ("820762786026740c76f36085b0efc47a31fe5020", "v7.0.0"),
}


def test_s6_3_5_setup_uv_enables_the_cache(tmp_path: Path) -> None:
    action = YamlUtils.load(
        _rendered(_root(tmp_path))[".github/actions/setup/action.yml"]
    )
    install = next(
        step for step in action["runs"]["steps"] if step["name"] == "Install uv"
    )
    assert install["with"]["enable-cache"] is True


def test_s7_4_4_1_uv_cache_follows_the_kiln_pin(tmp_path: Path) -> None:
    action = YamlUtils.load(
        _rendered(_root(tmp_path))[".github/actions/setup/action.yml"]
    )
    install = next(
        step for step in action["runs"]["steps"] if step["name"] == "Install uv"
    )
    assert install["with"]["cache-dependency-glob"].split() == [
        "**/uv.lock",
        ".rn-forge/kiln/config.toml",
    ]


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
        jobs = YamlUtils.load(_rendered(root)[".github/workflows/ci.yml"])["jobs"]
        step = next(s for s in jobs["validate"]["steps"] if s["name"] == "Validate")
        assert step["run"] == (
            "task lint" if archetype == "python-lib" else "task ci:validate"
        )
        assert step["env"]["KILN_DOCTOR_FULL"] == KILN_DOCTOR_FULL_EXPRESSION, archetype


RELEASE_PERMISSIONS = {
    "contents": "write",
    "id-token": "write",
    "attestations": "write",
}


def _lib_jobs(tmp_path: Path, **kwargs: object) -> dict[str, dict[str, object]]:
    return _ci_jobs(_root(tmp_path, "python-lib", **kwargs))  # type: ignore[arg-type]


PLAN_KEYS = (
    "release-order",
    "packages",
    "integration",
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


def test_s6_4_2_6_test_job(tmp_path: Path) -> None:
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


def test_s6_4_2_6_sonar_waits_for_test(tmp_path: Path) -> None:
    sonar = _lib_jobs(tmp_path)["sonar"]
    assert sonar["needs"] == ["validate", "test", "integration", "smoke"]
    assert str(sonar["if"]).startswith(
        "${{ !cancelled() && !contains(needs.*.result, 'failure') && ("
    )
    assert "head.repo.full_name == github.repository" in str(sonar["if"])


def test_s6_4_2_8_other_archetypes_keep_the_plain_pipeline(tmp_path: Path) -> None:
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


def test_s6_4_3_2_declared_jobs_follow_test(tmp_path: Path) -> None:
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


def test_s15_8_2_integration_is_generated(tmp_path: Path) -> None:
    assert "integration" in GENERATED_JOBS
    extra = f'\n[[ci.jobs]]\nname = "integration"\nuses = "{CALL}"\n'
    root = _with_ci(_root(tmp_path, "python-lib"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_s6_8_3_1_attest_step(tmp_path: Path) -> None:
    steps = _release_steps(_pypi_root(tmp_path / "pypi"))
    names = [step.get("name") for step in steps]
    index = names.index("Attest PyPI publish")
    assert names[index - 1] == "Generate provenance"
    assert names[index + 1] == "Publish releases"
    assert steps[index]["if"] == "steps.build.outputs.built != '0'"
    assert steps[index]["run"] == "task ci:release-sign"
    plain = _release_steps(_lib_root(tmp_path / "plain"))
    assert "Attest PyPI publish" not in [step.get("name") for step in plain]


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
    assert jobs["sonar"]["needs"] == [
        "validate",
        "test",
        "integration",
        "smoke",
    ]
    assert {"integration", "smoke", "suites"} <= set(jobs["checks-ok"]["needs"])  # type: ignore[arg-type]


def _marker_steps(job: dict[str, object]) -> list[dict[str, object]]:
    return job["steps"][-2:]  # type: ignore[index,return-value]


def test_s6_4_4_1_check_jobs_end_with_marker_steps(tmp_path: Path) -> None:
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


def test_s6_4_4_2_python_lib_release_job(tmp_path: Path) -> None:
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
    assert steps[3]["run"] == "task ci:release-build"  # type: ignore[index]
    assert steps[3]["env"] == env  # type: ignore[index]
    assert steps[5]["run"] == "task ci:release-publish"  # type: ignore[index]
    assert steps[5]["env"] == env  # type: ignore[index]
    assert len(steps) == 6  # type: ignore[arg-type]


def test_s6_4_4_3_release_task_is_pykit_s_script(tmp_path: Path) -> None:
    tasks = _ci_tasks_text(tmp_path)["tasks"]
    script = "\n".join(
        "\n".join(tasks[name]["cmds"])  # type: ignore[index]
        for name in ("release-build", "release-publish")
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


def test_s6_4_4_4_verify_release(tmp_path: Path) -> None:
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


def _ci_tasks_text_of(root: Path) -> dict[str, object]:
    from rn_forge.kiln.modules.tasks import TASKS

    rendered = {a.path: a.content for a in TASKS.artifacts(KilnConfig.load(root), root)}
    return YamlUtils.load(rendered["tasks/ci.yml"])


def _ci_tasks_text(tmp_path: Path) -> dict[str, object]:
    return _ci_tasks_text_of(_root(tmp_path / "tasks", "python-lib"))


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
        names = [s.get("name") for s in steps]
        assert "Generate provenance" in names
        assert "Publish GitHub Release" in names


def test_s6_4_6_1_test_passes_the_matrix_dir_through_env(
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
        ["actionlint", ".github/workflows/ci.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_s11_5_1_2_python_lib_docs_job(tmp_path: Path) -> None:
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
    publish = next(s for s in steps if s.get("run") == "task ci:docs-publish")  # type: ignore[attr-defined]
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


def test_s11_5_1_3_python_lib_renders_no_docs_yml(tmp_path: Path) -> None:
    rendered = _rendered(_root(tmp_path, "python-lib"))
    assert ".github/workflows/docs.yml" not in rendered
    assert ".github/workflows/ci.yml" in rendered


def test_s11_5_1_4_other_archetypes_deploy_docs_from_ci(
    tmp_path: Path,
) -> None:
    for archetype in ("python-app", "python-tool"):
        rendered = _rendered(_root(tmp_path / archetype, archetype))
        assert ".github/workflows/docs.yml" not in rendered, archetype
        assert "docs" in YamlUtils.load(rendered[".github/workflows/ci.yml"])["jobs"], (
            archetype
        )


def test_s11_5_1_2_actionlint_passes_on_the_docs_job(tmp_path: Path) -> None:
    if shutil.which("actionlint") is None:
        pytest.skip("actionlint is not on PATH")
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


def test_s6_4_7_1_release_needs_every_check_and_sonar(tmp_path: Path) -> None:
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


def test_s6_4_7_2_release_runs_on_a_default_branch_push_only(tmp_path: Path) -> None:
    release = _lib_jobs(tmp_path)["release"]
    assert release["if"] == RELEASE_IF % ""
    assert "pull_request" not in str(release["if"])
    assert "workflow_dispatch" not in str(release["if"])


def test_s6_4_7_3_release_waits_on_sonar_only_where_sonar_renders(
    tmp_path: Path,
) -> None:
    jobs = _lib_jobs(tmp_path, sonar=False)
    release = jobs["release"]
    assert release["needs"] == ["plan", "checks-ok"]
    assert "sonar" not in jobs["checks-ok"]["needs"]  # type: ignore[operator]
    assert release["if"] == RELEASE_IF % ""
    assert "sonar" not in str(release)


def test_s6_4_7_4_release_has_no_publish_switch(tmp_path: Path) -> None:
    text = _rendered(_root(tmp_path, "python-lib"))[".github/workflows/ci.yml"]
    assert "PUBLISH" not in text
    tasks = _ci_tasks_text(tmp_path)["tasks"]
    script = "\n".join(
        "\n".join(tasks[name]["cmds"])  # type: ignore[index]
        for name in ("release-build", "release-publish")
    )
    assert "PUBLISH" not in script
    assert "release-publish" in script


def test_s6_4_7_5_smoke_takes_an_empty_extra_row_unchanged(tmp_path: Path) -> None:
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


def test_s6_4_7_6_ci_ok_needs_every_job_and_tolerates_a_skipped_release(
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
def test_s6_4_7_7_actionlint_passes_on_the_python_lib_workflows(
    tmp_path: Path, release: str
) -> None:
    if shutil.which("actionlint") is None:
        pytest.skip("actionlint is not on PATH")
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


GOLDEN_RENDER = (
    '\n[[ci.jobs]]\nname = "golden-render"\n'
    'uses = "./.github/workflows/golden-render.yml"\n'
    'events = ["pull_request"]\n'
)


def _with_ci(root: Path, extra: str) -> Path:
    """Add `extra` to the `[ci]` section of `root`'s config."""
    config = root / ".rn-forge" / "kiln" / "config.toml"
    text = config.read_text(encoding="utf-8")
    if "[ci]" not in text:
        text += "\n[ci]\n"
    ci_end = text.index("[ci]")
    section_end = text.find("\n[", ci_end + 1)
    if section_end == -1:
        text += extra
    else:
        text = text[:section_end] + extra + text[section_end:]
    config.write_text(text, encoding="utf-8")
    return root


def _action(root: Path) -> str:
    return _rendered(root)[".github/actions/setup/action.yml"]


def test_s4_8_3_1_node_off_renders_no_node_steps(tmp_path: Path) -> None:
    action = _action(_root(tmp_path, "python-tool"))
    assert "pnpm/action-setup" not in action
    assert "actions/setup-node" not in action


def test_s4_8_3_1_web_app_keeps_node(tmp_path: Path) -> None:
    web = _action(
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"')
    )
    assert "pnpm/action-setup" in web
    assert "actions/setup-node" in web
    assert "cache: pnpm" in web
    assert "\n\n\n" not in web


def test_s4_8_3_2_no_declared_jobs_is_unchanged(tmp_path: Path) -> None:
    roots = [_root(tmp_path / a, a) for a in ARCHETYPES] + [
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"')
    ]
    for root in roots:
        plain = _rendered(root)[".github/workflows/ci.yml"]
        empty = _rendered(_with_ci(root, "jobs = []\n"))[".github/workflows/ci.yml"]
        assert plain == empty, root.name
        assert set(YamlUtils.load(plain)["jobs"]) <= GENERATED_JOBS, root.name
        assert "\n\n\n" not in plain, root.name


HOOKS = '\n[ci.hooks]\nsetup = ["./.github/actions/a", "./.github/actions/b"]\n'
CALL = "./.github/workflows/golden-render.yml"


def _hook_steps(action: str) -> list[dict[str, str]]:
    return YamlUtils.load(action)["runs"]["steps"]


def test_s4_11_1_1_setup_hooks_render_last_and_in_order(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), HOOKS)
    steps = _hook_steps(_action(root))
    assert steps[-3]["name"] == "Install go-task"
    assert steps[-2:] == [
        {"name": "Run ./.github/actions/a", "uses": "./.github/actions/a"},
        {"name": "Run ./.github/actions/b", "uses": "./.github/actions/b"},
    ]


def test_s4_11_1_1_hooks_follow_the_node_steps(tmp_path: Path) -> None:
    root = _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    plain = _hook_steps(_action(root))
    steps = _hook_steps(_action(_with_ci(root, HOOKS)))
    assert steps[: len(plain)] == plain
    assert "actions/setup-node" in steps[len(plain) - 1]["uses"]
    assert [s["name"] for s in steps[len(plain) :]] == [
        "Run ./.github/actions/a",
        "Run ./.github/actions/b",
    ]


def test_s4_11_1_2_no_hooks_is_byte_identical(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-tool")
    plain = _action(root)
    empty = _action(_with_ci(root, "hooks = { setup = [] }\n"))
    assert plain == empty
    assert "Run ./" not in plain
    assert "\n\n\n" not in plain


def test_s4_11_1_3_web_app_still_renders_node_steps(tmp_path: Path) -> None:
    web = _action(
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"')
    )
    assert "pnpm/action-setup" in web
    assert "actions/setup-node" in web
    assert "cache: pnpm" in web


def test_s4_11_1_4_node_key_is_refused(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), "node = true\n")
    with pytest.raises(AppException):
        KilnConfig.load(root)


@pytest.mark.parametrize(
    "path",
    [
        "./.github/actions/setup",
        ".github/actions/x",
        "./actions/x",
        "./.github/actions/X",
        "./.github/actions/a/b",
        "./.github/workflows/x.yml",
    ],
)
def test_s4_11_1_5_bad_hook_paths_are_refused(tmp_path: Path, path: str) -> None:
    root = _with_ci(
        _root(tmp_path, "python-tool"), f'\n[ci.hooks]\nsetup = ["{path}"]\n'
    )
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_s4_11_1_5_duplicate_hooks_are_refused(tmp_path: Path) -> None:
    extra = '\n[ci.hooks]\nsetup = ["./.github/actions/a", "./.github/actions/a"]\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_s4_11_1_6_declared_job_renders_as_a_call(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), GOLDEN_RENDER)
    jobs = _ci_jobs(root)
    assert jobs["golden-render"] == {
        "needs": "validate",
        "if": "${{ github.event_name == 'pull_request' }}",
        "permissions": {"contents": "read"},
        "uses": CALL,
    }
    assert "golden-render" in jobs["checks-ok"]["needs"]  # type: ignore[operator]
    names = list(jobs)
    assert names[-1] == "ci-ok"
    assert names[-2] == "checks-ok"
    assert names[-3] == "golden-render"


def test_s4_11_1_6_declared_job_defaults_to_every_event(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\n'
    job = _ci_jobs(_with_ci(_root(tmp_path, "python-tool"), extra))["extra"]
    assert "if" not in job


def test_s4_11_1_6_declared_job_with_two_events_ors_them(tmp_path: Path) -> None:
    extra = (
        f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\n'
        'events = ["push", "workflow_dispatch"]\n'
    )
    job = _ci_jobs(_with_ci(_root(tmp_path, "python-tool"), extra))["extra"]
    assert job["if"] == (
        "${{ github.event_name == 'push' || github.event_name == 'workflow_dispatch' }}"
    )


@pytest.mark.parametrize(
    "uses",
    [
        "./.github/workflows/ci.yml",
        ".github/workflows/x.yml",
        "./.github/actions/x",
        "./x.yml",
        "./.github/workflows/sub/x.yml",
        "./.github/workflows/x.txt",
        "owner/repo/.github/workflows/x.yml@v1",
    ],
)
def test_s4_11_1_7_bad_uses_is_refused(tmp_path: Path, uses: str) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{uses}"\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_s4_11_1_7_task_key_is_refused(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\ntask = "validate"\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


@pytest.mark.parametrize(
    "name", ["sonar", "validate", "ci-ok", "checks-ok", "Golden", "a_b"]
)
def test_s4_11_1_7_job_name_collision_is_refused(tmp_path: Path, name: str) -> None:
    extra = f'\n[[ci.jobs]]\nname = "{name}"\nuses = "{CALL}"\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_s4_11_1_7_duplicate_declared_names_are_refused(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "a"\nuses = "{CALL}"\n' * 2
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_s4_11_1_8_actionlint_passes_on_a_declared_call(tmp_path: Path) -> None:
    if shutil.which("actionlint") is None:
        pytest.skip("actionlint is not on PATH")
    root = _with_ci(_root(tmp_path, "python-tool"), HOOKS + GOLDEN_RENDER)
    cycle.apply(root, home=tmp_path / "home")
    for name in ("a", "b"):
        action = root / ".github" / "actions" / name / "action.yml"
        action.parent.mkdir(parents=True)
        action.write_text(
            "name: x\ndescription: x\nruns:\n  using: composite\n  steps:\n"
            "    - run: echo hi\n      shell: bash\n",
            encoding="utf-8",
        )
    called = root / ".github" / "workflows" / "golden-render.yml"
    called.write_text(
        "name: golden-render\non: workflow_call\njobs:\n  golden-render:\n"
        "    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "actionlint",
            ".github/workflows/ci.yml",
            ".github/workflows/golden-render.yml",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [
        ("python-app", ""),
        ("python-tool", ""),
        ("python-lib", ""),
        ("python-web-api", ""),
        ("python-web-app", 'frontend = "angular"'),
    ],
)
def test_s4_11_2_5_every_cell_passes_ci_pins_and_ci_hooks(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    if archetype.startswith("python-web"):
        root = _web_root(tmp_path, archetype, extra=extra)
    else:
        root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    assert pins_check.check(KilnConfig.load(root), root) == []
    assert hooks_check.check(KilnConfig.load(root), root) == []


# S4.11.3 — workflow security.

SECURITY_CELLS = [
    ("python-app", ""),
    ("python-tool", ""),
    ("python-lib", ""),
    ("python-web-api", ""),
    ("python-web-app", 'frontend = "angular"'),
]


def _cell_root(tmp_path: Path, archetype: str, extra: str) -> Path:
    if archetype.startswith("python-web"):
        return _web_root(tmp_path, archetype, extra=extra)
    return _root(tmp_path, archetype)


def _checkouts(root: Path) -> list[tuple[str, str, dict[str, object]]]:
    """Every `actions/checkout` step in the rendered workflows, as
    (workflow, job, step)."""
    found = []
    for path, content in _rendered(root).items():
        if not path.startswith(".github/workflows/"):
            continue
        for job_name, job in YamlUtils.load(content)["jobs"].items():
            for step in job.get("steps", []):
                if str(step.get("uses", "")).startswith("actions/checkout@"):
                    found.append((path, job_name, step))
    return found


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_3_1_checkouts_do_not_persist_credentials(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    checkouts = _checkouts(_cell_root(tmp_path, archetype, extra))
    assert checkouts
    for path, job, step in checkouts:
        if archetype == "python-lib" and job == "docs":
            continue
        assert step["with"]["persist-credentials"] is False, f"{path}:{job}"  # type: ignore[index]


def test_s4_11_3_1_the_python_lib_docs_job_keeps_credentials(tmp_path: Path) -> None:
    persisting = [
        (archetype, job)
        for archetype, extra in SECURITY_CELLS
        for _, job, step in _checkouts(
            _cell_root(tmp_path / archetype, archetype, extra)
        )
        if step["with"]["persist-credentials"] is True  # type: ignore[index]
    ]
    assert persisting == [("python-lib", "docs")]
    docs = _lib_jobs(tmp_path / "docs")["docs"]
    assert docs["permissions"]["contents"] == "write"  # type: ignore[index]


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s16_4_6_1_docs_job_comment(tmp_path: Path, archetype: str, extra: str) -> None:
    """Every persisted checkout in a rendered workflow carries the reason."""
    rendered = _rendered(_cell_root(tmp_path, archetype, extra))
    for path, content in rendered.items():
        if not path.startswith(".github/workflows/"):
            continue
        for line in content.splitlines():
            if "persist-credentials: true" in line:
                assert line.strip() == (
                    "persist-credentials: true # mike pushes gh-pages with this token"
                ), (archetype, path)
    ci = YamlUtils.load(rendered[".github/workflows/ci.yml"])["jobs"]
    if "docs" in ci and archetype == "python-lib":
        assert (
            "persist-credentials: true # mike pushes gh-pages with this token"
            in (rendered[".github/workflows/ci.yml"])
        )


def test_s4_11_3_1_fetch_depth_is_kept(tmp_path: Path) -> None:
    lib = _checkouts(_root(tmp_path, "python-lib"))
    deep = {job for _, job, step in lib if step["with"].get("fetch-depth") == 0}  # type: ignore[union-attr]
    assert {"plan", "sonar", "verify-release"} <= deep


def test_s4_11_3_2_the_release_version_is_read_through_env(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        for step in steps:
            if "run" in step:
                assert "${{" not in str(step["run"]), (root.name, step.get("name"))
        tasks = _ci_tasks_text_of(root)["tasks"]
        assert tasks["release-state"]["cmds"] == [  # type: ignore[index]
            '{{.DEVOPS}} release-state "v$({{.TASK_EXE}} version)"'
        ]


def test_s4_11_3_3_release_publishes_with_gh_release_create(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        publish = steps[_step_index(steps, "Publish GitHub Release")]
        assert "uses" not in publish
        assert "with" not in publish
        assert publish["run"] == "task ci:release-publish"
        env = publish["env"]  # type: ignore[index]
        assert env == {
            "GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
            "TAG": "${{ steps.check.outputs.tag }}",
            "SOURCE_SHA": "${{ steps.source.outputs.sha }}",
        }
        for content in _rendered(root).values():
            assert "softprops/action-gh-release" not in content


def test_s4_11_3_3_gh_release_pin_is_removed() -> None:
    assert "gh-release" not in load_pins()


def test_s4_11_3_4_local_setup_uses_carry_a_reasoned_ignore(tmp_path: Path) -> None:
    pattern = re.compile(r"# zizmor: ignore\[self-repository\] \S")
    for archetype, extra in SECURITY_CELLS:
        root = _cell_root(tmp_path / archetype, archetype, extra)
        seen = 0
        for path, content in _rendered(root).items():
            if not path.startswith(".github/workflows/"):
                continue
            for line in content.splitlines():
                if "uses: ./.github/actions/setup" in line:
                    seen += 1
                    assert pattern.search(line), f"{archetype}:{path}: {line}"
        assert seen, archetype


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_3_5_zizmor_and_actionlint_pass_on_every_cell(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    if shutil.which("zizmor") is None or shutil.which("actionlint") is None:
        pytest.skip("zizmor or actionlint is not on PATH")
    root = _cell_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    zizmor = subprocess.run(
        ["zizmor", "--offline", str(root / ".github")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert zizmor.returncode == 0, zizmor.stdout + zizmor.stderr
    workflows = sorted(
        str(p.relative_to(root)) for p in (root / ".github/workflows").glob("*.yml")
    )
    lint = subprocess.run(
        ["actionlint", *workflows],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr


DEPENDABOT = ".github/dependabot.yml"
DEPENDABOT_HOOKS = (
    '\n[ci.hooks]\nsetup = ["./.github/actions/b", "./.github/actions/a"]\n'
)


def _dependabot(root: Path) -> dict[str, object]:
    return YamlUtils.load(_rendered(root)[DEPENDABOT])


def _hook_entry(root: Path) -> dict[str, object]:
    """The `github-actions` entry for hook directories (no `directory`)."""
    (entry,) = [
        u
        for u in _dependabot(root)["updates"]  # type: ignore[attr-defined]
        if u["package-ecosystem"] == "github-actions" and "directories" in u
    ]
    return entry


def _updates_of(content: str) -> list[str]:
    """The package ecosystems a rendered `dependabot.yml` updates."""
    return [u["package-ecosystem"] for u in YamlUtils.load(content)["updates"]]


def _updates(root: Path) -> dict[str, dict[str, object]]:
    return {u["package-ecosystem"]: u for u in _dependabot(root)["updates"]}  # type: ignore[attr-defined]


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_4_1_dependabot_is_a_managed_row(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    artifacts = {a.path: a for a in CICD.artifacts(KilnConfig.load(root), root)}
    assert artifacts[DEPENDABOT].kind is ArtifactKind.MANAGED
    assert DEPENDABOT in CI_KEYS


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_4_2_no_hooks_renders_only_the_root_actions_entry_and_uv(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    parsed = _dependabot(root)
    assert parsed["version"] == 2
    updates = parsed["updates"]
    npm = 1 if archetype == "python-web-app" else 0
    assert [u["package-ecosystem"] for u in updates] == [  # type: ignore[index]
        "github-actions",
        "uv",
        *["npm"] * npm,
    ]
    assert "directories" not in updates[0]  # type: ignore[index]
    assert updates[1]["directory"] == "/"  # type: ignore[index]
    assert updates[1]["schedule"]["interval"] == "weekly"  # type: ignore[index]


def test_s4_11_4_3_hooks_render_exactly_their_directories(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), DEPENDABOT_HOOKS)
    updates = _dependabot(root)["updates"]
    assert [u["package-ecosystem"] for u in updates] == [  # type: ignore[index,union-attr]
        "github-actions",
        "github-actions",
        "uv",
    ]
    actions = updates[0]  # type: ignore[index]
    assert actions["directories"] == ["/.github/actions/b", "/.github/actions/a"]
    assert "directory" not in actions
    assert "ignore" not in actions
    assert actions["schedule"]["interval"] == "weekly"


@pytest.mark.parametrize(
    "hooks",
    [
        DEPENDABOT_HOOKS,
        '\n[ci.hooks]\nsetup = ["./.github/actions/one"]\n',
    ],
)
def test_s4_11_4_3_never_the_root_or_the_setup_action(
    tmp_path: Path, hooks: str
) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), hooks)
    directories = _hook_entry(root)["directories"]
    assert directories
    for directory in directories:  # type: ignore[attr-defined]
        assert directory not in {"/", "/.github/actions/setup"}
        assert not directory.endswith("*")


def test_s4_11_4_4_one_group_per_ecosystem_for_minor_and_patch(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), DEPENDABOT_HOOKS)
    updates = _dependabot(root)["updates"]
    assert len(updates) == 3  # type: ignore[arg-type]
    for entry in updates:  # type: ignore[attr-defined]
        groups = entry["groups"]
        assert len(groups) == 1
        assert next(iter(groups.values()))["update-types"] == ["minor", "patch"]


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_4_5_uv_directory_is_the_root(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    assert _updates(root)["uv"]["directory"] == "/"


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_4_6_ci_comment_no_longer_says_kiln_only(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    ci = _rendered(_cell_root(tmp_path, archetype, extra))[".github/workflows/ci.yml"]
    assert "Dependabot watches kiln's own repo" not in ci
    assert "dependabot.yml" in ci


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
@pytest.mark.parametrize("hooks", ["", DEPENDABOT_HOOKS])
def test_s4_11_4_7_the_file_passes_the_checks(
    tmp_path: Path, archetype: str, extra: str, hooks: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    if hooks:
        root = _with_ci(root, hooks)
        for name in ("a", "b"):
            action = root / ".github" / "actions" / name / "action.yml"
            action.parent.mkdir(parents=True)
            action.write_text(
                "name: x\nruns:\n  using: composite\n  steps: []\n", encoding="utf-8"
            )
    cycle.apply(root, home=tmp_path / "home")
    config = KilnConfig.load(root)  # fills the nav `mkdocs.yml` is rendered with
    generate.generate(root, config.packages if archetype == "python-lib" else ())
    assert (root / DEPENDABOT).is_file()
    assert checks.run(root, scope="ownership") == []
    assert _actions(root, tmp_path)[DEPENDABOT] is Action.UNCHANGED


def test_s4_11_4_8_ado_still_renders_nothing(tmp_path: Path) -> None:
    root = _root(tmp_path, provider="ado")
    with pytest.raises(AppException, match="E8"):
        _rendered(root)


def test_s4_11_4_9_every_entry_has_a_cooldown(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), DEPENDABOT_HOOKS)
    for entry in _dependabot(root)["updates"]:  # type: ignore[attr-defined]
        assert entry["cooldown"]["default-days"] >= 7


# S4.11.5 — dependency review.


def _review_jobs(root: Path) -> dict[str, dict[str, object]]:
    return YamlUtils.load(_rendered(root)[".github/workflows/ci.yml"])["jobs"]


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_5_8_dependency_review_job(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    jobs = _review_jobs(_cell_root(tmp_path, archetype, extra))
    job = jobs["dependency-review"]
    assert job["if"] == "${{ github.event_name == 'pull_request' }}"
    assert job["needs"] == "validate"
    assert job["permissions"] == {"contents": "read"}
    assert isinstance(job["timeout-minutes"], int)
    assert job["runs-on"] == "ubuntu-latest"
    steps = job["steps"]
    assert len(steps) == 2  # type: ignore[arg-type]
    pins = load_pins()
    checkout, review = steps  # type: ignore[misc]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["persist-credentials"] is False
    assert review["uses"] == (
        f"{pins['dependency-review']['uses']}@{pins['dependency-review']['sha']}"
    )
    assert all("actions/setup" not in str(s.get("uses", "")) for s in steps)  # type: ignore[attr-defined]


def test_s4_11_5_8_dependency_review_is_pinned(tmp_path: Path) -> None:
    pin = load_pins()["dependency-review"]
    assert pin["uses"] == "actions/dependency-review-action"
    assert re.fullmatch(r"[0-9a-f]{40}", pin["sha"])
    assert pin["version"]
    for archetype, extra in SECURITY_CELLS:
        root = _cell_root(tmp_path / archetype, archetype, extra)
        cycle.apply(root, home=tmp_path / archetype / "home")
        assert pins_check.check(KilnConfig.load(root), root) == [], archetype


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_5_8_ci_ok_needs_dependency_review(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    jobs = _review_jobs(_cell_root(tmp_path, archetype, extra))
    assert "dependency-review" in jobs["checks-ok"]["needs"]  # type: ignore[operator]


def test_s4_11_5_8_declared_jobs_cannot_take_the_name(tmp_path: Path) -> None:
    assert "dependency-review" in GENERATED_JOBS
    extra = f'\n[[ci.jobs]]\nname = "dependency-review"\nuses = "{CALL}"\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


# S4.11.6 — build provenance and an SBOM.

SUBJECTS = "dist/*.whl\ndist/*.tar.gz\ndist/*.cdx.json\n"
LIB_SUBJECTS = "dist/*/*.whl\ndist/*/*.tar.gz\ndist/*/*.cdx.json\n"
SINGLE_RELEASE_CELLS = [(a, e) for a, e in SECURITY_CELLS if a != "python-lib"]


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_6_3_release_job_permissions(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    allowed = {("ci.yml", "release"), ("ci.yml", "docs"), ("docs.yml", "deploy")}
    for path, content in _rendered(root).items():
        if not path.startswith(".github/workflows/"):
            continue
        workflow = Path(path).name
        for name, job in YamlUtils.load(content)["jobs"].items():
            permissions = job.get("permissions") or {}
            if (workflow, name) == ("ci.yml", "release"):
                assert permissions == RELEASE_PERMISSIONS, archetype
                continue
            assert "attestations" not in permissions, f"{workflow}:{name}"
            if "id-token" in permissions:
                assert (workflow, name) in allowed, f"{workflow}:{name}"


@pytest.mark.parametrize(("archetype", "extra"), SINGLE_RELEASE_CELLS)
def test_s4_11_6_4_single_package_release_attests_before_publishing(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    steps = _release_steps(_cell_root(tmp_path, archetype, extra))
    names = [s.get("name") for s in steps]
    build, provenance, publish = (
        names.index(n)
        for n in ("Build", "Generate provenance", "Publish GitHub Release")
    )
    assert build < provenance < publish
    pin = load_pins()["attest"]
    step = steps[provenance]
    assert step["uses"] == f"{pin['uses']}@{pin['sha']}"
    assert step["if"] == "steps.check.outputs.should-release == 'true'"
    assert step["with"] == {"subject-path": SUBJECTS}  # type: ignore[comparison-overlap]
    assert steps[publish]["run"] == "task ci:release-publish"


def test_s4_11_6_4_lib_release_attests_between_build_and_publish(
    tmp_path: Path,
) -> None:
    steps = _lib_jobs(tmp_path)["release"]["steps"]  # type: ignore[assignment]
    tail = steps[3:]  # type: ignore[index]
    assert [s["name"] for s in tail] == [
        "Build releases",
        "Generate provenance",
        "Publish releases",
    ]
    build, provenance, publish = tail
    env = {
        "GH_TOKEN": "${{ github.token }}",
        "SELECTED": "${{ needs.plan.outputs.release-order }}",
    }
    assert build["run"] == "task ci:release-build"
    assert build["env"] == env
    assert build["id"] == "build"
    pin = load_pins()["attest"]
    assert provenance["uses"] == f"{pin['uses']}@{pin['sha']}"
    assert provenance["if"] == "steps.build.outputs.built != '0'"
    assert provenance["with"] == {"subject-path": LIB_SUBJECTS}
    assert publish["run"] == "task ci:release-publish"
    assert publish["env"] == env


def test_s4_11_6_5_attest_is_pinned(tmp_path: Path) -> None:
    pin = load_pins()["attest"]
    assert pin["uses"] == "actions/attest"
    assert re.fullmatch(r"[0-9a-f]{40}", pin["sha"])
    assert pin["version"]
    assert "attest-provenance" not in load_pins()
    for archetype, extra in SECURITY_CELLS:
        root = _cell_root(tmp_path / archetype, archetype, extra)
        cycle.apply(root, home=tmp_path / archetype / "home")
        assert pins_check.check(KilnConfig.load(root), root) == [], archetype


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_6_6_release_none_renders_no_attestation(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    config = root / ".rn-forge" / "kiln" / "config.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(_release_none(text), encoding="utf-8")
    rendered = _rendered(root)
    assert "release" not in _ci_jobs(root)
    for path, content in rendered.items():
        if path != DEPENDABOT:  # its ignore list names every pinned action
            assert "attest" not in content, path
        if not path.startswith(".github/workflows/"):
            continue
        for name, job in YamlUtils.load(content)["jobs"].items():
            if "id-token" in (job.get("permissions") or {}):
                assert (Path(path).name, name) in {
                    ("ci.yml", "docs"),
                    ("docs.yml", "deploy"),
                }, f"{path}:{name}"


def _release_none(text: str) -> str:
    if 'release = "tag-exists"' in text:
        return text.replace('release = "tag-exists"', 'release = "none"')
    return text + '\n[ci]\nrelease = "none"\n'


DOCS_HOOKS = '\n[ci.hooks]\ndocs = ["./.github/actions/a", "./.github/actions/b"]\n'


def _docs_hook_steps(*names: str) -> list[dict[str, object]]:
    return [
        {
            "name": f"Run ./.github/actions/{n}",
            "uses": f"./.github/actions/{n}",
            "env": {"SITE_DIR": "${{ runner.temp }}/site"},
        }
        for n in names
    ]


def _job_steps(root: Path, workflow: str, job: str) -> list[dict[str, object]]:
    return YamlUtils.load(_rendered(root)[workflow])["jobs"][job]["steps"]


def test_s4_11_7_1_docs_hooks_render_before_the_upload(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-lib"), DOCS_HOOKS)
    steps = _job_steps(root, ".github/workflows/ci.yml", "docs")
    names = [s["name"] for s in steps]
    upload = names.index("Upload Pages artifact")
    assert steps[upload - 2 : upload] == _docs_hook_steps("a", "b")
    assert names[upload - 3] == "Deploy the package sites and build the root site"


def test_s4_11_7_1_docs_hooks_render_in_the_single_package_docs_job(
    tmp_path: Path,
) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), DOCS_HOOKS)
    steps = _job_steps(root, ".github/workflows/ci.yml", "docs")
    names = [s["name"] for s in steps]
    upload = names.index("Upload Pages artifact")
    assert steps[upload - 2 : upload] == _docs_hook_steps("a", "b")
    assert names[upload - 3] == "Build docs site"


@pytest.mark.parametrize("archetype", ["python-lib", "python-tool"])
def test_s4_11_7_2_no_docs_hooks_is_byte_identical(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    plain = _rendered(root)
    empty = _rendered(_with_ci(root, "hooks = { docs = [] }\n"))
    for workflow in WORKFLOWS:
        assert plain.get(workflow) == empty.get(workflow), workflow


def test_s4_11_7_3_docs_hooks_are_not_setup_hooks(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), DOCS_HOOKS)
    assert "Run ./" not in _action(root)


@pytest.mark.parametrize(
    "path",
    [
        "./.github/actions/setup",
        ".github/actions/x",
        "./actions/x",
        "./.github/actions/X",
        "./.github/actions/a/b",
        "./.github/workflows/x.yml",
    ],
)
def test_s4_11_7_4_bad_docs_hook_paths_are_refused(tmp_path: Path, path: str) -> None:
    root = _with_ci(
        _root(tmp_path, "python-tool"), f'\n[ci.hooks]\ndocs = ["{path}"]\n'
    )
    with pytest.raises(AppException, match=r"ci\.hooks\.docs"):
        KilnConfig.load(root)


def test_s4_11_7_4_duplicate_docs_hooks_are_refused(tmp_path: Path) -> None:
    extra = '\n[ci.hooks]\ndocs = ["./.github/actions/a", "./.github/actions/a"]\n'
    with pytest.raises(AppException):
        KilnConfig.load(_with_ci(_root(tmp_path / "dup", "python-tool"), extra))
    both = (
        '\n[ci.hooks]\nsetup = ["./.github/actions/a"]\n'
        'docs = ["./.github/actions/a"]\n'
    )
    KilnConfig.load(_with_ci(_root(tmp_path / "both", "python-tool"), both))


def test_s4_11_7_5_docs_hooks_without_docs_are_refused(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool", profile="none"), DOCS_HOOKS)
    with pytest.raises(AppException, match="nothing deploys Pages"):
        _rendered(root)


def test_s4_11_7_6_dependabot_covers_docs_hooks(tmp_path: Path) -> None:
    extra = (
        '\n[ci.hooks]\nsetup = ["./.github/actions/a"]\n'
        'docs = ["./.github/actions/b", "./.github/actions/a"]\n'
    )
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    assert _hook_entry(root)["directories"] == [
        "/.github/actions/a",
        "/.github/actions/b",
    ]


def test_s4_11_7_7_actionlint_passes_on_a_docs_hook(tmp_path: Path) -> None:
    if shutil.which("actionlint") is None:
        pytest.skip("actionlint is not on PATH")
    root = _with_ci(
        _root(tmp_path, "python-lib"),
        '\n[ci.hooks]\ndocs = ["./.github/actions/a"]\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    action = root / ".github" / "actions" / "a" / "action.yml"
    action.parent.mkdir(parents=True)
    action.write_text(
        "name: x\ndescription: x\nruns:\n  using: composite\n  steps:\n"
        "    - run: echo hi\n      shell: bash\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["actionlint", ".github/workflows/ci.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _ci_workflow(root: Path) -> dict[str, object]:
    return YamlUtils.load(_rendered(root)[".github/workflows/ci.yml"])


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_11_8_1_default_is_byte_identical(tmp_path: Path, archetype: str) -> None:
    plain = _rendered(_root(tmp_path / "plain", archetype))
    named = _rendered(
        _with_ci(
            _root(tmp_path / "named", archetype), 'doctor_full = "default-branch"\n'
        )
    )
    assert plain[".github/workflows/ci.yml"] == named[".github/workflows/ci.yml"]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_11_8_2_every_run_sets_the_variable(tmp_path: Path, archetype: str) -> None:
    default = _ci_workflow(_root(tmp_path / "default", archetype))
    every = _ci_workflow(
        _with_ci(_root(tmp_path / "every", archetype), 'doctor_full = "every-run"\n')
    )
    steps = every["jobs"]["validate"]["steps"]  # type: ignore[index]
    step = next(s for s in steps if s["name"] == "Validate")
    assert step["env"] == {"KILN_DOCTOR_FULL": "1"}
    step["env"] = next(
        s
        for s in default["jobs"]["validate"]["steps"]  # type: ignore[index]
        if s["name"] == "Validate"
    )["env"]
    assert every == default


def test_s4_11_8_3_bad_value_is_refused(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), 'doctor_full = "always"\n')
    with pytest.raises(AppException, match=r"ci\.doctor_full"):
        KilnConfig.load(root)


def test_s4_11_8_4_actionlint_passes_on_every_run(tmp_path: Path) -> None:
    if shutil.which("actionlint") is None:
        pytest.skip("actionlint is not on PATH")
    root = _with_ci(_root(tmp_path, "python-app"), 'doctor_full = "every-run"\n')
    cycle.apply(root, home=tmp_path / "home")
    result = subprocess.run(
        ["actionlint", ".github/workflows/ci.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _pypi_root(tmp_path: Path, archetype: str = "python-lib", **kwargs: object) -> Path:
    return _root(tmp_path, archetype, release="pypi", **kwargs)  # type: ignore[arg-type]


def _ci_text(root: Path) -> dict[str, object]:
    return YamlUtils.load(_rendered(root)[".github/workflows/ci.yml"])


def test_s7_6_4_1_dispatch_takes_testpypi(tmp_path: Path) -> None:
    on = _ci_text(_pypi_root(tmp_path / "pypi"))["on"]
    assert on["workflow_dispatch"] == {  # type: ignore[index]
        "inputs": {
            "testpypi": {
                "type": "boolean",
                "default": False,
                "description": "Upload every package to TestPyPI; no tags or releases",
            }
        }
    }
    plain = _ci_text(_root(tmp_path / "plain", "python-lib"))["on"]
    assert plain["workflow_dispatch"] == {}  # type: ignore[index]


def test_s7_6_4_2_release_job_environment(tmp_path: Path) -> None:
    release = _ci_jobs(_pypi_root(tmp_path))["release"]
    assert release["environment"] == "${{ inputs.testpypi && 'testpypi' || 'pypi' }}"
    assert release["permissions"] == RELEASE_PERMISSIONS
    plain = _lib_jobs(tmp_path / "plain")["release"]
    assert "environment" not in plain
    push = "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    dispatch = "github.event_name == 'workflow_dispatch' && inputs.testpypi"
    expected = str(plain["if"]).replace(push, f"(({push}) || ({dispatch}))")
    assert f"(({push}) || ({dispatch}))" in str(release["if"])
    assert release["if"] == expected


def test_s7_6_4_3_release_steps_pass_testpypi(tmp_path: Path) -> None:
    steps = _release_steps(_pypi_root(tmp_path))
    expected = "${{ github.event_name == 'workflow_dispatch' && inputs.testpypi }}"
    for name in ("Build releases", "Publish releases"):
        step = steps[_step_index(steps, name)]
        assert step["env"]["TESTPYPI"] == expected, name  # type: ignore[index]
    provenance = steps[_step_index(steps, "Generate provenance")]
    assert str(provenance["if"]).endswith(" && env.TESTPYPI != 'true'")
    plain = _release_steps(_lib_root(tmp_path / "plain"))
    for step in plain:
        assert "TESTPYPI" not in str(step)


def _lib_root(path: Path) -> Path:
    return _root(path, "python-lib")


def test_s7_6_4_4_pypi_needs_a_workspace(tmp_path: Path) -> None:
    root = _pypi_root(tmp_path, "python-tool")
    with pytest.raises(ValueError, match=r"ci\.release"):
        _rendered(root)


@pytest.mark.parametrize("sonar", [True, False])
def test_s7_6_4_5_pypi_keeps_every_tag_exists_job(tmp_path: Path, sonar: bool) -> None:
    plain = _ci_jobs(_root(tmp_path / "plain", "python-lib", sonar=sonar))
    pypi = _ci_jobs(_pypi_root(tmp_path / "pypi", sonar=sonar))
    assert list(pypi) == list(plain)
    assert pypi["ci-ok"]["needs"] == plain["ci-ok"]["needs"]
    for name in plain:
        assert pypi[name].get("needs") == plain[name].get("needs"), name
    assert "release" in pypi["ci-ok"]["needs"]  # type: ignore[operator]
    assert "verify-release" in pypi["ci-ok"]["needs"]  # type: ignore[operator]


def test_s7_6_6_1_declared_job_can_write_contents(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\ncontents = "write"\n'
    job = _ci_jobs(_with_ci(_root(tmp_path, "python-tool"), extra))["extra"]
    assert job["permissions"] == {"contents": "write"}


def test_s7_6_6_2_declared_job_reads_by_default(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\n'
    job = _ci_jobs(_with_ci(_root(tmp_path, "python-tool"), extra))["extra"]
    assert job["permissions"] == {"contents": "read"}


def test_s7_6_6_3_bad_contents_is_refused(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\ncontents = "admin"\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


# S9.1.1 — the node setup action.

SETUP_ACTION = ".github/actions/setup/action.yml"


def _node_lib_action(tmp_path: Path, hooks: str = "") -> dict[str, object]:
    root = _root(tmp_path, "node-lib")
    if hooks:
        root = _with_ci(root, hooks)
    return YamlUtils.load(_rendered(root)[SETUP_ACTION])


def test_s9_1_1_1_node_lib_action_inputs_and_steps(tmp_path: Path) -> None:
    action = _node_lib_action(tmp_path)
    inputs = action["inputs"]
    assert list(inputs) == ["start-ci-run", "registry-url", "github-token"]  # type: ignore[arg-type]
    assert inputs["start-ci-run"]["default"] == ""  # type: ignore[index]
    assert inputs["registry-url"]["default"] == ""  # type: ignore[index]
    pins = load_pins()
    steps = action["runs"]["steps"]  # type: ignore[index]

    def uses(key: str) -> str:
        return f"{pins[key]['uses']}@{pins[key]['sha']}"

    assert [s.get("uses", s.get("run")) for s in steps] == [
        uses("pnpm-setup"),
        "pnpm dlx nx start-ci-run $START_CI_RUN",
        uses("setup-node"),
        "pnpm install --frozen-lockfile",
        uses("setup-uv"),
        uses("setup-task"),
    ]
    assert steps[0]["with"] == {"run_install": False}
    assert steps[1]["if"] == "${{ inputs.start-ci-run != '' }}"
    assert steps[2]["with"] == {
        "node-version-file": ".nvmrc",
        "cache": "pnpm",
        "registry-url": "${{ inputs.registry-url }}",
    }
    assert steps[4]["if"] == (
        "${{ hashFiles('**/uv.lock', '!**/node_modules/**') != '' }}"
    )
    assert steps[4]["with"]["cache-dependency-glob"] == "**/uv.lock"
    assert steps[5]["with"]["repo-token"] == "${{ inputs.github-token }}"


def test_s9_1_1_1_hooks_follow_the_setup_task_step(tmp_path: Path) -> None:
    steps = _node_lib_action(tmp_path, HOOKS)["runs"]["steps"]  # type: ignore[index]
    assert [s["name"] for s in steps[-2:]] == [
        "Run ./.github/actions/a",
        "Run ./.github/actions/b",
    ]
    assert "setup-task" in steps[-3]["uses"]


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [
        ("python-app", ""),
        ("python-tool", ""),
        ("python-lib", ""),
        ("python-web-api", ""),
        ("python-web-app", 'frontend = "angular"'),
    ],
)
def test_s9_1_1_2_other_archetypes_render_no_node_lib_action(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    rendered = _rendered(_cell_root(tmp_path, archetype, extra))
    assert "start-ci-run" not in rendered[SETUP_ACTION]
    assert "registry-url" not in rendered[SETUP_ACTION]
    if archetype != "python-web-app":
        assert "npm" not in _updates_of(rendered[".github/dependabot.yml"])


def test_s9_1_1_3_node_lib_dependabot_adds_npm_beside_uv(
    tmp_path: Path,
) -> None:
    updates = YamlUtils.load(
        _rendered(_root(tmp_path, "node-lib"))[".github/dependabot.yml"]
    )["updates"]
    by_ecosystem = {u["package-ecosystem"]: u for u in updates}
    assert set(by_ecosystem) == {"github-actions", "uv", "npm"}
    npm = by_ecosystem["npm"]
    assert npm["directory"] == "/"
    assert npm["schedule"] == {"interval": "weekly"}
    assert list(npm["groups"]) == ["npm"]


# S9.1.10 — the `tools/ci/` helpers are generated.

NODE_HELPERS = tuple(
    f"tools/ci/{name}.mjs"
    for name in (
        "resolve-dist-workspace-deps",
        "verify-dist-manifest",
        "assemble-site",
        "release-notes",
    )
)
NGKIT = Path(__file__).resolve().parents[4] / "ngkit"
NGKIT_REF = "0c2cd2a"


def test_s9_1_10_1_node_lib_renders_the_helpers_and_no_others(tmp_path: Path) -> None:
    rendered = _rendered(_root(tmp_path, "node-lib"))
    assert {p for p in rendered if p.startswith("tools/")} == set(NODE_HELPERS)
    assert not any("check-template" in p for p in rendered)


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [
        ("python-app", ""),
        ("python-tool", ""),
        ("python-lib", ""),
        ("python-web-api", ""),
        ("python-web-app", 'frontend = "angular"'),
    ],
)
def test_s9_1_10_1_other_archetypes_render_none(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    rendered = _rendered(_cell_root(tmp_path, archetype, extra))
    assert not any(p.startswith("tools/") for p in rendered)


def _without_t7(body: str) -> str:
    """Undo S9.1.11's two `assemble-site.mjs` changes, so the rest can be compared with ngkit's."""
    for new, old in T7_HUNKS:
        assert new in body, new
        body = body.replace(new, old)
    return body


T7_HUNKS = (
    (
        " * Assembles the docs site into `dist/site/` (or the directory given as the\n"
        " * first argument) from every project that declares\n",
        " * Assembles the docs site into `dist/site/` from every project that declares\n",
    ),
    (
        " * plus a generated `index.html` (unless the site already has one) and\n"
        " * `.nojekyll`.\n"
        " * Existing content of the site directory is kept.\n",
        " * plus a generated `index.html` and `.nojekyll`.\n",
    ),
    (
        " * Usage: node assemble-site.mjs [site-dir]   (run from the workspace root)",
        " * Usage: node assemble-site.mjs   (run from the workspace root)",
    ),
    ("  readFileSync,\n", "  readFileSync,\n  rmSync,\n"),
    (
        "import { basename, join, resolve } from 'node:path';",
        "import { basename, join } from 'node:path';",
    ),
    (
        "const site = process.argv[2]\n  ? resolve(root, process.argv[2])\n  : join(root, 'dist', 'site');",
        "const site = join(root, 'dist', 'site');",
    ),
    (
        "mkdirSync(site, { recursive: true });",
        "rmSync(site, { recursive: true, force: true });\nmkdirSync(site, { recursive: true });",
    ),
    (
        "if (!existsSync(join(site, 'index.html'))) {\n"
        "  writeFileSync(\n    join(site, 'index.html'),\n    `<!doctype html>",
        "writeFileSync(\n  join(site, 'index.html'),\n  `<!doctype html>",
    ),
    ("</html>\n`,\n  );\n}\n", "</html>\n`,\n);\n"),
)


@pytest.mark.parametrize("path", NODE_HELPERS)
def test_s9_1_10_2_body_is_ngkits_under_t1(tmp_path: Path, path: str) -> None:
    lines = _rendered(_root(tmp_path, "node-lib"))[path].splitlines()
    assert lines[0] == "#!/usr/bin/env node"
    assert lines[1].startswith("// Generated by kiln ")
    assert "ci-template" not in "\n".join(lines)
    if not (NGKIT / ".git").exists():
        pytest.skip("no ngkit checkout beside this repository")
    golden = subprocess.run(
        ["git", "-C", str(NGKIT), "show", f"{NGKIT_REF}:{path}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert golden[0] == lines[0]
    assert golden[1].startswith("// ci-template:")
    body = "\n".join(lines[2:])
    if path.endswith("assemble-site.mjs"):
        body = _without_t7(body)
    assert golden[2:] == body.splitlines()


def test_s9_1_10_3_a_hand_edit_is_drift(tmp_path: Path) -> None:
    root = _root(tmp_path, "node-lib")
    cycle.apply(root, home=tmp_path / "home")
    helper = root / NODE_HELPERS[0]
    helper.write_text(helper.read_text() + "// edit\n", encoding="utf-8")
    codes = [f.code for f in checks.run(root)]
    assert "artifact.drift" in codes


# S9.1.2 — affected CI.

CI_YML = ".github/workflows/ci.yml"
AGENTS = ".nx/workflows/agents.yaml"


def _node_lib_ci(tmp_path: Path) -> dict[str, object]:
    return YamlUtils.load(_rendered(_root(tmp_path, "node-lib"))[CI_YML])


def test_s9_1_2_1_node_lib_jobs_are_the_affected_set(tmp_path: Path) -> None:
    jobs = _node_lib_ci(tmp_path)["jobs"]
    assert list(jobs) == [  # type: ignore[arg-type]
        "validate",
        "dependency-review",
        "secret-scan",
        "test-cloud",
        "test-local",
        "sonar",
        "smoke",
        "release",
        "verify-release",
        "docs",
        "checks-ok",
        "ci-ok",
    ]
    assert jobs["test-cloud"]["needs"] == "validate"  # type: ignore[index]
    assert jobs["test-local"]["needs"] == "validate"  # type: ignore[index]
    python = _ci_jobs(_root(tmp_path / "py", "python-tool"))
    node_validate = jobs["validate"]  # type: ignore[index]
    node_steps = node_validate.pop("steps")
    python_validate = python["validate"]  # type: ignore[index]
    python_steps = python_validate.pop("steps")
    assert node_validate == python_validate
    assert [s.get("name") for s in node_steps] == [s.get("name") for s in python_steps]
    assert [s for s in node_steps if s.get("name") != "Validate"] == [
        s for s in python_steps if s.get("name") != "Validate"
    ]
    assert jobs["dependency-review"] == python["dependency-review"]  # type: ignore[index]


def test_s9_1_2_2_triggers_and_concurrency(tmp_path: Path) -> None:
    ci = _node_lib_ci(tmp_path)
    triggers = ci[True] if True in ci else ci["on"]  # type: ignore[index]
    assert triggers["push"] == {"branches": ["main"]}  # type: ignore[index]
    assert triggers["pull_request"] == {"branches": ["main"]}  # type: ignore[index]
    assert triggers["workflow_dispatch"] == {  # type: ignore[index]
        "inputs": {
            "use-nx-cloud": {
                "description": "Use Nx Cloud distributed CI (leave unchecked to validate on a GitHub runner)",
                "required": False,
                "type": "boolean",
                "default": False,
            }
        }
    }
    assert ci["concurrency"] == {
        "group": "ci-${{ github.ref }}",
        "cancel-in-progress": "${{ github.event_name == 'pull_request' }}",
    }
    assert ci["permissions"] == {"contents": "read"}
    for name in ("test-cloud", "test-local"):
        assert ci["jobs"][name]["permissions"] == {  # type: ignore[index]
            "actions": "read",
            "contents": "read",
        }


def test_s9_1_2_3_ci_cloud_matches_ngkit(tmp_path: Path) -> None:
    job = _node_lib_ci(tmp_path)["jobs"]["test-cloud"]  # type: ignore[index]
    pins = load_pins()
    assert job["if"] == (
        "${{ (github.event_name == 'workflow_dispatch' && inputs.use-nx-cloud) "
        "|| (github.event_name != 'workflow_dispatch' && vars.USE_NX_CLOUD == 'true') }}"
    )
    assert job["env"] == {
        "NX_CLOUD_ACCESS_TOKEN": "${{ secrets.NX_CLOUD_ACCESS_TOKEN }}"
    }
    checkout, setup, shas, affected, fix = job["steps"]
    assert checkout["with"] == {
        "filter": "tree:0",
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    assert setup["uses"].startswith("./.github/actions/setup")
    assert setup["with"]["github-token"] == "${{ secrets.GITHUB_TOKEN }}"
    assert setup["with"]["start-ci-run"] == (
        "--distribute-on=\"${{ vars.NX_CLOUD_AGENTS || '3' }} linux-medium\" "
        '--stop-agents-after="lint,test,build,e2e-ci"'
    )
    assert shas["uses"].startswith(f"nrwl/nx-set-shas@{pins['nx-set-shas']['sha']}")
    assert affected == {"run": "task ci:affected -- lint test build e2e-ci"}
    assert fix == {"run": "pnpm exec nx fix-ci", "if": "always()"}


def test_s9_1_2_4_ci_local_matches_ngkit(tmp_path: Path) -> None:
    job = _node_lib_ci(tmp_path)["jobs"]["test-local"]  # type: ignore[index]
    pins = load_pins()
    assert job["if"] == (
        "${{ (github.event_name == 'workflow_dispatch' && inputs.use-nx-cloud == false) "
        "|| (github.event_name != 'workflow_dispatch' && vars.USE_NX_CLOUD != 'true') }}"
    )
    assert "env" not in job
    checkout, setup, e2e, cache, install, deps, shas, affected = job["steps"]
    assert checkout["with"] == {
        "filter": "tree:0",
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    assert setup["with"] == {"github-token": "${{ secrets.GITHUB_TOKEN }}"}
    assert e2e["id"] == "e2e"
    assert e2e["run"] == 'task ci:has-e2e >> "$GITHUB_OUTPUT"'
    assert cache["uses"].startswith(f"actions/cache@{pins['cache']['sha']}")
    assert cache["id"] == "playwright-cache"
    assert cache["with"]["path"] == "~/.cache/ms-playwright"
    assert install["run"] == "task ci:playwright"
    assert install["if"] == (
        "steps.e2e.outputs.has-e2e == 'true' "
        "&& steps.playwright-cache.outputs.cache-hit != 'true'"
    )
    assert deps["run"] == "task ci:playwright:deps"
    assert deps["if"] == (
        "steps.e2e.outputs.has-e2e == 'true' "
        "&& steps.playwright-cache.outputs.cache-hit == 'true'"
    )
    assert shas["uses"].startswith("nrwl/nx-set-shas@")
    assert affected == {"run": "task ci:affected -- lint test build e2e"}


def test_s9_1_2_6_ci_ok_needs_every_job_and_checks_both_paths(tmp_path: Path) -> None:
    jobs = _node_lib_ci(tmp_path)["jobs"]
    assert jobs["checks-ok"]["needs"] == [  # type: ignore[index]
        "validate",
        "dependency-review",
        "test-cloud",
        "test-local",
        "smoke",
        "sonar",
        "secret-scan",
    ]
    ok = jobs["ci-ok"]  # type: ignore[index]
    assert ok["needs"] == ["checks-ok", "release", "verify-release", "docs"]
    assert ok["if"] == "always()"
    assert ok["permissions"] == {}
    (step,) = ok["steps"]
    assert "jq" not in step["run"]


def test_s9_1_2_6_declared_jobs_join_ci_ok(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\n'
    jobs = _ci_jobs(_with_ci(_root(tmp_path, "node-lib"), extra))
    assert jobs["checks-ok"]["needs"][-1] == "extra"  # type: ignore[index]


def test_s9_1_2_7_agents_yaml_is_ngkits_under_t1(tmp_path: Path) -> None:
    lines = _rendered(_root(tmp_path, "node-lib"))[AGENTS].splitlines()
    assert lines[0].startswith("# Generated by kiln ")
    assert "ci-template" not in "\n".join(lines)
    assert "image: 'ubuntu22.04-node24.14-v1'" in lines[4]
    if not (NGKIT / ".git").exists():
        pytest.skip("no ngkit checkout beside this repository")
    golden = subprocess.run(
        ["git", "-C", str(NGKIT), "show", f"{NGKIT_REF}:{AGENTS}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert golden[0].startswith("# ci-template:")
    assert golden[1:] == lines[1:]


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [
        ("python-app", ""),
        ("python-tool", ""),
        ("python-lib", ""),
        ("python-web-api", ""),
        ("python-web-app", 'frontend = "angular"'),
    ],
)
def test_s9_1_2_other_archetypes_render_no_node_lib_ci(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    rendered = _rendered(_cell_root(tmp_path, archetype, extra))
    assert AGENTS not in rendered
    assert "use-nx-cloud" not in rendered[CI_YML]
    assert "nx-set-shas" not in rendered[CI_YML]


# S9.2.8 — Nx Cloud is opt-in.

CLOUD_IF = (
    "${{ (github.event_name == 'workflow_dispatch' && inputs.use-nx-cloud) "
    "|| (github.event_name != 'workflow_dispatch' && vars.USE_NX_CLOUD == 'true') }}"
)
LOCAL_IF = (
    "${{ (github.event_name == 'workflow_dispatch' && inputs.use-nx-cloud == false) "
    "|| (github.event_name != 'workflow_dispatch' && vars.USE_NX_CLOUD != 'true') }}"
)


def test_s9_2_8_1_ci_cloud_runs_only_when_asked(tmp_path: Path) -> None:
    assert _node_lib_ci(tmp_path)["jobs"]["test-cloud"]["if"] == CLOUD_IF  # type: ignore[index]


def test_s9_2_8_2_ci_local_is_the_default_path(tmp_path: Path) -> None:
    assert _node_lib_ci(tmp_path)["jobs"]["test-local"]["if"] == LOCAL_IF  # type: ignore[index]


def test_s9_2_8_3_dispatch_input_defaults_to_false(tmp_path: Path) -> None:
    ci = _node_lib_ci(tmp_path)
    triggers = ci[True] if True in ci else ci["on"]  # type: ignore[index]
    inputs = triggers["workflow_dispatch"]["inputs"]  # type: ignore[index]
    assert inputs["use-nx-cloud"]["default"] is False


def _evaluate(expression: str, event: str, use_nx_cloud: bool | None, var: str) -> bool:
    """Evaluate one of the two `if` expressions for an event, the dispatch input
    and the repository variable ('' is unset)."""
    python = (
        expression.removeprefix("${{")
        .removesuffix("}}")
        .replace("&&", " and ")
        .replace("||", " or ")
        .replace("github.event_name", "event")
        .replace("inputs.use-nx-cloud", "use_nx_cloud")
        .replace("vars.USE_NX_CLOUD", "var")
        .replace("false", "False")
    )
    return bool(
        eval(python, {}, {"event": event, "use_nx_cloud": use_nx_cloud, "var": var})
    )  # noqa: S307


@pytest.mark.parametrize(
    ("event", "use_nx_cloud", "var", "cloud"),
    [
        ("push", None, "", False),
        ("push", None, "true", True),
        ("push", None, "false", False),
        ("pull_request", None, "", False),
        ("pull_request", None, "true", True),
        ("pull_request", None, "false", False),
        ("workflow_dispatch", True, "", True),
        ("workflow_dispatch", False, "", False),
        ("workflow_dispatch", True, "false", True),
        ("workflow_dispatch", False, "true", False),
    ],
)
def test_s9_2_8_5_exactly_one_of_ci_cloud_and_ci_local_runs(
    tmp_path: Path, event: str, use_nx_cloud: bool | None, var: str, cloud: bool
) -> None:
    jobs = _node_lib_ci(tmp_path)["jobs"]
    ran_cloud = _evaluate(jobs["test-cloud"]["if"], event, use_nx_cloud, var)  # type: ignore[index]
    ran_local = _evaluate(jobs["test-local"]["if"], event, use_nx_cloud, var)  # type: ignore[index]
    assert (ran_cloud, ran_local) == (cloud, not cloud)


def test_s9_2_8_4_web_app_config_has_no_nx_cloud(tmp_path: Path) -> None:
    root = _web_root(tmp_path, "python-web-app", extra="nx_cloud = false")
    with pytest.raises(ModelValidationError) as caught:
        KilnConfig.load(root)
    kinds = {error.path: error.kind for error in caught.value.errors}
    assert kinds["archetype.python-web-app.nx_cloud"] == "extra_forbidden"

    flags = commands._flag_layer(
        archetype="python-web-app",
        docs="none",
        manifest=archetypes.load("python-web-app"),
        allow_untested=False,
    )
    flags["repository"]["name"] = "demo"
    document = commands.ConfigManager().resolve(flags=flags).config.to_document()
    assert "nx_cloud" not in document["archetype"]["python-web-app"]


# S9.1.3 — node Sonar.

SONAR_PROPERTIES = "sonar-project.properties"


def test_s9_1_3_1_sonar_job_matches_ngkit(tmp_path: Path) -> None:
    job = _node_lib_ci(tmp_path)["jobs"]["sonar"]  # type: ignore[index]
    pins = load_pins()
    assert job["needs"] == ["validate", "test-cloud", "test-local"]
    assert job["if"] == (
        "${{ always() && github.actor != 'dependabot[bot]' "
        "&& (needs.test-cloud.result == 'success' || needs.test-local.result == 'success') "
        "&& (github.event_name != 'pull_request' "
        "|| github.event.pull_request.head.repo.full_name == github.repository) }}"
    )
    assert job["timeout-minutes"] == 15
    assert job["permissions"] == {"contents": "read", "pull-requests": "read"}
    checkout, setup, coverage, scan = job["steps"]
    assert checkout["with"] == {"fetch-depth": 0, "persist-credentials": False}
    assert setup["uses"].startswith("./.github/actions/setup")
    assert coverage["id"] == "coverage"
    assert coverage["run"] == 'task ci:coverage >> "$GITHUB_OUTPUT"'
    assert scan["uses"].startswith(
        f"SonarSource/sonarqube-scan-action@{pins['sonarqube-scan']['sha']}"
    )
    assert scan["with"]["args"] == (
        "-Dsonar.javascript.lcov.reportPaths=${{ steps.coverage.outputs.reports }} "
        "-Dsonar.qualitygate.wait=true\n"
    )
    assert scan["env"] == {"SONAR_TOKEN": "${{ secrets.SONAR_TOKEN }}"}


def test_s9_1_3_3_properties_are_ngkits_generic_keys(tmp_path: Path) -> None:
    lines = _rendered(_root(tmp_path, "node-lib"))[SONAR_PROPERTIES].splitlines()
    assert lines[0].startswith("# Generated by kiln ")
    assert "sonar.projectKey=rn-forge_demo" in lines
    assert "sonar.organization=rn-forge" in lines
    assert "sonar.sources=libs,apps" in lines
    assert "sonar.tests=libs,apps" in lines
    assert "sonar.test.inclusions=**/*.spec.ts" in lines
    assert (
        "sonar.exclusions=**/node_modules/**,**/dist/**,**/*.stories.ts,"
        "**/.storybook/**,**/.venv/**"
    ) in lines
    assert not any("python" in line or "coverage.exclusions" in line for line in lines)
    if not (NGKIT / ".git").exists():
        pytest.skip("no ngkit checkout beside this repository")
    golden = subprocess.run(
        ["git", "-C", str(NGKIT), "show", f"{NGKIT_REF}:{SONAR_PROPERTIES}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    for key in (
        "sonar.sources",
        "sonar.tests",
        "sonar.test.inclusions",
        "sonar.exclusions",
    ):
        ours = next(line for line in lines if line.startswith(f"{key}="))
        theirs = next(line for line in golden if line.startswith(f"{key}="))
        if key == "sonar.exclusions":
            assert theirs.startswith(ours)
        else:
            assert ours == theirs


def test_s9_1_3_4_ci_ok_needs_sonar_only_when_sonar_is_on(tmp_path: Path) -> None:
    on = _ci_jobs(_root(tmp_path / "on", "node-lib"))
    assert "sonar" in on["checks-ok"]["needs"]  # type: ignore[index]
    off = _ci_jobs(_root(tmp_path / "off", "node-lib", sonar=False))
    assert "sonar" not in off
    assert "sonar" not in off["checks-ok"]["needs"]  # type: ignore[index]


# S9.1.4 — package.


def test_s9_1_4_1_package_job_matches_ngkit(tmp_path: Path) -> None:
    job = _node_lib_ci(tmp_path)["jobs"]["smoke"]  # type: ignore[index]
    pins = load_pins()
    assert job["needs"] == ["validate", "test-cloud", "test-local"]
    assert job["if"] == (
        "${{ always() && (needs.test-cloud.result == 'success' "
        "|| needs.test-local.result == 'success') }}"
    )
    assert job["timeout-minutes"] == 15
    assert job["permissions"] == {"contents": "read"}
    checkout, setup, pack, upload = job["steps"]
    assert checkout["with"] == {
        "filter": "tree:0",
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    assert setup["uses"].startswith("./.github/actions/setup")
    assert pack["run"] == "task ci:package"
    upload_pin = pins["upload-artifact"]
    assert upload["uses"] == f"{upload_pin['uses']}@{upload_pin['sha']}"
    assert upload["with"] == {
        "name": "package-tarballs",
        "path": "dist/tarballs/*.tgz",
        "retention-days": 14,
    }


def test_s9_1_4_3_ci_ok_needs_smoke_even_without_sonar(tmp_path: Path) -> None:
    on = _ci_jobs(_root(tmp_path / "on", "node-lib"))
    assert on["checks-ok"]["needs"][-2:] == ["sonar", "secret-scan"]  # type: ignore[index]
    off = _ci_jobs(_root(tmp_path / "off", "node-lib", sonar=False))
    assert off["checks-ok"]["needs"][-2:] == ["smoke", "secret-scan"]  # type: ignore[index]
    assert off["ci-ok"]["needs"] == ["checks-ok", "release", "verify-release", "docs"]  # type: ignore[index]
    assert "smoke" in off


# S9.1.11 — one Pages site.

SITE_ROOT = Path(__file__).resolve().parents[3]


def _docs_job(tmp_path: Path) -> dict[str, object]:
    return _node_lib_ci(tmp_path)["jobs"]["docs"]  # type: ignore[index,return-value]


def test_s9_1_11_1_node_lib_renders_no_docs_yml_and_one_docs_job(
    tmp_path: Path,
) -> None:
    rendered = _rendered(_root(tmp_path / "files", "node-lib"))
    assert ".github/workflows/docs.yml" not in rendered
    job = _docs_job(tmp_path / "jobs")
    assert job["needs"] == ["checks-ok", "release", "verify-release"]
    assert job["if"] == (
        "${{ !cancelled() && needs.checks-ok.result == 'success' && "
        "!contains(needs.*.result, 'failure') && "
        "!contains(needs.*.result, 'cancelled') && "
        "github.event_name == 'push' && github.ref_name == 'main' }}"
    )
    assert job["timeout-minutes"] == 30
    assert job["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }
    assert job["environment"] == {
        "name": "github-pages",
        "url": "${{ steps.deployment.outputs.page_url }}",
    }
    assert job["concurrency"] == {"group": "pages", "cancel-in-progress": False}


def test_s9_1_11_1_node_lib_without_mkdocs_has_no_docs_job(tmp_path: Path) -> None:
    jobs = _ci_jobs(_root(tmp_path, "node-lib", profile="none"))
    assert "docs" not in jobs
    assert "docs" not in jobs["ci-ok"]["needs"]  # type: ignore[index,operator]


def test_s9_1_11_2_steps(tmp_path: Path) -> None:
    pins = load_pins()
    steps = _docs_job(tmp_path)["steps"]
    checkout, setup, mkdocs, site, pages, upload, deploy = steps  # type: ignore[misc]
    assert checkout["with"] == {
        "filter": "tree:0",
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    assert setup["uses"].startswith("./.github/actions/setup")
    assert "if" not in mkdocs
    assert mkdocs["run"] == "task docs:build"
    assert site["run"] == "task ci:docs:site"
    for step, name in ((pages, "configure-pages"), (upload, "upload-pages-artifact")):
        assert step["uses"] == f"{pins[name]['uses']}@{pins[name]['sha']}"
    assert upload["with"] == {"path": ".docs-site", "include-hidden-files": True}
    assert deploy["id"] == "deployment"
    assert (
        deploy["uses"]
        == f"{pins['deploy-pages']['uses']}@{pins['deploy-pages']['sha']}"
    )


def test_s9_3_1_3_docs_job_steps_have_no_id_env_or_if(tmp_path: Path) -> None:
    job = _docs_job(tmp_path)
    steps = job["steps"]
    assert [s.get("uses", s.get("run")) for s in steps][2:4] == [  # type: ignore[attr-defined,union-attr]
        "task docs:build",
        "task ci:docs:site",
    ]
    for step in steps:  # type: ignore[attr-defined]
        assert "env" not in step
        assert "if" not in step
        assert step.get("id") in (None, "deployment")
    assert job["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }


def test_s9_3_1_3_nx_set_shas_is_used_twice(tmp_path: Path) -> None:
    text = _root(tmp_path, "node-lib") / CI_YML
    cycle.apply(_root(tmp_path / "r", "node-lib"), home=tmp_path / "home")
    text = (tmp_path / "r" / CI_YML).read_text(encoding="utf-8")
    assert text.count("nrwl/nx-set-shas") == 2


def test_s9_1_11_2_docs_hooks_run_on_the_assembled_site(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "node-lib"), DOCS_HOOKS)
    steps = _job_steps(root, ".github/workflows/ci.yml", "docs")
    site = next(i for i, s in enumerate(steps) if s.get("run") == "task ci:docs:site")
    assert steps[site + 1 : site + 3] == [
        {
            "name": f"Run ./.github/actions/{n}",
            "uses": f"./.github/actions/{n}",
            "env": {"SITE_DIR": ".docs-site"},
        }
        for n in ("a", "b")
    ]


def test_s9_1_11_2_actionlint_passes(tmp_path: Path) -> None:
    if shutil.which("actionlint") is None:
        pytest.skip("actionlint is not on PATH")
    root = _root(tmp_path, "node-lib")
    cycle.apply(root, home=tmp_path / "home")
    result = subprocess.run(
        ["actionlint", ".github/workflows/ci.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _assemble(tmp_path: Path, *args: str, existing: bool) -> Path:
    if shutil.which("node") is None:
        pytest.skip("node is not on PATH")
    root = _root(tmp_path / "cell", "node-lib")
    cycle.apply(root, home=tmp_path / "home")
    stub = tmp_path / "bin"
    stub.mkdir()
    pnpm = stub / "pnpm"
    pnpm.write_text("#!/bin/sh\necho '[]'\n")
    pnpm.chmod(0o755)
    if existing:
        (root / ".docs-site").mkdir()
        (root / ".docs-site" / "index.html").write_text("mkdocs")
        (root / ".docs-site" / "guide.html").write_text("guide")
    subprocess.run(
        ["node", "tools/ci/assemble-site.mjs", *args],
        cwd=root,
        check=True,
        env={**os.environ, "PATH": f"{stub}:{os.environ['PATH']}"},
    )
    return root


def test_s9_1_11_4_site_dir_is_the_first_argument(tmp_path: Path) -> None:
    root = _assemble(tmp_path, ".docs-site", existing=False)
    assert (root / ".docs-site" / "index.html").is_file()
    assert not (root / "dist" / "site").exists()


def test_s9_1_11_4_the_default_site_dir_is_dist_site(tmp_path: Path) -> None:
    root = _assemble(tmp_path, existing=False)
    assert (root / "dist" / "site" / "index.html").is_file()


def test_s9_1_11_4_existing_content_and_index_are_kept(tmp_path: Path) -> None:
    root = _assemble(tmp_path, ".docs-site", existing=True)
    site = root / ".docs-site"
    assert (site / "index.html").read_text() == "mkdocs"
    assert (site / "guide.html").read_text() == "guide"
    assert (site / ".nojekyll").is_file()


def test_s9_3_1_4_no_doc_target_keeps_index_and_makes_no_subsites(
    tmp_path: Path,
) -> None:
    root = _assemble(tmp_path, ".docs-site", existing=True)
    site = root / ".docs-site"
    assert (site / "index.html").read_text() == "mkdocs"
    assert (site / ".nojekyll").is_file()
    assert not (site / "api").exists()
    assert not (site / "storybook").exists()


def test_s9_3_1_5_assemble_site_is_braced_and_its_comment_is_short(
    tmp_path: Path,
) -> None:
    text = _rendered(_root(tmp_path, "node-lib"))["tools/ci/assemble-site.mjs"]
    lines = text.splitlines()
    guard = [ln for ln in lines if ln.startswith("if (!existsSync(")]
    assert guard == ["if (!existsSync(join(site, 'index.html'))) {"]
    start = next(i for i, ln in enumerate(lines) if ln == "/**")
    end = next(i for i, ln in enumerate(lines) if ln == " */")
    assert all(len(ln) <= 80 for ln in lines[start : end + 1])


def test_s9_1_11_6_the_idea_row_is_gone() -> None:
    ideas = (SITE_ROOT / "docs" / "specs" / "ideas" / "index.md").read_text(
        encoding="utf-8"
    )
    assert "node-docs-site-assembly" not in ideas


# S9.1.5 — dispatch release.

RELEASE_YML = ".github/workflows/release.yml"


def test_s9_1_5_1_nx_dispatch_is_node_libs_default(tmp_path: Path) -> None:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        'schema_version = 1\n\n[repository]\nname = "demo"\narchetype = "node-lib"\n',
        encoding="utf-8",
    )
    rendered = _rendered(tmp_path)
    assert RELEASE_YML not in rendered
    assert "release" in YamlUtils.load(rendered[CI_YML])["jobs"]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s9_1_5_1_nx_dispatch_is_refused_elsewhere(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype, release="nx-dispatch")
    with pytest.raises(ValueError, match=r"ci\.release"):
        _rendered(root)


@pytest.mark.parametrize("release", ["tag-exists", "pypi"])
def test_s9_1_5_1_node_lib_refuses_the_other_modes(
    tmp_path: Path, release: str
) -> None:
    root = _root(tmp_path, "node-lib", release=release)
    with pytest.raises(ValueError, match=r"ci\.release"):
        _rendered(root)


def test_s9_1_5_2_release_none_renders_no_release_yml_and_no_release_tasks(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "node-lib", release="none")
    rendered = _rendered(root)
    assert RELEASE_YML not in rendered
    jobs = YamlUtils.load(rendered[CI_YML])["jobs"]
    assert "release" not in jobs
    assert "release" not in jobs["ci-ok"]["needs"]
    config = KilnConfig.load(root)
    tasks = {a.path: a.content for a in TASKS.artifacts(config, root)}["tasks/ci.yml"]
    assert "release:" not in tasks
    assert "published-install" not in tasks


def test_s9_1_5_3_the_rendered_run_lines_name_no_forbidden_tool(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "node-lib")
    cycle.apply(root, home=tmp_path / "home")
    codes = [f.code for f in checks.run(root)]
    assert not [c for c in codes if c.startswith("ci.entrypoint")], codes


# S9.2.4 — one pnpm and Node block in the setup action.

# node-lib's action.yml before S9.2.4, minus the header line, with each pin
# replaced by PIN.
NODE_LIB_ACTION_BEFORE = """name: Setup
description: Install pnpm and Node, uv when the repository commits a uv.lock, optionally start an Nx Cloud CI run, and install dependencies. Run after actions/checkout.

inputs:
  start-ci-run:
    description: Arguments for `nx start-ci-run`; when empty, no Nx Cloud CI run is started
    required: false
    default: ''
  registry-url:
    description: npm registry URL passed to actions/setup-node (needed for npm OIDC publishing)
    required: false
    default: ''
  github-token:
    description: Token for setup-task's release lookup, to avoid rate limits.
    required: true

runs:
  using: composite
  steps:
    - uses: pnpm/action-setup@PIN
      with:
        run_install: false

    - if: ${{ inputs.start-ci-run != '' }}
      env:
        START_CI_RUN: ${{ inputs.start-ci-run }}
      # Unquoted on purpose: the input holds several arguments.
      run: pnpm dlx nx start-ci-run $START_CI_RUN
      shell: bash

    - uses: actions/setup-node@PIN
      with:
        node-version-file: .nvmrc
        cache: pnpm
        registry-url: ${{ inputs.registry-url }}

    - run: pnpm install --frozen-lockfile
      shell: bash

    - if: ${{ hashFiles('**/uv.lock', '!**/node_modules/**') != '' }}
      uses: astral-sh/setup-uv@PIN
      with:
        version: 0.13.1
        enable-cache: true
        cache-dependency-glob: '**/uv.lock'

    - uses: arduino/setup-task@PIN
      with:
        version: 3.x
        repo-token: ${{ inputs.github-token }}
"""


def _web_app_action(tmp_path: Path) -> dict[str, object]:
    root = _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    return YamlUtils.load(_rendered(root)[SETUP_ACTION])


def _step(action: dict[str, object], needle: str) -> dict[str, object]:
    steps = action["runs"]["steps"]  # type: ignore[index]
    return next(s for s in steps if needle in s.get("uses", ""))


def test_s9_2_4_1_pnpm_setup_does_not_install(tmp_path: Path) -> None:
    for action in (
        _node_lib_action(tmp_path / "lib"),
        _web_app_action(tmp_path / "app"),
    ):
        assert _step(action, "pnpm/action-setup")["with"] == {"run_install": False}


def test_s9_2_4_2_setup_node_reads_nvmrc_and_caches_pnpm(tmp_path: Path) -> None:
    lib = _step(_node_lib_action(tmp_path / "lib"), "actions/setup-node")["with"]
    app = _step(_web_app_action(tmp_path / "app"), "actions/setup-node")["with"]
    assert lib == {
        "node-version-file": ".nvmrc",
        "cache": "pnpm",
        "registry-url": "${{ inputs.registry-url }}",
    }
    assert app == {"node-version-file": ".nvmrc", "cache": "pnpm"}


@pytest.mark.parametrize(
    "archetype", ["python-app", "python-tool", "python-lib", "python-web-api"]
)
def test_s9_2_4_3_other_python_archetypes_render_no_pnpm_step(
    tmp_path: Path, archetype: str
) -> None:
    action = _rendered(_cell_root(tmp_path, archetype, ""))[SETUP_ACTION]
    assert "pnpm" not in action
    assert "setup-node" not in action


def test_s9_2_4_4_node_lib_action_is_byte_identical_to_before(tmp_path: Path) -> None:
    text = _rendered(_root(tmp_path, "node-lib"))[SETUP_ACTION].split("\n", 1)[1]
    pinned = re.sub(r"(uses: [\w./-]+)@[0-9a-f]{40} # \S+", r"\1@PIN", text)
    assert pinned == NODE_LIB_ACTION_BEFORE


def test_s9_2_4_5_each_step_is_written_once() -> None:
    template = (
        Path(__file__).resolve().parents[3]
        / "src/rn_forge/kiln/modules/cicd/templates/action.yml.j2"
    )
    text = template.read_text(encoding="utf-8")
    assert text.count('pins["pnpm-setup"].uses') == 1
    assert text.count('pins["setup-node"].uses') == 1


def test_s9_2_5_5_both_node_cells_carry_the_same_npm_block(tmp_path: Path) -> None:
    def updates(root: Path) -> dict[str, object]:
        parsed = YamlUtils.load(_rendered(root)[".github/dependabot.yml"])
        return {u["package-ecosystem"]: u for u in parsed["updates"]}

    lib = updates(_root(tmp_path / "lib", "node-lib"))
    app = updates(
        _web_root(tmp_path / "app", "python-web-app", extra='frontend = "angular"')
    )
    assert "npm" in lib
    assert app["npm"] == lib["npm"]


@pytest.mark.parametrize("archetype", ["python-app", "python-tool", "python-lib"])
def test_s9_2_5_5_python_cells_have_no_npm_block(
    tmp_path: Path, archetype: str
) -> None:
    assert "npm" not in _updates_of(_rendered(_root(tmp_path, archetype))[DEPENDABOT])


def test_s9_2_6_4_web_app_sonar_reads_the_web_lcov_report(tmp_path: Path) -> None:
    properties = _rendered(
        _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    )["sonar-project.properties"].splitlines()
    assert "sonar.javascript.lcov.reportPaths=coverage/web/lcov.info" in properties
    assert "sonar.exclusions=**/node_modules/**,**/dist/**,**/*.spec.ts" in properties


def test_s9_2_6_4_sonar_report_path_keeps_the_project_name(tmp_path: Path) -> None:
    properties = _rendered(
        _web_root(
            tmp_path,
            "python-web-app",
            extra='frontend = "angular"\nweb_dir = "apps/frontend"',
        )
    )["sonar-project.properties"]
    assert "sonar.javascript.lcov.reportPaths=coverage/web/lcov.info" in properties


@pytest.mark.parametrize("archetype", ["python-web-api", "python-tool", "node-lib"])
def test_s9_2_6_4_other_archetypes_name_no_web_report(
    tmp_path: Path, archetype: str
) -> None:
    root = (
        _web_root(tmp_path, archetype)
        if archetype == "python-web-api"
        else _root(tmp_path, archetype)
    )
    properties = _rendered(root)["sonar-project.properties"]
    assert "sonar.javascript.lcov.reportPaths" not in properties
    assert "**/dist/**,**/*.spec.ts" not in properties


# S9.3.2 — a repository declares its Sonar exclusions.

# Each archetype's sonar-project.properties before S9.3.2, with the version in
# the header line replaced by {version}.
SONAR_BEFORE = {
    "python-app": (
        "# Generated by kiln {version} from .rn-forge/kiln/config.toml — do not edit; run 'kiln apply'\n"
        "sonar.projectKey=rn-forge_demo\n"
        "sonar.projectName=demo\n"
        "sonar.organization=rn-forge\n"
        "\n"
        "sonar.sources=src\n"
        "sonar.tests=tests\n"
        "\n"
        "sonar.python.version=3.14\n"
        "sonar.python.coverage.reportPaths=coverage.xml\n"
    ),
    "python-lib": (
        "# Generated by kiln {version} from .rn-forge/kiln/config.toml — do not edit; run 'kiln apply'\n"
        "sonar.projectKey=rn-forge_demo\n"
        "sonar.projectName=demo\n"
        "sonar.organization=rn-forge\n"
        "\n"
        "sonar.sources=packages/alpha/src,packages/beta/src\n"
        "sonar.tests=packages/alpha/tests,packages/beta/tests\n"
        "\n"
        "sonar.python.version=3.14\n"
        "sonar.python.coverage.reportPaths=coverage.xml\n"
    ),
    "python-web-api": (
        "# Generated by kiln {version} from .rn-forge/kiln/config.toml — do not edit; run 'kiln apply'\n"
        "sonar.projectKey=rn-forge_demo\n"
        "sonar.projectName=demo\n"
        "sonar.organization=rn-forge\n"
        "\n"
        "sonar.sources=apps/api/src\n"
        "sonar.tests=apps/api/tests\n"
        "\n"
        "sonar.python.version=3.14\n"
        "sonar.python.coverage.reportPaths=coverage.xml\n"
    ),
    "python-web-app": (
        "# Generated by kiln {version} from .rn-forge/kiln/config.toml — do not edit; run 'kiln apply'\n"
        "sonar.projectKey=rn-forge_demo\n"
        "sonar.projectName=demo\n"
        "sonar.organization=rn-forge\n"
        "\n"
        "sonar.sources=apps/api/src,apps/web/src\n"
        "sonar.tests=apps/api/tests\n"
        "sonar.javascript.lcov.reportPaths=coverage/web/lcov.info\n"
        "sonar.exclusions=**/node_modules/**,**/dist/**,**/*.spec.ts\n"
        "\n"
        "sonar.python.version=3.14\n"
        "sonar.python.coverage.reportPaths=coverage.xml\n"
    ),
    "node-lib": (
        "# Generated by kiln {version} from .rn-forge/kiln/config.toml — do not edit; run 'kiln apply'\n"
        "sonar.projectKey=rn-forge_demo\n"
        "sonar.projectName=demo\n"
        "sonar.organization=rn-forge\n"
        "\n"
        "sonar.sources=libs,apps\n"
        "sonar.tests=libs,apps\n"
        "sonar.test.inclusions=**/*.spec.ts\n"
        "sonar.exclusions=**/node_modules/**,**/dist/**,**/*.stories.ts,**/.storybook/**,**/.venv/**\n"
    ),
}


def _sonar(root: Path) -> str:
    return _rendered(root)["sonar-project.properties"]


def _sonar_root(tmp_path: Path, archetype: str, extra: str = "") -> Path:
    if archetype == "python-web-app":
        root = _web_root(tmp_path, archetype, extra='frontend = "angular"')
    elif archetype == "python-web-api":
        root = _web_root(tmp_path, archetype)
    else:
        root = _root(tmp_path, archetype)
    return _with_ci(root, extra) if extra else root


NGKIT_COVERAGE_EXCLUSIONS = (
    'sonar_coverage_exclusions = ["tools/scripts/patch-package-exports.mjs", '
    '"apps/*-e2e/**", "apps/*/src/environments/**", '
    '"apps/*/src/app/app.config.ts"]\n'
)


def test_s9_3_2_1_ci_config_accepts_both_lists_under_every_archetype(
    tmp_path: Path,
) -> None:
    for archetype in SONAR_BEFORE:
        root = _sonar_root(
            tmp_path / archetype,
            archetype,
            'sonar_exclusions = ["a/**"]\nsonar_coverage_exclusions = ["b/**"]\n',
        )
        ci = KilnConfig.load(root).document.ci  # type: ignore[attr-defined]
        assert ci.sonar_exclusions == ["a/**"]
        assert ci.sonar_coverage_exclusions == ["b/**"]
        plain = KilnConfig.load(_sonar_root(tmp_path / f"{archetype}-plain", archetype))
        assert plain.document.ci.sonar_exclusions == []  # type: ignore[attr-defined]
        assert plain.document.ci.sonar_coverage_exclusions == []  # type: ignore[attr-defined]


@pytest.mark.parametrize("key", ["sonar_exclusions", "sonar_coverage_exclusions"])
@pytest.mark.parametrize("entry", ['""', '"a,b"', '"a\\nb"'])
def test_s9_3_2_2_a_bad_entry_is_refused(tmp_path: Path, key: str, entry: str) -> None:
    root = _sonar_root(tmp_path, "node-lib", f"{key} = [{entry}]\n")
    with pytest.raises(ModelValidationError) as caught:
        KilnConfig.load(root)
    assert {(error.path, error.kind) for error in caught.value.errors} == {
        (f"ci.{key}", "value_error")
    }


def test_s9_3_2_3_node_lib_appends_the_repository_s_exclusions(
    tmp_path: Path,
) -> None:
    root = _sonar_root(
        tmp_path,
        "node-lib",
        'sonar_exclusions = ["apps/ng-demo-api/**", "apps/ng-demo-api-fastapi/**"]\n',
    )
    assert (
        "sonar.exclusions=**/node_modules/**,**/dist/**,**/*.stories.ts,"
        "**/.storybook/**,**/.venv/**,apps/ng-demo-api/**,"
        "apps/ng-demo-api-fastapi/**\n"
    ) in _sonar(root)


@pytest.mark.parametrize("archetype", list(SONAR_BEFORE))
def test_s9_3_2_4_coverage_exclusions_render_in_every_archetype(
    tmp_path: Path, archetype: str
) -> None:
    root = _sonar_root(tmp_path, archetype, NGKIT_COVERAGE_EXCLUSIONS)
    lines = _sonar(root).splitlines()
    assert (
        "sonar.coverage.exclusions=tools/scripts/patch-package-exports.mjs,"
        "apps/*-e2e/**,apps/*/src/environments/**,apps/*/src/app/app.config.ts"
    ) in lines


@pytest.mark.parametrize("archetype", list(SONAR_BEFORE))
def test_s9_3_2_4_empty_coverage_exclusions_render_no_line(
    tmp_path: Path, archetype: str
) -> None:
    assert "coverage.exclusions" not in _sonar(_sonar_root(tmp_path, archetype))


@pytest.mark.parametrize("archetype", list(SONAR_BEFORE))
def test_s9_3_2_5_empty_lists_render_what_the_archetype_rendered_before(
    tmp_path: Path, archetype: str
) -> None:
    text = _sonar(_sonar_root(tmp_path, archetype))
    assert text == SONAR_BEFORE[archetype].format(version=__version__)


def test_s9_3_2_6_exclusions_follow_sonar_tests_in_a_plain_archetype(
    tmp_path: Path,
) -> None:
    lines = _sonar(
        _sonar_root(tmp_path, "python-app", 'sonar_exclusions = ["docs/**"]\n')
    ).splitlines()
    assert lines[lines.index("sonar.tests=tests") + 1] == "sonar.exclusions=docs/**"


def test_s9_3_2_6_web_app_appends_to_its_own_exclusions(tmp_path: Path) -> None:
    root = _sonar_root(tmp_path, "python-web-app", 'sonar_exclusions = ["docs/**"]\n')
    assert (
        "sonar.exclusions=**/node_modules/**,**/dist/**,**/*.spec.ts,docs/**\n"
    ) in _sonar(root)


def test_s9_3_2_7_standard_names_both_keys_in_its_ci_example() -> None:
    standard = (
        Path(__file__).resolve().parents[3] / "docs/reference/standard-repo.md"
    ).read_text(encoding="utf-8")
    example = standard[standard.index('provider = "github"') :]
    assert "sonar_exclusions = []" in example
    assert "sonar_coverage_exclusions = []" in example


# S9.3.4 — validate runs only the checks that do not run Nx.


def test_s9_3_4_3_validate_step_runs_ci_validate(
    tmp_path: Path,
) -> None:
    expected = {
        "python-app": "task ci:validate",
        "python-tool": "task ci:validate",
        "python-lib": "task lint",
        "node-lib": "task ci:validate",
    }
    for archetype, run in expected.items():
        root = _root(tmp_path / archetype, archetype)
        workflow = _rendered(root)[".github/workflows/ci.yml"]
        job = YamlUtils.load(workflow)["jobs"]["validate"]
        step = next(s for s in job["steps"] if s["name"] == "Validate")
        assert step["run"] == run, archetype
        assert step["env"]["KILN_DOCTOR_FULL"] == KILN_DOCTOR_FULL_EXPRESSION, archetype
        assert job["timeout-minutes"] == 20, archetype
        comment = "# The Nx projects are checked by test-cloud or test-local; this job runs the rest."
        assert (comment in workflow) == (archetype == "node-lib"), archetype


# S9.3.7 — small corrections to the node files.


def test_s9_3_7_2_gate_comment_is_one_text_for_every_archetype(
    tmp_path: Path,
) -> None:
    for archetype in ("node-lib", "python-app", "python-lib"):
        ci = _rendered(_root(tmp_path / archetype, archetype))[
            ".github/workflows/ci.yml"
        ]
        assert "a\n  # release or deploy on a pull request" in ci, archetype


def test_s9_3_7_3_setup_uv_pin_is_v10_3_0(tmp_path: Path) -> None:
    sha = "1c37ad07a6a961277cf70c0d37d6f313000f5884"
    assert UPSTREAM_PINS["setup-uv"] == (sha, "v10.3.0")
    uses = f"astral-sh/setup-uv@{sha} # v10.3.0"
    cases = [(a, _root(tmp_path / a, a)) for a in (*ARCHETYPES, "node-lib")]
    cases += [
        ("python-web-api", _web_root(tmp_path / "api", "python-web-api")),
        (
            "python-web-app",
            _web_root(tmp_path / "app", "python-web-app", extra='frontend = "angular"'),
        ),
    ]
    for archetype, root in cases:
        action = _rendered(root)[".github/actions/setup/action.yml"]
        assert uses in action, archetype


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_1_2_7_umbrella_needs_a_release(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype, release="none")
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8") + "\n[ci.checks]\numbrella-release = true\n",
        encoding="utf-8",
    )
    with pytest.raises(
        AppException,
        match=r"cicd\.render: ci\.checks\.umbrella-release needs \[ci\] release other than none",
    ):
        _rendered(root)
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'release = "none"', 'release = "tag-exists"'
        ),
        encoding="utf-8",
    )
    assert ".github/workflows/ci.yml" in _rendered(root)


# S15.6.1 — kiln renders `scorecard.yml`.

SCORECARD = ".github/workflows/scorecard.yml"


def _scorecard_root(tmp_path: Path, archetype: str) -> Path:
    return _with_ci(_root(tmp_path, archetype), "\n[ci.checks]\nscorecard = true\n")


@pytest.mark.parametrize("archetype", [*ARCHETYPES, "node-lib"])
def test_s15_6_1_1_absent_by_default(tmp_path: Path, archetype: str) -> None:
    assert SCORECARD not in _rendered(_root(tmp_path, archetype))


@pytest.mark.parametrize("archetype", [*ARCHETYPES, "node-lib"])
def test_s15_6_1_2_on(tmp_path: Path, archetype: str) -> None:
    workflow = YamlUtils.load(
        _rendered(_scorecard_root(tmp_path, archetype))[SCORECARD]
    )
    assert workflow["on"]["schedule"] == [{"cron": "17 4 * * 1"}]
    assert "workflow_dispatch" in workflow["on"]
    assert list(workflow["jobs"]) == ["analysis"]
    job = workflow["jobs"]["analysis"]
    assert job["permissions"] == {
        "contents": "read",
        "actions": "read",
        "id-token": "write",
        "security-events": "write",
    }
    pins = load_pins()
    checkout, scan, upload = job["steps"]
    assert checkout["uses"] == f"{pins['checkout']['uses']}@{pins['checkout']['sha']}"
    assert checkout["with"] == {"persist-credentials": False}
    assert scan["uses"] == f"{pins['scorecard']['uses']}@{pins['scorecard']['sha']}"
    assert scan["with"] == {
        "results_file": "results.sarif",
        "results_format": "sarif",
        "publish_results": True,
    }
    assert (
        upload["uses"]
        == f"{pins['upload-sarif']['uses']}@{pins['upload-sarif']['sha']}"
    )
    assert upload["uses"].startswith("github/codeql-action/upload-sarif@")
    assert upload["with"] == {"sarif_file": "results.sarif"}


@pytest.mark.parametrize("archetype", [*ARCHETYPES, "node-lib"])
def test_s15_6_1_3_not_gating(tmp_path: Path, archetype: str) -> None:
    jobs = _ci_jobs(_scorecard_root(tmp_path, archetype))
    assert "scorecard" not in jobs
    assert "scorecard" not in jobs["ci-ok"]["needs"]


@pytest.mark.parametrize("archetype", [*ARCHETYPES, "node-lib"])
def test_s15_6_1_4_pins(tmp_path: Path, archetype: str) -> None:
    root = _scorecard_root(tmp_path, archetype)
    assert "ci.unpinned" not in _codes(root)
    assert "ci.permissions" not in _codes(root)
    rendered = _rendered(root)[SCORECARD]
    pins = load_pins()
    for key in ("scorecard", "upload-sarif"):
        assert f"@{pins[key]['sha']} # {pins[key]['version']}" in rendered


def test_s15_6_1_5_generated_job_name(tmp_path: Path) -> None:
    assert "scorecard" in GENERATED_JOBS
    extra = f'\n[[ci.jobs]]\nname = "scorecard"\nuses = "{CALL}"\n'
    root = _with_ci(_root(tmp_path, "python-lib"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def _actions_entry(root: Path) -> dict[str, object]:
    return _updates(root)["github-actions"]


def _unique_uses(pins: dict[str, dict[str, str]]) -> list[str]:
    return sorted(
        {"/".join(t["uses"].split("/")[:2]) for t in pins.values() if "uses" in t}
    )


@pytest.mark.parametrize("archetype", ARCHETYPES + ("node-lib",))
def test_s15_7_1_1_github_actions_entry(tmp_path: Path, archetype: str) -> None:
    updates = _updates(_root(tmp_path, archetype))
    entry = updates["github-actions"]
    assert entry["directory"] == "/"
    for key in ("schedule", "cooldown"):
        assert entry[key] == updates["uv"][key]
    assert next(iter(entry["groups"].values())) == next(  # type: ignore[attr-defined]
        iter(updates["uv"]["groups"].values())  # type: ignore[attr-defined]
    )


@pytest.mark.parametrize("archetype", ARCHETYPES + ("node-lib",))
def test_s15_7_1_2_ignore_covers_every_pin(tmp_path: Path, archetype: str) -> None:
    names = [
        i["dependency-name"]
        for i in _actions_entry(_root(tmp_path, archetype))["ignore"]
    ]  # type: ignore[attr-defined,index]
    assert names == sorted(set(names))
    assert names == _unique_uses(load_pins())
    assert "actions/checkout" in names
    assert "github/codeql-action" in names
    assert not any(n.count("/") != 1 for n in names)


def test_s15_7_1_3_new_pin_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pins = load_pins() | {"extra": {"uses": "x/y", "sha": "0" * 40, "version": "v1"}}
    monkeypatch.setattr("rn_forge.kiln.modules.cicd.artifacts.load_pins", lambda: pins)
    names = [i["dependency-name"] for i in _actions_entry(_root(tmp_path))["ignore"]]  # type: ignore[attr-defined,index]
    assert "x/y" in names


# S15.5.2 — an `umbrella` job runs `kiln-devops umbrella`.

UMBRELLA_ARCHETYPES = (*ARCHETYPES, "python-web-api", "python-web-app")
UMBRELLA_IF = (
    "${{ !cancelled() && needs.checks-ok.result == 'success' && "
    "needs.release.result != 'failure' && github.event_name == 'push' && "
    "github.ref == 'refs/heads/main' }}"
)


def _umbrella_root(tmp_path: Path, archetype: str, on: bool) -> Path:
    root = _sonar_root(tmp_path, archetype)
    if on:
        config = root / ".rn-forge" / "kiln" / "config.toml"
        config.write_text(
            config.read_text(encoding="utf-8")
            + "\n[ci.checks]\numbrella-release = true\n",
            encoding="utf-8",
        )
    return root


def _umbrella_files(
    root: Path,
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    jobs = _ci_jobs(root)
    return jobs, _ci_tasks_text_of(root)["tasks"]  # type: ignore[return-value]


@pytest.mark.parametrize("archetype", [*UMBRELLA_ARCHETYPES, "node-lib"])
def test_s15_5_2_1_off_by_default(tmp_path: Path, archetype: str) -> None:
    jobs, tasks = _umbrella_files(_umbrella_root(tmp_path, archetype, False))
    assert "umbrella" not in jobs
    assert "release:umbrella" not in tasks


@pytest.mark.parametrize("archetype", UMBRELLA_ARCHETYPES)
def test_s15_5_2_2_on(tmp_path: Path, archetype: str) -> None:
    jobs, tasks = _umbrella_files(_umbrella_root(tmp_path, archetype, True))
    job = jobs["umbrella"]
    assert job["needs"] == ["checks-ok", "release"]
    assert job["permissions"] == {"contents": "write"}
    assert job["concurrency"] == {"group": "release", "cancel-in-progress": False}
    steps = job["steps"]
    assert "actions/checkout" in steps[0]["uses"]  # type: ignore[index]
    assert steps[1]["uses"] == "./.github/actions/setup"  # type: ignore[index]
    assert steps[2]["run"] == "task ci:release:umbrella"  # type: ignore[index]
    assert len(steps) == 3  # type: ignore[arg-type]
    assert steps[2]["env"] == {"GH_TOKEN": "${{ github.token }}"}  # type: ignore[index]
    for name, other in jobs.items():
        if name != "umbrella":
            assert "umbrella" not in str(other.get("steps", "")), name
    assert tasks["release:umbrella"]["cmds"] == [  # type: ignore[index]
        '{{.DEVOPS}} umbrella --sha "$GITHUB_SHA"'
    ]


@pytest.mark.parametrize("archetype", UMBRELLA_ARCHETYPES)
def test_s15_5_2_3_needs_a_release(tmp_path: Path, archetype: str) -> None:
    root = _umbrella_root(tmp_path, archetype, True)
    config = root / ".rn-forge" / "kiln" / "config.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text + '\n[ci]\nrelease = "none"\n'
        if "[ci]" not in text
        else text.replace('release = "tag-exists"', 'release = "none"'),
        encoding="utf-8",
    )
    with pytest.raises(
        AppException,
        match=r"cicd\.render: ci\.checks\.umbrella-release needs \[ci\] release other than none",
    ):
        _rendered(root)


@pytest.mark.parametrize("archetype", UMBRELLA_ARCHETYPES)
def test_s15_5_2_4_docs_only_shipped_transition(tmp_path: Path, archetype: str) -> None:
    jobs = _ci_jobs(_umbrella_root(tmp_path, archetype, True))
    assert jobs["umbrella"]["if"] == UMBRELLA_IF
    assert "release-order" not in str(jobs["umbrella"]["if"])
    if archetype == "python-lib":
        assert "release-order != '[]'" in str(jobs["release"]["if"])


@pytest.mark.parametrize("archetype", UMBRELLA_ARCHETYPES)
def test_s15_5_2_5_ci_ok(tmp_path: Path, archetype: str) -> None:
    on = _ci_jobs(_umbrella_root(tmp_path / "on", archetype, True))
    assert "umbrella" in on["ci-ok"]["needs"]  # type: ignore[operator]
    off = _ci_jobs(_umbrella_root(tmp_path / "off", archetype, False))
    assert "umbrella" not in off["ci-ok"]["needs"]  # type: ignore[operator]
