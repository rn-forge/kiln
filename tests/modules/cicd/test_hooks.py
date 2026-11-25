"""Setup hooks and declared jobs in the rendered workflows."""

from __future__ import annotations
import pytest
import subprocess
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.checks import hooks as hooks_check, pins as pins_check
from rn_forge.kiln.modules.cicd.config import GENERATED_JOBS
from rn_forge.kiln.modules.core import cycle
from tests.conftest import requires
from tests.modules.cicd.support import (
    ARCHETYPES,
    CALL,
    HOOKS,
    _action,
    _ci_jobs,
    _rendered,
    _root,
    _web_root,
    _with_ci,
)


UMBRELLA = "\n[ci.checks]\numbrella-release = true\n"

GOLDEN_RENDER = (
    '\n[[ci.jobs]]\nname = "golden-render"\n'
    'uses = "./.github/workflows/golden-render.yml"\n'
    'events = ["pull_request"]\n'
)


def test_node_off_renders_no_node_steps(tmp_path: Path) -> None:
    action = _action(_root(tmp_path, "python-tool"))
    assert "pnpm/action-setup" not in action
    assert "actions/setup-node" not in action


def test_web_app_keeps_node(tmp_path: Path) -> None:
    web = _action(
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"')
    )
    assert "pnpm/action-setup" in web
    assert "actions/setup-node" in web
    assert "cache: pnpm" in web
    assert "\n\n\n" not in web


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [
        ("node-lib", ""),
        ("python-tool", ""),
        ("python-lib", ""),
        ("python-app", ""),
        ("python-tool", UMBRELLA),
    ],
)
def test_every_rendered_job_is_reserved(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _root(tmp_path, archetype)
    if extra:
        root = _with_ci(root, extra)
    jobs = set(YamlUtils.load(_rendered(root)[".github/workflows/ci.yml"])["jobs"])
    assert jobs <= GENERATED_JOBS, jobs - GENERATED_JOBS


def test_no_declared_jobs_is_unchanged(tmp_path: Path) -> None:
    roots = [_root(tmp_path / a, a) for a in ARCHETYPES] + [
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"')
    ]
    for root in roots:
        plain = _rendered(root)[".github/workflows/ci.yml"]
        empty = _rendered(_with_ci(root, "jobs = []\n"))[".github/workflows/ci.yml"]
        assert plain == empty, root.name
        assert set(YamlUtils.load(plain)["jobs"]) <= GENERATED_JOBS, root.name
        assert "\n\n\n" not in plain, root.name


def _hook_steps(action: str) -> list[dict[str, str]]:
    return YamlUtils.load(action)["runs"]["steps"]


def test_setup_hooks_render_last_and_in_order(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), HOOKS)
    steps = _hook_steps(_action(root))
    assert steps[-3]["name"] == "Install go-task"
    assert steps[-2:] == [
        {"name": "Run ./.github/actions/a", "uses": "./.github/actions/a"},
        {"name": "Run ./.github/actions/b", "uses": "./.github/actions/b"},
    ]


def test_hooks_follow_the_node_steps(tmp_path: Path) -> None:
    root = _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    plain = _hook_steps(_action(root))
    steps = _hook_steps(_action(_with_ci(root, HOOKS)))
    assert steps[: len(plain)] == plain
    assert "actions/setup-node" in steps[len(plain) - 1]["uses"]
    assert [s["name"] for s in steps[len(plain) :]] == [
        "Run ./.github/actions/a",
        "Run ./.github/actions/b",
    ]


def test_no_hooks_is_byte_identical(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-tool")
    plain = _action(root)
    empty = _action(_with_ci(root, "hooks = { setup = [] }\n"))
    assert plain == empty
    assert "Run ./" not in plain
    assert "\n\n\n" not in plain


def test_web_app_still_renders_node_steps(tmp_path: Path) -> None:
    web = _action(
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"')
    )
    assert "pnpm/action-setup" in web
    assert "actions/setup-node" in web
    assert "cache: pnpm" in web


def test_node_key_is_refused(tmp_path: Path) -> None:
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
def test_bad_hook_paths_are_refused(tmp_path: Path, path: str) -> None:
    root = _with_ci(
        _root(tmp_path, "python-tool"), f'\n[ci.hooks]\nsetup = ["{path}"]\n'
    )
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_duplicate_hooks_are_refused(tmp_path: Path) -> None:
    extra = '\n[ci.hooks]\nsetup = ["./.github/actions/a", "./.github/actions/a"]\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_declared_job_renders_as_a_call(tmp_path: Path) -> None:
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


def test_declared_job_defaults_to_every_event(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\n'
    job = _ci_jobs(_with_ci(_root(tmp_path, "python-tool"), extra))["extra"]
    assert "if" not in job


def test_declared_job_with_two_events_ors_them(tmp_path: Path) -> None:
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
def test_bad_uses_is_refused(tmp_path: Path, uses: str) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{uses}"\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_task_key_is_refused(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\ntask = "validate"\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


@pytest.mark.parametrize(
    "name",
    [
        "sonar",
        "validate",
        "ci-ok",
        "checks-ok",
        "Golden",
        "a_b",
        "test-cloud",
        "test-local",
        "umbrella",
        "evidence",
    ],
)
def test_job_name_collision_is_refused(tmp_path: Path, name: str) -> None:
    extra = f'\n[[ci.jobs]]\nname = "{name}"\nuses = "{CALL}"\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_duplicate_declared_names_are_refused(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "a"\nuses = "{CALL}"\n' * 2
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


@requires("actionlint")
def test_actionlint_passes_on_a_declared_call(tmp_path: Path) -> None:
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
def test_every_cell_passes_ci_pins_and_ci_hooks(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    if archetype.startswith("python-web"):
        root = _web_root(tmp_path, archetype, extra=extra)
    else:
        root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    assert pins_check.check(KilnConfig.load(root), root) == []
    assert hooks_check.check(KilnConfig.load(root), root) == []
