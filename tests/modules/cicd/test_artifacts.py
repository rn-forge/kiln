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


def test_s4_3_4_5_python_lib_matrix_lists_every_package_basename(
    tmp_path: Path,
) -> None:
    rendered = _rendered(_root(tmp_path, "python-lib"))
    jobs = yaml.safe_load(rendered[".github/workflows/ci.yml"])["jobs"]
    assert jobs["release"]["strategy"]["matrix"]["package"] == ["alpha", "beta"]


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
    return [_root(tmp_path / archetype, archetype) for archetype in ARCHETYPES]


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
        assert step["run"] == "task validate"
        assert step["env"]["KILN_DOCTOR_FULL"] == KILN_DOCTOR_FULL_EXPRESSION, archetype
