"""Tests for `kiln-devops umbrella`."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from rn_forge.kiln.devops import cli, github

SHA = "abc1234"
NOTES: list[str] = []
PAGE = """# Release 2 — Name

|  |  |
| -- | -- |
| **Status** | {status} |

Body line.

## Entry criteria

- one
"""


def _repo(root: Path, status: str, number: int = 2) -> Path:
    page = root / "docs" / "releases" / f"release-{number}" / "index.md"
    page.parent.mkdir(parents=True)
    page.write_text(PAGE.format(status=status), encoding="utf-8")
    return page


def _gh(monkeypatch: pytest.MonkeyPatch, exists: bool) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[:3] == ["gh", "release", "create"]:
            path = Path(command[command.index("--notes-file") + 1])
            NOTES.append(path.read_text(encoding="utf-8"))
        code = 0 if exists or command[:3] != ["gh", "release", "view"] else 1
        return subprocess.CompletedProcess(command, code, stdout="")

    monkeypatch.setattr(github.subprocess, "run", run)
    return calls


def _umbrella(*extra: str) -> int:
    return cli.main(["umbrella", "--sha", SHA, *extra])


def test_s15_5_1_1_shipped_page_makes_a_release(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    NOTES.clear()
    _repo(tmp_path, "shipped")
    monkeypatch.chdir(tmp_path)
    calls = _gh(monkeypatch, exists=False)
    assert _umbrella() == 0
    create = calls[-1]
    assert calls[0] == ["gh", "release", "view", "release-2"]
    assert create[:7] == [
        "gh", "release", "create", "release-2", "--title", "Release 2 — Name",
        "--notes-file",
    ]  # fmt: skip
    assert create[8:] == ["--target", SHA]
    assert NOTES == ["Body line.\n\n## Entry criteria\n\n- one\n"]


@pytest.mark.parametrize("status", ["planned", "in progress"])
def test_s15_5_1_2_planned_page_is_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: str
) -> None:
    _repo(tmp_path, status)
    monkeypatch.chdir(tmp_path)
    calls = _gh(monkeypatch, exists=False)
    assert _umbrella() == 0
    assert [c for c in calls if c[:3] == ["gh", "release", "create"]] == []


def test_s15_5_1_3_existing_release_is_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo(tmp_path, "shipped")
    monkeypatch.chdir(tmp_path)
    calls = _gh(monkeypatch, exists=True)
    assert _umbrella() == 0
    assert calls == [["gh", "release", "view", "release-2"]]


def test_s15_5_1_4_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _repo(tmp_path, "shipped")
    monkeypatch.chdir(tmp_path)
    calls = _gh(monkeypatch, exists=False)
    assert _umbrella("--dry-run") == 0
    assert calls == []
    out = capsys.readouterr().out
    assert out.startswith("gh release create release-2 --title 'Release 2 — Name'")
    assert out.rstrip().endswith(f"--target {SHA}")
