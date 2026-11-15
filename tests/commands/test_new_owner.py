"""`kiln new`: `repository.owner` is configured."""

from __future__ import annotations
import pytest
import tomllib
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.kiln import commands
from typing import Any


@pytest.fixture(autouse=True)
def _in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`kiln new` stages beneath the current directory; keep that out of the repo."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


def _owner_written(directory: Path) -> str:
    text = (directory / ".rn-forge/kiln/config.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)["repository"]["owner"]


def test_s16_6_8_1_new_without_owner_fails(tmp_path: Path) -> None:
    directory = tmp_path / "demo"

    with pytest.raises(AppException) as raised:
        commands.new(directory, archetype="python-tool", docs="none", yes=True)

    assert raised.value.message.startswith("new.owner-required: ")
    assert "--owner" in raised.value.message
    assert not directory.exists()


def test_s16_6_8_1_new_without_owner_exits_non_zero(tmp_path: Path) -> None:
    from rn_forge.kiln import main

    code = main.app(["new", str(tmp_path / "demo"), "--archetype", "python-tool"])

    assert code != 0


@pytest.mark.parametrize(
    ("layer_owner", "flag_owner", "written"),
    [
        pytest.param(None, "acme", "acme", id="flag"),
        pytest.param("from-config", None, "from-config", id="config"),
        pytest.param("from-config", "flag", "flag", id="flag-beats-config"),
    ],
)
def test_s16_6_8_2_the_strongest_layer_sets_the_owner(
    tmp_path: Path, layer_owner: str | None, flag_owner: str | None, written: str
) -> None:
    kwargs: dict[str, Any] = {}
    if layer_owner is not None:
        layer = tmp_path / "layer"
        layer.mkdir()
        (layer / "config.toml").write_text(
            f'[repository]\nowner = "{layer_owner}"\n', encoding="utf-8"
        )
        kwargs["config"] = str(layer)
    if flag_owner is not None:
        kwargs["owner"] = flag_owner
    directory = tmp_path / "demo"

    commands.new(directory, archetype="python-tool", docs="none", yes=True, **kwargs)

    assert _owner_written(directory) == written
