"""`running_install`: the install the running kiln was started from."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from rn_forge.kiln.product import Installed, running_install

from tests.conftest import INSTALLED_COMMIT


def test_running_install_reads_the_active_state(
    fake_install: Callable[..., Path],
) -> None:
    fake_install()
    assert running_install() == Installed("feature/v1", INSTALLED_COMMIT)


def test_running_install_is_none_outside_the_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RNF_HOME", str(tmp_path / "home"))
    assert running_install() is None


def test_running_install_is_none_for_an_inactive_version(
    fake_install: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_install()
    other = tmp_path / "home" / "kiln" / "versions" / "other" / "tool"
    other.mkdir(parents=True)
    monkeypatch.setattr("sys.prefix", str(other))
    assert running_install() is None
