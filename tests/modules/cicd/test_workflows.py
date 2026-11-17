"""The `cicd` module's artifacts: workflows, the setup action, Sonar.

Also proves the properties every concern module owes: its template inventory,
create-only apply into an empty directory, idempotence, and passing checks.
"""

from __future__ import annotations
import pytest
import subprocess
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.generation import Action, ArtifactKind
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd import CICD
from rn_forge.kiln.modules.core import cycle
from tests.conftest import actions as _actions, requires
from tests.modules.cicd import workflows
from tests.modules.cicd.support import (
    ARCHETYPES,
    CI_KEYS,
    WORKFLOWS,
    _codes,
    _rendered,
    _root,
    _web_root,
)


def _keys(archetype: str, keys: tuple[str, ...] = CI_KEYS) -> tuple[str, ...]:
    """The rows `archetype` renders: the same for every archetype now, but a library workspace runs `release` inline in `ci.yml`."""
    if archetype == "python-lib":
        return tuple(k for k in keys if not k.endswith("/_release.yml"))
    return keys


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_renders_exactly_the_module_s_template_inventory_rows(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    artifacts = CICD.artifacts(KilnConfig.load(root), root)
    assert [(a.path, a.kind) for a in artifacts] == [
        (path, ArtifactKind.MANAGED) for path in _keys(archetype)
    ]


def test_without_mkdocs_or_sonar_renders_three_rows(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, profile="none", sonar=False)
    assert list(_rendered(root)) == [
        *CI_KEYS[:3],
        ".github/workflows/_smoke.yml",
        ".github/workflows/_release.yml",
        ".github/workflows/_verify-release.yml",
        ".github/dependabot.yml",
    ]


def test_ado_is_reserved(tmp_path: Path) -> None:
    root = _root(tmp_path, provider="ado")
    with pytest.raises(AppException, match="E8"):
        _rendered(root)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_into_an_empty_directory_only_creates(tmp_path: Path, archetype: str) -> None:
    actions = _actions(_root(tmp_path, archetype), tmp_path)
    assert {actions[key] for key in _keys(archetype)} == {Action.CREATE}


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_a_second_apply_is_unchanged(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    actions = _actions(root, tmp_path)
    assert {actions[key] for key in _keys(archetype)} == {Action.UNCHANGED}


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_checks_pass_on_the_rendered_output(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    assert _codes(root) == []


def test_entrypoint_fails_on_a_direct_uv_call(tmp_path: Path) -> None:
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
@requires("actionlint")
def test_actionlint_passes_on_every_rendered_workflow(
    tmp_path: Path, archetype: str, sonar: bool
) -> None:
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


def test_ci_pins_passes_on_the_rendered_output(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    cycle.apply(root, home=tmp_path / "home")
    assert not [c for c in _codes(root) if c.startswith("ci.")]


def test_sonar_off_renders_no_sonar_job_and_release_needs_validate(
    tmp_path: Path,
) -> None:
    on = _rendered(_root(tmp_path / "on"))
    off = _rendered(_root(tmp_path / "off", sonar=False))
    assert "sonar-project.properties" not in off
    jobs = workflows.jobs(off)
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


def test_release_none_renders_no_release_job(tmp_path: Path) -> None:
    rendered = _rendered(_root(tmp_path, release="none"))
    jobs = workflows.jobs(rendered)
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


def test_ci_entrypoint_passes_on_the_rendered_workflows(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    assert "ci.entrypoint" not in _codes(root)


def test_ci_entrypoint_fails_on_a_fixture_calling_uv(repo) -> None:
    root = repo(
        **{
            ".github__workflows__ci.yml": (
                "jobs:\n  a:\n    permissions: {}\n    steps:\n      - run: uv sync\n"
            )
        }
    )
    assert _codes(root) == ["ci.entrypoint"]


def test_only_python_web_app_s_setup_action_sets_up_pnpm_and_node(
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


def test_sonar_properties_web_api_uses_api_dir(tmp_path: Path) -> None:
    rendered = _rendered(_web_root(tmp_path, "python-web-api"))
    properties = rendered["sonar-project.properties"]
    assert "sonar.sources=apps/api/src" in properties
    assert "sonar.tests=apps/api/tests" in properties


def test_sonar_properties_web_app_adds_web_dir_to_sources(
    tmp_path: Path,
) -> None:
    rendered = _rendered(
        _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    )
    properties = rendered["sonar-project.properties"]
    assert "sonar.sources=apps/api/src,apps/web/src" in properties
    assert "sonar.tests=apps/api/tests" in properties


def test_ci_pins_passes_on_the_web_app_setup_action(tmp_path: Path) -> None:
    root = _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    cycle.apply(root, home=tmp_path / "home")
    assert not [c for c in _codes(root) if c.startswith("ci.")]


@pytest.mark.parametrize("sonar", [True, False])
@requires("actionlint")
def test_actionlint_passes_on_web_app_workflows(tmp_path: Path, sonar: bool) -> None:
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
