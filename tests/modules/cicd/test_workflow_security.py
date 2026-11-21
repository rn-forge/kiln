"""Workflow security: credentials, pins, Dependabot."""

from __future__ import annotations
import pytest
import re
import subprocess
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.commons.generation import Action, ArtifactKind
from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd import CICD
from rn_forge.kiln.modules.core.pins import load_pins
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.docs import generate
from tests.conftest import actions as _actions, requires
from tests.modules.cicd import workflows
from tests.modules.cicd.support import (
    CI_KEYS,
    DEPENDABOT,
    SECURITY_CELLS,
    _cell_root,
    _ci_tasks_text_of,
    _dependabot,
    _hook_entry,
    _lib_jobs,
    _release_roots,
    _release_steps,
    _rendered,
    _root,
    _step_index,
    _updates,
    _with_ci,
)


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
def test_checkouts_do_not_persist_credentials(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    checkouts = _checkouts(_cell_root(tmp_path, archetype, extra))
    assert checkouts
    for path, job, step in checkouts:
        if archetype == "python-lib" and job == "docs":
            continue
        assert step["with"]["persist-credentials"] is False, f"{path}:{job}"  # type: ignore[index]


def test_the_python_lib_docs_job_keeps_credentials(tmp_path: Path) -> None:
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
def test_docs_job_comment(tmp_path: Path, archetype: str, extra: str) -> None:
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
    ci = workflows.jobs(rendered)
    if "docs" in ci and archetype == "python-lib":
        assert (
            "persist-credentials: true # mike pushes gh-pages with this token"
            in (rendered[".github/workflows/_docs.yml"])
        )


def test_fetch_depth_is_kept(tmp_path: Path) -> None:
    lib = _checkouts(_root(tmp_path, "python-lib"))
    deep = {job for _, job, step in lib if step["with"].get("fetch-depth") == 0}  # type: ignore[union-attr]
    assert {"plan", "sonar", "verify-release"} <= deep


def test_the_release_version_is_read_through_env(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        for step in steps:
            if "run" in step:
                assert "${{" not in str(step["run"]), (root.name, step.get("name"))
        tasks = _ci_tasks_text_of(root)["tasks"]
        assert tasks["release:state"]["cmds"] == [  # type: ignore[index]
            '{{.DEVOPS}} release-state "v$({{.TASK_EXE}} version)"'
        ]


def test_release_publishes_with_gh_release_create(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        publish = steps[_step_index(steps, "Publish GitHub Release")]
        assert "uses" not in publish
        assert "with" not in publish
        assert publish["run"] == "task ci:release:publish"
        env = publish["env"]  # type: ignore[index]
        assert env == {
            "GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
            "TAG": "${{ steps.check.outputs.tag }}",
            "SOURCE_SHA": "${{ steps.source.outputs.sha }}",
        }
        for content in _rendered(root).values():
            assert "softprops/action-gh-release" not in content


def test_gh_release_pin_is_removed() -> None:
    assert "gh-release" not in load_pins()


def test_local_setup_uses_carry_a_reasoned_ignore(tmp_path: Path) -> None:
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
@requires("zizmor", "actionlint")
def test_zizmor_and_actionlint_pass_on_every_cell(
    tmp_path: Path, archetype: str, extra: str
) -> None:
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


DEPENDABOT_HOOKS = (
    '\n[ci.hooks]\nsetup = ["./.github/actions/b", "./.github/actions/a"]\n'
)


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_dependabot_is_a_managed_row(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    artifacts = {a.path: a for a in CICD.artifacts(KilnConfig.load(root), root)}
    assert artifacts[DEPENDABOT].kind is ArtifactKind.MANAGED
    assert DEPENDABOT in CI_KEYS


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_no_hooks_renders_only_the_root_actions_entry_and_uv(
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


def test_hooks_render_exactly_their_directories(tmp_path: Path) -> None:
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
def test_never_the_root_or_the_setup_action(tmp_path: Path, hooks: str) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), hooks)
    directories = _hook_entry(root)["directories"]
    assert directories
    for directory in directories:  # type: ignore[attr-defined]
        assert directory not in {"/", "/.github/actions/setup"}
        assert not directory.endswith("*")


def test_one_group_per_ecosystem_for_minor_and_patch(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), DEPENDABOT_HOOKS)
    updates = _dependabot(root)["updates"]
    assert len(updates) == 3  # type: ignore[arg-type]
    for entry in updates:  # type: ignore[attr-defined]
        groups = entry["groups"]
        assert len(groups) == 1
        assert next(iter(groups.values()))["update-types"] == ["minor", "patch"]


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_uv_directory_is_the_root(tmp_path: Path, archetype: str, extra: str) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    assert _updates(root)["uv"]["directory"] == "/"


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_ci_comment_no_longer_says_kiln_only(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    ci = _rendered(_cell_root(tmp_path, archetype, extra))[".github/workflows/ci.yml"]
    assert "Dependabot watches kiln's own repo" not in ci
    assert "dependabot.yml" in ci


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
@pytest.mark.parametrize("hooks", ["", DEPENDABOT_HOOKS])
def test_the_file_passes_the_checks(
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


def test_ado_still_renders_nothing(tmp_path: Path) -> None:
    root = _root(tmp_path, provider="ado")
    with pytest.raises(AppException, match="E8"):
        _rendered(root)


def test_every_entry_has_a_cooldown(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), DEPENDABOT_HOOKS)
    for entry in _dependabot(root)["updates"]:  # type: ignore[attr-defined]
        assert entry["cooldown"]["default-days"] >= 7


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_no_dependabot_entry_sets_a_target_branch(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    for entry in _dependabot(root)["updates"]:  # type: ignore[attr-defined]
        assert "target-branch" not in entry
