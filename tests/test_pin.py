"""`kiln pin`: move a repository's `[kiln] ref`, and nothing else."""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import commands
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.main import app
from rn_forge.kiln.modules.core import cycle, kiln_ref

from tests.conftest import git, write_config

CONFIG = Path(".rn-forge/kiln/config.toml")


@pytest.fixture
def repo(
    monkeypatch: pytest.MonkeyPatch,
    rendered_copy: Callable[..., Path],
) -> Path:
    root = rendered_copy("python-tool")
    cycle.apply(root)
    monkeypatch.chdir(root)
    yield root
    console.set_mode(OutputMode.PLAIN)


def _files(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_writes_only_the_ref(
    repo: Path, capsys: pytest.CaptureFixture[str], kiln_remote_sha: str
) -> None:
    commands.pin("v0.0.1")  # a tag pin carries no `track`
    before = _files(repo)
    commands.pin(kiln_remote_sha)
    after = _files(repo)
    assert {k for k in after if after[k] != before.get(k)} == {str(CONFIG)}
    assert set(after) == set(before)
    old = before[str(CONFIG)].decode()
    new = after[str(CONFIG)].decode()
    assert old.replace('ref = "v0.0.1"', f'ref = "{kiln_remote_sha}"') == new
    assert f"kiln ref v0.0.1 \u2192 {kiln_remote_sha}" in capsys.readouterr().out


def test_the_cli_takes_the_ref_as_an_option(repo: Path, kiln_remote_sha: str) -> None:
    assert app(["pin", "--ref", kiln_remote_sha]) == 0
    assert (
        tomllib.loads((repo / CONFIG).read_text(encoding="utf-8"))["kiln"]["ref"]
        == kiln_remote_sha
    )
    try:
        code = app(["pin", kiln_remote_sha])
    except SystemExit as exc:
        code = exc.code
    assert code != 0


@pytest.mark.parametrize("ref", ["", "   "])
def test_a_blank_ref_is_refused_and_writes_nothing(repo: Path, ref: str) -> None:
    commands.pin("v0.0.1")
    before = _files(repo)
    with pytest.raises(AppException):
        commands.pin(ref)
    assert _files(repo) == before


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    yield tmp_path
    console.set_mode(OutputMode.PLAIN)


def _kiln(root: Path) -> dict:
    return tomllib.loads((root / CONFIG).read_text(encoding="utf-8")).get("kiln", {})


def test_a_branch_pins_its_newest_commit(root: Path, kiln_remote_sha: str) -> None:
    commands.pin("feature/v1")
    assert _kiln(root) == {"ref": kiln_remote_sha, "track": "feature/v1"}


def test_a_tag_or_sha_drops_track(root: Path, kiln_remote_sha: str) -> None:
    commands.pin("feature/v1")
    commands.pin("v0.0.1")
    assert _kiln(root) == {"ref": "v0.0.1"}
    commands.pin("feature/v1")
    commands.pin("a" * 40)
    assert _kiln(root) == {"ref": "a" * 40}


def test_no_argument_follows_track(
    root: Path,
    kiln_remote: tuple[str, str],
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A private copy, so the shared remote's `feature/v1` does not move.
    base = tmp_path_factory.mktemp("moving-remote")
    bare = base / "kiln.git"
    git(base, "clone", "-q", "--bare", kiln_remote[0], str(bare))
    work = base / "work"
    git(base, "clone", "-q", str(bare), str(work))
    monkeypatch.setattr(kiln_ref, "REMOTE", bare.as_uri())
    commands.pin("feature/v1")
    assert _kiln(root)["ref"] == kiln_remote[1]
    git(work, "commit", "-q", "--allow-empty", "-m", "next")
    git(work, "push", "-q", "origin", "feature/v1")
    new = git(work, "rev-parse", "HEAD")
    commands.pin()
    assert _kiln(root) == {"ref": new, "track": "feature/v1"}


@pytest.mark.parametrize("ref", ["", "no-such-branch", "v9.9.9"])
def test_errors_write_nothing(root: Path, ref: str) -> None:
    before = (root / CONFIG).read_bytes()
    with pytest.raises(AppException):
        commands.pin(ref)
    assert (root / CONFIG).read_bytes() == before


def test_a_branch_ref_repository_migrates(root: Path, kiln_remote_sha: str) -> None:
    path = root / CONFIG
    path.write_text(path.read_text() + '\n[kiln]\nref = "feature/v1"\n')
    with pytest.raises(AppException):
        KilnConfig.load(root)
    commands.pin("feature/v1")
    assert _kiln(root) == {"ref": kiln_remote_sha, "track": "feature/v1"}
    KilnConfig.load(root)


def test_show_prints_the_ref(
    root: Path, capsys: pytest.CaptureFixture[str], kiln_remote_sha: str
) -> None:
    commands.pin("feature/v1")
    before = (root / CONFIG).read_bytes()
    capsys.readouterr()
    commands.pin(show=True)
    assert capsys.readouterr().out.strip() == kiln_remote_sha
    assert (root / CONFIG).read_bytes() == before
