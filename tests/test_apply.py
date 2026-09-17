"""S4.5.2 — `kiln apply`: reconciliation.

Built over a copy of the `python-tool` golden repo — already scaffolded and
already passing every check (`tests/test_checks_registry.py`), so these tests
need no `uv init` and run fast. The copy skips `.venv` and the various tool
caches, which `cycle.apply`/`checks.run` never touch.
"""

from __future__ import annotations

import inspect
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import commands
from rn_forge.kiln.modules.core import cycle

GOLDEN = Path(__file__).resolve().parent / "fixtures" / "golden" / "python-tool"
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
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A copy of the `python-tool` golden repo, resynced to the current templates.

    The checked-in golden is hand-kept in step with the templates (README);
    mid-feature-branch it can be briefly behind, so `cycle.apply` once before
    the test brings its generated files (never `pyproject.toml`/`src`, which
    `python`'s module renders nothing of) current — without `uv init`.
    """
    root = tmp_path / "repo"
    shutil.copytree(GOLDEN, root, ignore=_IGNORE)
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
