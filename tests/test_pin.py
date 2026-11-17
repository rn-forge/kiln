"""S7.2.5 — `kiln pin`: move a repository's `[kiln] ref`, and nothing else."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import commands
from rn_forge.kiln.modules.core import cycle

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


def test_s7_2_5_1_writes_only_the_ref(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commands.pin("v1.0.0")  # a tag pin carries no `track`
    before = _files(repo)
    commands.pin("v9.9.9")
    after = _files(repo)
    assert {k for k in after if after[k] != before.get(k)} == {str(CONFIG)}
    assert set(after) == set(before)
    old = before[str(CONFIG)].decode()
    new = after[str(CONFIG)].decode()
    assert old.replace('ref = "v1.0.0"', 'ref = "v9.9.9"') == new
    assert "kiln ref v1.0.0 \u2192 v9.9.9" in capsys.readouterr().out


@pytest.mark.parametrize("ref", ["", "   "])
def test_s7_2_5_2_empty_ref(repo: Path, ref: str) -> None:
    before = _files(repo)
    with pytest.raises(AppException):
        commands.pin(ref)
    assert _files(repo) == before
