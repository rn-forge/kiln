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


def test_shipped_page_makes_a_release(
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
    assert create[8:] == ["--target", SHA, "--latest"]
    assert NOTES == ["Body line.\n\n## Entry criteria\n\n- one\n"]


@pytest.mark.parametrize("status", ["planned", "in progress"])
def test_planned_page_is_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: str
) -> None:
    _repo(tmp_path, status)
    monkeypatch.chdir(tmp_path)
    calls = _gh(monkeypatch, exists=False)
    assert _umbrella() == 0
    assert [c for c in calls if c[:3] == ["gh", "release", "create"]] == []


def test_existing_release_is_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo(tmp_path, "shipped")
    monkeypatch.chdir(tmp_path)
    calls = _gh(monkeypatch, exists=True)
    assert _umbrella() == 0
    assert calls == [["gh", "release", "view", "release-2"]]


def test_dry_run_creates_no_release(
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
    assert out.rstrip().endswith(f"--target {SHA} --latest")


def _many(root: Path, shipped: range, planned: range = range(0)) -> None:
    for number in shipped:
        _repo(root, "shipped", number)
    for number in planned:
        _repo(root, "planned", number)


def _gh_tags(monkeypatch: pytest.MonkeyPatch, existing: set[str]) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        code = 0
        if command[:3] == ["gh", "release", "view"]:
            code = 0 if command[3] in existing else 1
        return subprocess.CompletedProcess(command, code, stdout="")

    monkeypatch.setattr(github.subprocess, "run", run)
    return calls


def _creates(calls: list[list[str]]) -> list[list[str]]:
    return [c for c in calls if c[:3] == ["gh", "release", "create"]]


def _skipped(err: str) -> list[str]:
    return [
        line.split(":")[1].strip().removeprefix("skipped ")
        for line in err.splitlines()
        if line.startswith("kiln-devops: skipped release-")
    ]


def test_old_untagged_releases_are_not_backfilled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _many(tmp_path, range(1, 8), range(8, 9))
    monkeypatch.chdir(tmp_path)
    calls = _gh_tags(monkeypatch, {"release-6", "release-7"})
    assert _umbrella() == 0
    assert _creates(calls) == []
    assert _skipped(capsys.readouterr().err) == [f"release-{n}" for n in range(1, 6)]


def test_only_the_newest_is_created(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _many(tmp_path, range(1, 9))
    monkeypatch.chdir(tmp_path)
    calls = _gh_tags(monkeypatch, {"release-6", "release-7"})
    assert _umbrella() == 0
    creates = _creates(calls)
    assert len(creates) == 1
    assert creates[0][3] == "release-8"
    assert creates[0][-3:] == ["--target", SHA, "--latest"]
    assert _skipped(capsys.readouterr().err) == [f"release-{n}" for n in range(1, 6)]


def test_latest_is_never_given_to_an_older_release(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _many(tmp_path, range(1, 8), range(8, 9))
    monkeypatch.chdir(tmp_path)
    calls = _gh_tags(monkeypatch, {"release-6"})
    assert _umbrella() == 0
    _repo(tmp_path, "shipped", 9)
    assert _umbrella() == 0
    creates = _creates(calls)
    assert creates
    assert [c[3] for c in creates] == ["release-7", "release-9"]
    assert all("--latest=false" not in c for c in creates)


def test_nothing_to_do_when_newest_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _many(tmp_path, range(1, 8))
    monkeypatch.chdir(tmp_path)
    calls = _gh_tags(monkeypatch, {"release-7"})
    assert _umbrella() == 0
    assert _creates(calls) == []
    assert (
        "No shipped release is missing its GitHub release." in capsys.readouterr().err
    )


def test_dry_run_prints_only_the_newest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _many(tmp_path, range(1, 4))
    monkeypatch.chdir(tmp_path)
    calls = _gh_tags(monkeypatch, set())
    assert _umbrella("--dry-run") == 0
    assert calls == []
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("gh release create release-3 ")
    assert lines[0].endswith("--latest")
    assert _skipped(captured.err) == ["release-1", "release-2"]


EVIDENCE_PAGE = """# Release 2 — Security evidence

|  |  |
| -- | -- |
{run}| **Commit** | abc1234 |

Body.
"""
RUN_ROW = (
    "| **Run** | [77, attempt 1](https://github.com/o/r/actions/runs/77/attempts/1) |\n"
)


def _evidence_page(root: Path, run_row: str = RUN_ROW) -> Path:
    page = root / "docs" / "releases" / "release-2" / "security.md"
    page.write_text(EVIDENCE_PAGE.format(run=run_row), encoding="utf-8")
    return page


def _download(monkeypatch: pytest.MonkeyPatch, ok: bool) -> list[int]:
    runs: list[int] = []

    def download(run: int, name: str, dest: Path) -> bool:
        runs.append(run)
        if ok:
            (dest / "security-evidence.json").write_text("{}", encoding="utf-8")
        return ok

    monkeypatch.setattr(github, "download_artifact", download)
    return runs


def _shipped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[list[str]]:
    _repo(tmp_path, "shipped")
    monkeypatch.chdir(tmp_path)
    return _gh(monkeypatch, exists=False)


def test_evidence_is_attached_to_the_release(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = _shipped(monkeypatch, tmp_path)
    page = _evidence_page(tmp_path)
    runs = _download(monkeypatch, True)
    assert _umbrella("--evidence") == 0
    create = _creates(calls)[0]
    assert create[3] == "release-2"
    assert create[4].endswith("security-evidence.json")
    assert create[5] == str(page)
    assert runs == [77]


def test_release_is_created_without_a_page_and_warns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _shipped(monkeypatch, tmp_path)
    _download(monkeypatch, True)
    assert _umbrella("--evidence") == 0
    assert _creates(calls)[0][4] == "--title"
    assert (
        "release-2: no security evidence attached (no security.md)"
        in capsys.readouterr().err
    )


def test_release_is_created_when_the_artifact_is_gone(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _shipped(monkeypatch, tmp_path)
    _evidence_page(tmp_path)
    _download(monkeypatch, False)
    assert _umbrella("--evidence") == 0
    assert _creates(calls)[0][4] == "--title"
    assert "run 77 has no security-evidence artifact" in capsys.readouterr().err


def test_page_without_a_run_warns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _shipped(monkeypatch, tmp_path)
    _evidence_page(tmp_path, run_row="")
    runs = _download(monkeypatch, True)
    assert _umbrella("--evidence") == 0
    assert _creates(calls)[0][4] == "--title"
    assert runs == []
    assert "security.md names no run" in capsys.readouterr().err


def test_dry_run_names_the_evidence_without_downloading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _shipped(monkeypatch, tmp_path)
    page = _evidence_page(tmp_path)
    runs = _download(monkeypatch, True)
    assert _umbrella("--dry-run", "--evidence") == 0
    out = capsys.readouterr().out
    assert "release-2 security-evidence.json " + str(page) in out
    assert runs == []


def test_no_evidence_flag_attaches_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = _shipped(monkeypatch, tmp_path)
    _evidence_page(tmp_path)
    runs = _download(monkeypatch, True)
    assert _umbrella() == 0
    assert _creates(calls)[0][4] == "--title"
    assert runs == []
