"""S4.5.3 — `kiln diff` and `kiln version`: inspection.

Built over the same golden-repo fixture as `test_apply.py` (the nearest `done`
story in this feature) — already scaffolded and passing, so no `uv init` is
needed.
"""

from __future__ import annotations

import json
import shutil
from importlib import metadata
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
    root = tmp_path / "repo"
    shutil.copytree(GOLDEN, root, ignore=_IGNORE)
    cycle.apply(root)
    monkeypatch.chdir(root)
    yield root
    console.set_mode(OutputMode.PLAIN)


def _last_json(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    out = capsys.readouterr().out.strip().splitlines()
    return json.loads(out[-1])


def _edit_taskfile(repo: Path) -> None:
    target = repo / "Taskfile.yml"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# edit\n", encoding="utf-8"
    )


def test_s4_5_3_1_clean_repo_diff_prints_nothing_and_exits_0(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commands.diff()
    assert capsys.readouterr().out == ""


def test_s4_5_3_1_edited_artifact_diff_names_the_path_and_raises(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _edit_taskfile(repo)
    with pytest.raises(AppException):
        commands.diff()
    out = capsys.readouterr().out
    assert "Taskfile.yml" in out
    assert "# edit" in out


def test_s4_5_3_1_diff_limits_to_the_named_artifact(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _edit_taskfile(repo)
    editorconfig = repo / ".editorconfig"
    editorconfig.write_text(
        editorconfig.read_text(encoding="utf-8") + "\n# edit\n", encoding="utf-8"
    )

    with pytest.raises(AppException):
        commands.diff("Taskfile.yml")
    out = capsys.readouterr().out
    assert "Taskfile.yml" in out
    assert ".editorconfig" not in out


def test_s4_5_3_1_unknown_artifact_is_refused_by_name(repo: Path) -> None:
    with pytest.raises(AppException, match="nope"):
        commands.diff("nope")


def test_s4_5_3_2_version_json_matches_the_installed_distribution(
    capsys: pytest.CaptureFixture[str],
) -> None:
    commands.version(json=True)
    payload = _last_json(capsys)
    assert payload["version"] == metadata.version("rn-forge-kiln")
