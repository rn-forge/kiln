"""S16.3.1 — `docs/runbooks/cutover.md`: the one-time move onto kiln."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.kiln import commands

from rn_forge.commons.generation import StateEntry
from rn_forge.commons.generation.artifacts import block_from_entry

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs/runbooks/cutover.md"
CONFIG = Path(".rn-forge/kiln/config.toml")
STEPS = (
    "Branch",
    "Run kiln init",
    "Read the diff file by file",
    "Record a verdict",
    "Land the absorb stories",
    "Bump [kiln] ref and run kiln apply",
    "Merge",
)


_IGNORE = shutil.ignore_patterns(
    ".venv", ".uv-cache", ".ruff_cache", ".import_linter_cache", ".pytest_cache",
    ".docs-site", ".git", "__pycache__",
)  # fmt: skip


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _commit(root: Path) -> None:
    _git(root, "add", "-A")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "edit")


def _unadopted(fresh: Path, tmp_path: Path) -> Path:
    """A copy of *fresh* with its kiln state and blocks removed, as a committed git repository."""
    root = tmp_path / fresh.name
    shutil.copytree(fresh, root, ignore=_IGNORE)
    state = json.loads((root / ".rn-forge/kiln/state.json").read_text(encoding="utf-8"))
    for entry in state["entries"].values():
        if entry["kind"] == "block":
            block = StateEntry.from_dict(entry)
            path = root / block.path
            path.write_text(
                block_from_entry(block).remove(path.read_text(encoding="utf-8")),
                encoding="utf-8",
            )
    shutil.rmtree(root / ".rn-forge")
    _git(root, "init", "-q")
    _commit(root)
    return root


def _text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def test_s16_3_1_1_runbook_steps() -> None:
    text = _text()

    assert text.startswith("# Cutting a repository over to kiln")
    found = re.findall(r"^(\d+)\. \*\*(.+?)\.?\*\*", text, re.MULTILINE)
    assert len(found) == len(STEPS)  # mdformat numbers every item `1.`
    for (_, heading), expected in zip(found, STEPS, strict=True):
        assert heading.replace("`", "").startswith(expected)


def test_s16_3_1_2_table_format() -> None:
    assert "| File | What is lost | Verdict | Where it went |" in _text()


def test_s16_3_1_3_listed() -> None:
    index = (ROOT / "docs/runbooks/index.md").read_text(encoding="utf-8")

    assert "](cutover.md)" in index


def test_s16_3_1_4_sequence_runs(
    rendered: Callable[[str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        commands, "_run_task", lambda root, name: calls.append((root, name))
    )
    root = _unadopted(rendered("python-app"), tmp_path)
    monkeypatch.chdir(root)
    (root / "Taskfile.yml").write_text(
        "version: '3'\ntasks:\n  test:\n    cmds: [pytest]\n", encoding="utf-8"
    )
    (root / "mkdocs.yml").write_text("site_name: old\n", encoding="utf-8")
    (root / ".github/workflows").mkdir(parents=True, exist_ok=True)
    (root / ".github/workflows/ci.yml").write_text(
        "name: old\non: push\njobs: {}\n", encoding="utf-8"
    )
    _commit(root)

    commands.init(archetype="python-app", docs="mkdocs", yes=True)
    assert [name for _, name in calls] == ["setup", "format", "docs:generate"]
    _commit(root)

    config = root / CONFIG
    text = config.read_text(encoding="utf-8")
    assert re.search(r'^ref = ".*"$', text, re.MULTILINE)
    config.write_text(
        re.sub(r'^ref = ".*"$', 'ref = "v9.9.9"', text, flags=re.MULTILINE),
        encoding="utf-8",
    )

    commands.apply()

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True
    ).stdout
    changed = {line[3:] for line in status.splitlines()}
    # the pinned ref is rendered into these task files, so they move with it
    ref_carriers = {
        "tasks/ci.yml",
        "tasks/docs.yml",
        "tasks/kiln.yml",
        "tasks/python.yml",
    }
    assert changed <= {
        ".rn-forge/kiln/config.toml",
        ".rn-forge/kiln/state.json",
        *ref_carriers,
    }, status
    _commit(root)

    with pytest.raises(AppException, match="use `kiln apply`"):
        commands.init(archetype="python-app", docs="mkdocs", yes=True)


# S16.6.6 — the runbook says what the rehearsal needed.


def _flat() -> str:
    return " ".join(_text().split())


def test_s16_6_6_1_origin() -> None:
    text = _flat()

    assert "Run it from a checkout whose `origin` is the repository" in text
    assert "the repository name comes from the `origin` remote" in text


def test_s16_6_6_2_python_lib_config() -> None:
    text = _flat()

    assert (
        "A `python-lib` passes `--config` with `packages`, `modules`, "
        "`import_contracts` and `[ci] release`"
    ) in text
    assert (
        "https://github.com/rn-forge/pykit/blob/main/docs/specs/epics/"
        "E16-kiln-adoption/F16.3-cutover.md"
    ) in text


def test_s16_6_6_3_old_workflows() -> None:
    text = _flat()

    assert "`init` exits 1 while the old workflows are present" in text
    assert "because its closing `kiln doctor` checks them" in text
    assert "Delete the old workflows now (`git rm .github/workflows/<old>.yml`)" in text
    assert "right after this read and before step 6" in text


def test_s16_6_6_4_steps_unchanged() -> None:
    found = re.findall(r"^(\d+)\. \*\*(.+?)\.?\*\*", _text(), re.MULTILINE)

    assert len(found) == len(STEPS)
    for (_, heading), expected in zip(found, STEPS, strict=True):
        assert heading.replace("`", "").startswith(expected)


def test_s16_6_13_5_runbook_names_migrate() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "node-lib" in text
    assert "nx migrate" in text
    assert "pnpm audit" in text
