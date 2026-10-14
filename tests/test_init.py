"""S4.5.8 — `kiln init`: bring an existing standard repository under kiln.

Built over a copy of the session-rendered `python-app` repo (`rendered` in
`tests/conftest.py`), with `.rn-forge/` and every kiln block removed and a
`.git` entry added: a standard repository kiln has never seen, whose managed
files already equal their renders. No test runs a scaffold; every scaffold
function `commands` imports is replaced by one that records and fails.
"""

from __future__ import annotations

import json
import os
import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.tooling.generation import ArtifactKind, StateEntry
from rn_forge.tooling.generation.artifacts import block_from_entry

from rn_forge.kiln import commands

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(".rn-forge/kiln/state.json")
CONFIG = Path(".rn-forge/kiln/config.toml")
SELECTORS: dict[str, Any] = {"archetype": "python-app", "docs": "mkdocs"}

_IGNORE = shutil.ignore_patterns(
    ".venv",
    ".uv-cache",
    ".ruff_cache",
    ".import_linter_cache",
    ".pytest_cache",
    ".docs-site",
    ".git",
    "__pycache__",
)
_SCAFFOLDS = (
    "scaffold_backend",
    "scaffold_frontend",
    "reconcile_backend",
    "reconcile_frontend",
    "docs_scaffold",
    "instructions_scaffold",
    "python_add_package",
    "docs_add_package",
)


def _entries(root: Path) -> dict[str, dict[str, Any]]:
    return json.loads((root / STATE).read_text(encoding="utf-8"))["entries"]


def _blocks(root: Path) -> list[StateEntry]:
    return [
        StateEntry.from_dict(entry)
        for entry in _entries(root).values()
        if entry["kind"] == "block"
    ]


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        file.relative_to(root).as_posix(): file.read_bytes()
        for file in sorted(root.rglob("*"))
        if file.is_file() and ".git" not in file.parts
    }


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


@pytest.fixture
def scaffold_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every scaffold function `commands` holds fails if called, and is recorded."""
    calls: list[str] = []

    def forbidden(name: str) -> Callable[..., None]:
        def fail(*_: object, **__: object) -> None:
            calls.append(name)
            raise AssertionError(f"init called {name}")

        return fail

    for name in _SCAFFOLDS:
        monkeypatch.setattr(commands, name, forbidden(name))
    return calls


@pytest.fixture
def fresh(rendered: Callable[[str], Path]) -> Path:
    """The `new` repo the standard says init must reproduce."""
    return rendered("python-app")


@pytest.fixture
def repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fresh: Path,
    scaffold_calls: list[str],
) -> Path:
    """A standard repository with no kiln state, no kiln blocks, files already equal."""
    root = tmp_path / fresh.name
    shutil.copytree(fresh, root, ignore=_IGNORE)
    for block in _blocks(root):
        path = root / block.path
        path.write_text(
            block_from_entry(block).remove(path.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
    shutil.rmtree(root / ".rn-forge")
    (root / ".git").mkdir()
    monkeypatch.chdir(root)
    return root


def _tamper_block(root: Path, fresh: Path, path: str) -> None:
    """Put a kiln block with the wrong body into *path*."""
    entry = next(block for block in _blocks(fresh) if block.path == path)
    file = root / path
    file.write_text(
        block_from_entry(entry).render(file.read_text(encoding="utf-8"), "tampered"),
        encoding="utf-8",
    )


def test_s4_5_8_1_equal_files_are_baselined_without_rewriting(
    repo: Path, fresh: Path
) -> None:
    whole = [
        repo / entry["path"]
        for entry in _entries(fresh).values()
        if entry["kind"] == "managed" and (repo / entry["path"]).is_file()
    ]
    assert whole
    for file in whole:
        os.utime(file, ns=(1_000_000_000, 1_000_000_000))

    commands.init(**SELECTORS, yes=True)

    assert (repo / CONFIG).is_file()
    assert (repo / STATE).is_file()
    assert {file: file.stat().st_mtime_ns for file in whole} == {
        file: 1_000_000_000 for file in whole
    }
    assert _entries(repo) == _entries(fresh)


def test_s4_5_8_1_force_over_differences_reproduces_a_fresh_new(
    repo: Path, fresh: Path
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    _tamper_block(repo, fresh, "CLAUDE.md")

    commands.init(**SELECTORS, force=True, yes=True)

    assert _entries(repo) == _entries(fresh)
    for entry in _entries(fresh).values():
        if entry["kind"] == "managed":
            assert (repo / entry["path"]).read_bytes() == (
                fresh / entry["path"]
            ).read_bytes()
    claude = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert "tampered" not in claude
    assert tomllib.loads((repo / CONFIG).read_text(encoding="utf-8")) == tomllib.loads(
        (fresh / CONFIG).read_text(encoding="utf-8")
    )


def test_s4_5_8_2_outside_a_git_worktree_fails_and_leaves_no_umbrella(
    repo: Path,
) -> None:
    (repo / ".git").rmdir()
    with pytest.raises(AppException, match="Git worktree"):
        commands.init(**SELECTORS, yes=True)
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_2_kilns_own_checkout_fails_and_leaves_no_umbrella(repo: Path) -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    name = pyproject["project"]["name"]
    (repo / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "0"\n', encoding="utf-8"
    )
    with pytest.raises(AppException, match="own source checkout"):
        commands.init(**SELECTORS, yes=True)
    assert not (repo / ".rn-forge").exists()


@pytest.mark.parametrize(
    "missing",
    [
        "pyproject.toml",
        "Taskfile.yml",
        "tasks",
        ".github",
        "docs",
        "README.md",
        "CLAUDE.md",
        "AGENTS.md",
        ".gitignore",
    ],
)
def test_s4_5_8_2_a_missing_preflight_path_fails_and_leaves_no_umbrella(
    repo: Path, missing: str
) -> None:
    target = repo / missing
    shutil.rmtree(target) if target.is_dir() else target.unlink()
    with pytest.raises(AppException, match=f"missing {missing}"):
        commands.init(**SELECTORS, yes=True)
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_2_every_failed_condition_is_named_in_one_error(repo: Path) -> None:
    (repo / ".git").rmdir()
    (repo / "Taskfile.yml").unlink()
    shutil.rmtree(repo / "tasks")
    with pytest.raises(AppException) as raised:
        commands.init(**SELECTORS)
    message = str(raised.value)
    assert "Git worktree" in message
    assert "Taskfile.yml" in message
    assert "tasks/" in message or "missing tasks" in message
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_2_archetype_is_required(repo: Path) -> None:
    with pytest.raises(AppException, match="--archetype"):
        commands.init(yes=True)
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_3_unforced_conflicts_are_all_named_and_nothing_changes(
    repo: Path, fresh: Path
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    _tamper_block(repo, fresh, "CLAUDE.md")
    before = _snapshot(repo)

    with pytest.raises(AppException) as raised:
        commands.init(**SELECTORS, yes=True)

    assert "Taskfile.yml" in str(raised.value)
    assert "CLAUDE.md" in str(raised.value)
    assert _snapshot(repo) == before
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_3_a_block_without_a_state_entry_is_a_conflict_even_if_equal(
    repo: Path, fresh: Path
) -> None:
    (repo / "CLAUDE.md").write_bytes((fresh / "CLAUDE.md").read_bytes())
    before = _snapshot(repo)

    with pytest.raises(AppException, match="CLAUDE.md"):
        commands.init(**SELECTORS, yes=True)
    assert _snapshot(repo) == before


def test_s4_5_8_3_an_existing_config_without_state_is_a_conflict(
    repo: Path, fresh: Path
) -> None:
    (repo / CONFIG).parent.mkdir(parents=True)
    (repo / CONFIG).write_text("# mine\n", encoding="utf-8")
    with pytest.raises(AppException, match="config.toml"):
        commands.init(**SELECTORS, yes=True)
    assert (repo / CONFIG).read_text(encoding="utf-8") == "# mine\n"
    assert not (repo / STATE).exists()


def test_s4_5_8_4_force_archives_every_overwritten_target(
    repo: Path, fresh: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    _tamper_block(repo, fresh, "CLAUDE.md")
    claude_before = (repo / "CLAUDE.md").read_bytes()
    gitignore = repo / ".gitignore"
    gitignore.write_text("custom-entry\n", encoding="utf-8")

    commands.init(**SELECTORS, force=True, yes=True)

    assert "--force" in capsys.readouterr().err
    stamps = list((repo / ".rn-forge/kiln/backups").iterdir())
    archive = next(stamp for stamp in stamps if (stamp / "Taskfile.yml").exists())
    assert (archive / "Taskfile.yml").read_text(encoding="utf-8") == "# hand made\n"
    assert (archive / "CLAUDE.md").read_bytes() == claude_before
    assert gitignore.read_text(encoding="utf-8").startswith("custom-entry\n")
    assert "tampered" not in (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert (repo / "Taskfile.yml").read_text(encoding="utf-8") != "# hand made\n"


def test_s4_5_8_5_a_second_unforced_init_fails_naming_the_state(repo: Path) -> None:
    commands.init(**SELECTORS, yes=True)
    before = _snapshot(repo)

    with pytest.raises(AppException, match="state.json"):
        commands.init(**SELECTORS, yes=True)
    assert _snapshot(repo) == before


def test_s4_5_8_5_a_forced_reinit_archives_state_and_applies_the_new_selectors(
    repo: Path,
) -> None:
    commands.init(**SELECTORS, yes=True)
    old_state = (repo / STATE).read_bytes()
    old_config = (repo / CONFIG).read_bytes()

    commands.init(archetype="python-app", docs="none", force=True, yes=True)

    archived = {
        relative: [
            (stamp / relative).read_bytes()
            for stamp in (repo / ".rn-forge/kiln/backups").iterdir()
            if (stamp / relative).exists()
        ]
        for relative in (STATE, CONFIG)
    }
    assert old_state in archived[STATE]
    assert old_config in archived[CONFIG]
    config = tomllib.loads((repo / CONFIG).read_text(encoding="utf-8"))
    assert config["docs"]["profile"] == "none"
    assert _entries(repo) != json.loads(old_state)["entries"]


def test_s4_5_8_6_neither_path_runs_a_scaffold(
    repo: Path, scaffold_calls: list[str]
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    commands.init(**SELECTORS, force=True, yes=True)
    commands.init(**SELECTORS, force=True, yes=True)
    assert scaffold_calls == []


def test_s4_5_8_preview_prints_the_plan_and_writes_nothing(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _snapshot(repo)
    commands.init(**SELECTORS, json=True)
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["root"] == str(repo.resolve())
    assert payload["config"]["repository"]["name"] == repo.name
    assert payload["artifacts"]
    assert _snapshot(repo) == before
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_force_does_not_imply_yes_and_dry_run_beats_yes(repo: Path) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    before = _snapshot(repo)
    commands.init(**SELECTORS, force=True)
    commands.init(**SELECTORS, force=True, yes=True, dry_run=True)
    assert _snapshot(repo) == before


def test_s4_5_8_a_failing_check_keeps_the_writes_and_the_archive(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    monkeypatch.setattr(
        commands.checks,
        "run",
        lambda *_a, **_k: [Finding("x.y", Severity.ERROR, "broken")],
    )
    with pytest.raises(AppException, match="check"):
        commands.init(**SELECTORS, force=True, yes=True)
    assert (repo / STATE).is_file()
    assert (repo / CONFIG).is_file()
    assert any((repo / ".rn-forge/kiln/backups").glob("*/Taskfile.yml"))
