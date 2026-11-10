"""S4.5.2 — `kiln apply`: reconciliation.

Built over a copy of the session-rendered `python-tool` repo (`rendered` in
`tests/conftest.py`) — already scaffolded and already passing every check
(`tests/test_checks_registry.py`), so each test needs no `uv init` and runs fast. The copy skips `.venv` and the various tool
caches, which `cycle.apply`/`checks.run` never touch.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
import shutil
from pathlib import Path
from typing import Any

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.generation import Action
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import commands
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.instructions.artifacts import KILN_BLOCK

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


@pytest.fixture
def repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rendered: Callable[[str], Path],
) -> Path:
    """A copy of the rendered `python-tool` repo, applied once more."""
    root = tmp_path / "repo"
    shutil.copytree(rendered("python-tool"), root, ignore=_IGNORE)
    cycle.apply(root)
    monkeypatch.chdir(root)
    yield root
    console.set_mode(OutputMode.PLAIN)


def _last_json(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    out = capsys.readouterr().out.strip().splitlines()
    return json.loads(out[-1])


def test_s4_5_2_apply_has_no_yes_option() -> None:
    assert "yes" not in inspect.signature(commands.apply).parameters


def test_s4_5_2_clean_repo_dry_run_json_lists_unchanged(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every artifact is settled: `unchanged`, or `skip` for a seeded one already on disk."""
    commands.apply(dry_run=True, json=True)
    payload = _last_json(capsys)
    assert len(payload["artifacts"]) > 0
    assert all(row["action"] in ("unchanged", "skip") for row in payload["artifacts"])


def test_s4_5_2_dry_run_writes_nothing(repo: Path) -> None:
    """A full tree snapshot before/after — covers every file, `backups/` included."""
    before = _snapshot(repo)
    commands.apply(dry_run=True)
    assert _snapshot(repo) == before


def test_s4_5_2_config_edit_then_dry_run_lists_update_and_writes_nothing(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _flip_sonar(repo)
    before = _snapshot(repo)

    commands.apply(dry_run=True, json=True)
    payload = _last_json(capsys)
    actions = {row["action"] for row in payload["artifacts"]}
    assert "update" in actions
    assert _snapshot(repo) == before


def test_s4_5_2_apply_writes_the_update_then_next_dry_run_is_clean(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _flip_sonar(repo)

    commands.apply()
    commands.apply(dry_run=True, json=True)
    payload = _last_json(capsys)
    assert all(row["action"] in ("unchanged", "skip") for row in payload["artifacts"])


def test_s4_5_2_unforced_drift_is_refused_and_writes_nothing(repo: Path) -> None:
    target = repo / "Taskfile.yml"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# edit\n", encoding="utf-8"
    )
    before = _snapshot(repo)

    with pytest.raises(AppException, match="Taskfile.yml"):
        commands.apply()
    assert _snapshot(repo) == before


def test_s4_5_2_force_rewrites_only_the_named_path(repo: Path) -> None:
    task_path = repo / "Taskfile.yml"
    task_path.write_text(
        task_path.read_text(encoding="utf-8") + "\n# edit\n", encoding="utf-8"
    )
    editorconfig = repo / ".editorconfig"
    original_editorconfig = editorconfig.read_text(encoding="utf-8")

    commands.apply(force=["Taskfile.yml"])

    assert "# edit" not in task_path.read_text(encoding="utf-8")
    assert editorconfig.read_text(encoding="utf-8") == original_editorconfig


def test_s4_5_2_force_naming_an_unreported_path_is_refused(repo: Path) -> None:
    with pytest.raises(AppException, match=r"\.editorconfig"):
        commands.apply(force=[".editorconfig"])


def _flip_sonar(repo: Path) -> None:
    config_path = repo / ".rn-forge" / "kiln" / "config.toml"
    text = config_path.read_text(encoding="utf-8")
    assert "sonar = true" in text
    config_path.write_text(
        text.replace("sonar = true", "sonar = false"), encoding="utf-8"
    )


def _snapshot(repo: Path) -> dict[str, str]:
    """Every tracked file's text, keyed by relative path — cheap drift detection."""
    skip = {".rn-forge/kiln/backups", ".rn-forge/kiln/rendered"}
    result: dict[str, str] = {}
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(repo).as_posix()
        if any(relative.startswith(prefix) for prefix in skip):
            continue
        try:
            result[relative] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            result[relative] = "<binary>"
    return result


def test_s6_9_1_2_apply_does_not_recreate_a_deleted_starter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    commands.new(Path("tool"), archetype="python-tool", docs="mkdocs", yes=True)
    root = tmp_path / "tool"
    monkeypatch.chdir(root)
    product = next(root.glob("src/*/product.py"))
    relative = product.relative_to(root).as_posix()
    product.unlink()
    capsys.readouterr()

    commands.apply(dry_run=True, json=True)
    rows = _last_json(capsys)["artifacts"]
    assert {row["action"] for row in rows if row["path"] == relative} == {"forget"}
    assert all(row["action"] != "create" for row in rows)

    commands.apply()
    assert not product.exists()
    capsys.readouterr()
    commands.apply(dry_run=True, json=True)
    assert all(row["path"] != relative for row in _last_json(capsys)["artifacts"])


def test_s16_9_6_2_apply_keeps_the_scaffolded_list(repo: Path) -> None:
    state = repo / ".rn-forge/kiln/state.json"
    before = json.loads(state.read_text("utf-8"))["metadata"]["scaffolded"]
    assert before
    cycle.apply(repo)
    after = json.loads(state.read_text("utf-8"))["metadata"]["scaffolded"]
    assert after == before


_OLD_KEY = "CLAUDE.md#rn-forge kiln"
_NEW_KEY = "AGENTS.md#rn-forge kiln"


def _old_layout(root: Path) -> str:
    """Rewrite the copy into the pre-F16.10 layout (block in `CLAUDE.md`); return the block body."""
    agents = root / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    body = KILN_BLOCK.extract(text)
    assert body is not None
    agents.write_text(KILN_BLOCK.remove(text), encoding="utf-8")
    claude = root / "CLAUDE.md"
    claude.write_text(
        KILN_BLOCK.render(claude.read_text(encoding="utf-8"), body), encoding="utf-8"
    )
    state_path = root / ".rn-forge" / "kiln" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    entry = state["entries"].pop(_NEW_KEY)
    entry["path"] = "CLAUDE.md"
    state["entries"][_OLD_KEY] = entry
    state_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return body


def test_s16_10_3_1_apply_moves_the_block(repo: Path) -> None:
    claude_before = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    body = _old_layout(repo)
    kiln_actions = {
        c.key: c.action
        for c in cycle.plan(repo).changes
        if c.key in (_OLD_KEY, _NEW_KEY)
    }
    assert kiln_actions == {_OLD_KEY: Action.REMOVE, _NEW_KEY: Action.INSERT}
    cycle.apply(repo)
    assert KILN_BLOCK.extract((repo / "AGENTS.md").read_text(encoding="utf-8")) == body
    claude = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert KILN_BLOCK.extract(claude) is None
    assert claude == claude_before
    state = json.loads((repo / ".rn-forge/kiln/state.json").read_text(encoding="utf-8"))
    assert _NEW_KEY in state["entries"]
    assert _OLD_KEY not in state["entries"]


def test_s16_10_3_2_a_second_apply_changes_nothing(repo: Path) -> None:
    _old_layout(repo)
    cycle.apply(repo)
    assert all(
        c.action in (Action.UNCHANGED, Action.SKIP) for c in cycle.plan(repo).changes
    )


def test_s16_10_3_3_an_edited_old_block_blocks_until_forced(repo: Path) -> None:
    body = _old_layout(repo)
    claude = repo / "CLAUDE.md"
    text = claude.read_text(encoding="utf-8")
    at = text.index(body) + 3
    claude.write_text(text[:at] + "#" + text[at + 1 :], encoding="utf-8")
    with pytest.raises(AppException):
        cycle.apply(repo)
    cycle.apply(repo, force=["CLAUDE.md"])
    assert KILN_BLOCK.extract(claude.read_text(encoding="utf-8")) is None
    assert KILN_BLOCK.extract((repo / "AGENTS.md").read_text(encoding="utf-8")) == body


def test_s16_10_3_4_a_missing_agents_md_is_created_with_the_block(repo: Path) -> None:
    body = _old_layout(repo)
    (repo / "AGENTS.md").unlink()
    cycle.apply(repo)
    assert KILN_BLOCK.extract((repo / "AGENTS.md").read_text(encoding="utf-8")) == body
