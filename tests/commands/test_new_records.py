"""`kiln new`: formatting after apply and the scaffolded-file record."""

from __future__ import annotations
import json
import pytest
from collections.abc import Callable
from pathlib import Path
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.kiln.modules.node import scaffold as node_scaffold
from rn_forge.kiln.modules.python import scaffold as python_scaffold
from tests.conftest import new_repo
from typing import Any


@pytest.fixture(autouse=True)
def _in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`kiln new` stages beneath the current directory; keep that out of the repo."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


@pytest.mark.parametrize("archetype", ["node-lib", "python-tool"])
def test_new_formats_after_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, archetype: str
) -> None:
    calls: list[tuple[Path, bool]] = []
    frontend = tmp_path / "prepared"
    frontend.mkdir()

    monkeypatch.setattr(python_scaffold, "scaffold_backend", lambda *_: None)
    monkeypatch.setattr(python_scaffold, "reconcile_backend", lambda *_: None)
    monkeypatch.setattr(
        node_scaffold,
        "scaffold_node",
        lambda _raw, config: frontend if config.archetype == "node-lib" else None,
    )
    monkeypatch.setattr(node_scaffold, "reconcile_node", lambda *_: None)
    monkeypatch.setattr(
        node_scaffold,
        "format_node",
        lambda workspace: calls.append(
            (workspace, (workspace / ".prettierrc").is_file())
        ),
    )

    new_repo(tmp_path / "demo", archetype=archetype, docs="none", yes=True)

    if archetype == "node-lib":
        assert len(calls) == 1
        assert calls[0][1] is True
    else:
        assert calls == []


@pytest.mark.parametrize(
    ("archetype", "expected"),
    [
        ("python-lib", {"pyproject.toml"}),
        ("node-lib", {"package.json", "nx.json"}),
    ],
)
def test_new_records_the_scaffolded_files(
    rendered: Callable[[str], Path], archetype: str, expected: set[str]
) -> None:
    root = rendered(archetype)
    state = json.loads((root / ".rn-forge/kiln/state.json").read_text("utf-8"))
    scaffolded = state["metadata"]["scaffolded"]
    assert scaffolded == sorted(scaffolded)
    assert {"README.md"} | expected <= set(scaffolded)
    assert "CLAUDE.md" not in scaffolded
    assert "AGENTS.md" not in scaffolded
    assert not set(scaffolded) & {e["path"] for e in state["entries"].values()}
    forbidden = (".rn-forge/", ".git/", "node_modules/", ".venv/")
    assert not [p for p in scaffolded if p.startswith(forbidden)]


@pytest.mark.parametrize("archetype", ["python-lib", "node-lib"])
def test_neither_instruction_file_is_scaffolded(
    rendered: Callable[[str], Path], archetype: str
) -> None:
    root = rendered(archetype)
    state = json.loads((root / ".rn-forge/kiln/state.json").read_text("utf-8"))
    paths = {e["path"] for e in state["entries"].values()}
    assert "CLAUDE.md" not in state["metadata"]["scaffolded"]
    assert "AGENTS.md" not in state["metadata"]["scaffolded"]
    assert "AGENTS.md" in paths
    assert "CLAUDE.md" not in paths
    assert not (root / "CLAUDE.md").exists()
