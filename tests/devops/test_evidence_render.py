"""Tests for `kiln-devops evidence render`."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from rn_forge.kiln.devops import cli, evidence, github

FIXTURES = Path(__file__).parent / "fixtures" / "evidence"
TODAY = date(2026, 11, 24)
REPO = "repos/{owner}/{repo}"
PUSH = "Push protection"


def _install(
    monkeypatch: pytest.MonkeyPatch,
    answer: tuple[int, Any] = (200, {}),
    artifact: bool = True,
) -> list[int]:
    downloads: list[int] = []

    def download(run: int, name: str, dest: Path) -> bool:
        downloads.append(run)
        assert name == "security-evidence"
        if artifact:
            shutil.copy(FIXTURES / "record.json", dest / "security-evidence.json")
        return artifact

    def api(path: str) -> tuple[int, Any]:
        assert path == REPO
        return answer

    monkeypatch.setattr(github, "download_artifact", download)
    monkeypatch.setattr(github, "api", api)
    return downloads


def _releases(tmp_path: Path, number: int = 4) -> Path:
    releases = tmp_path / "releases"
    (releases / f"release-{number}").mkdir(parents=True)
    (releases / f"release-{number}" / "index.md").write_text("# R\n", encoding="utf-8")
    return releases


def _render(releases: Path) -> Path:
    return evidence.render_page(123, 4, releases, TODAY)


def _row(page: Path) -> str:
    return next(
        line
        for line in page.read_text(encoding="utf-8").splitlines()
        if line.startswith(f"| {PUSH} ")
    )


def _security(status: str) -> tuple[int, Any]:
    body = {
        "security_and_analysis": {"secret_scanning_push_protection": {"status": status}}
    }
    return 200, body


def test_render_writes_the_page(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install(monkeypatch)
    page = _render(_releases(tmp_path))
    assert page == tmp_path / "releases" / "release-4" / "security.md"
    expected = (FIXTURES / "security.md").read_text(encoding="utf-8")
    assert page.read_text(encoding="utf-8") == expected


def test_render_is_stable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install(monkeypatch)
    releases = _releases(tmp_path)
    first = _render(releases).read_bytes()
    assert _render(releases).read_bytes() == first


@pytest.mark.parametrize(
    ("status", "result"), [("enabled", "passed"), ("disabled", "failed")]
)
def test_render_fills_push_protection_when_readable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: str, result: str
) -> None:
    _install(monkeypatch, _security(status))
    row = _row(_render(_releases(tmp_path)))
    assert row == (
        f"| {PUSH} | blocks the push | {result} | "
        "GET repos/rn-forge/kiln security_and_analysis, 2026-11-24 |"
    )


def test_render_keeps_not_checked_without_admin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install(monkeypatch, (403, None))
    assert "| not checked |" in _row(_render(_releases(tmp_path)))


def test_render_fails_without_an_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install(monkeypatch, artifact=False)
    releases = _releases(tmp_path)
    with pytest.raises(ValueError, match="run 123"):
        _render(releases)
    assert not (releases / "release-4" / "security.md").exists()


def test_render_fails_without_a_release_page(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    downloads = _install(monkeypatch)
    with pytest.raises(ValueError, match="no release page"):
        _render(tmp_path / "releases")
    assert downloads == []


def test_cli_render_exits_2_and_names_the_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install(monkeypatch, artifact=False)
    monkeypatch.chdir(tmp_path)
    _releases(tmp_path)
    code = cli.main(
        [
            "evidence",
            "render",
            "--run",
            "123",
            "--release",
            "4",
            "--releases",
            "releases",
        ]
    )
    assert code == 2
    assert "run 123" in capsys.readouterr().err
