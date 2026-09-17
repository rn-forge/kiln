"""S4.5.1 — `kiln new`: creation.

The end-to-end tests that run `uv init` through the python scaffold are slow;
`tests/modules/python/test_scaffold.py` — the nearest `done` story's tests —
marks none of its own `uv init` tests either, so none are marked here.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import archetypes, checks, commands
from rn_forge.kiln.modules.registry import builtin


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


def _last_json(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    out = capsys.readouterr().out.strip().splitlines()
    return json.loads(out[-1])


def test_s4_5_1_flags_match_module_union() -> None:
    """`new`'s config-setting flags are exactly backed by a registered module's `Option`.

    `framework`/`frontend` join both the signature and this set once F5.1/F5.2
    register a module that declares them — see commands.py's `_FLAG_NAMES`
    comment.
    """
    union = {option.flag for module in builtin().modules for option in module.options()}
    assert set(commands._FLAG_NAMES) == union


def test_s4_5_1_preview_without_yes_writes_nothing(tmp_path: Path) -> None:
    directory = tmp_path / "preview"
    commands.new(directory, archetype="python-app", docs="none")
    assert not (directory / ".rn-forge").exists()


def test_s4_5_1_preview_json_lists_artifacts_without_writing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = tmp_path / "preview"
    commands.new(directory, archetype="python-app", docs="none", json=True)
    payload = _last_json(capsys)
    assert payload["root"] == str(directory.resolve())
    assert len(payload["artifacts"]) > 0
    assert all(
        row["action"] in ("create", "insert", "skip") for row in payload["artifacts"]
    )
    assert not (directory / ".rn-forge").exists()


def test_s4_5_1_nonempty_directory_is_refused_and_writes_nothing(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "full"
    directory.mkdir()
    (directory / "x").write_text("x", encoding="utf-8")

    with pytest.raises(AppException, match=str(directory)):
        commands.new(directory, archetype="python-app", docs="none", yes=True)
    assert not (directory / ".rn-forge").exists()


def test_s4_5_1_untested_flag_value_is_refused_without_allow_untested() -> None:
    manifest = archetypes.Archetype.parse(
        tomllib.loads(
            """
            name = "python-app"
            modules = ["core"]
            forbidden_tools = []
            required_validate = []

            [dependencies]
            required = []
            allowed = []

            [untested]
            docs = ["external"]
            """
        ),
        source="fixture",
    )

    with pytest.raises(AppException, match="--docs"):
        commands._flag_layer(
            archetype="python-app",
            docs="external",
            manifest=manifest,
            allow_untested=False,
        )

    flags = commands._flag_layer(
        archetype="python-app", docs="external", manifest=manifest, allow_untested=True
    )
    assert flags["docs"]["profile"] == "external"


@pytest.mark.parametrize("value", [None, ""])
def test_s4_5_1_missing_archetype_is_refused(tmp_path: Path, value: str | None) -> None:
    kwargs: dict[str, Any] = {"docs": "none"}
    if value is not None:
        kwargs["archetype"] = value
    with pytest.raises(AppException, match="--archetype"):
        commands.new(tmp_path / "repo", **kwargs)


def test_s4_5_1_yes_creates_and_passes_every_check(tmp_path: Path) -> None:
    """The slow path: `uv init` through the python scaffold, then a full apply."""
    directory = tmp_path / "demo"
    commands.new(directory, archetype="python-tool", docs="none", yes=True)

    assert (directory / ".rn-forge" / "kiln" / "config.toml").is_file()
    assert (directory / "pyproject.toml").is_file()
    assert checks.run(directory) == []


def test_s4_5_1_yes_json_artifacts_actions_only_create_insert_or_skip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = tmp_path / "demo-json"
    commands.new(directory, archetype="python-tool", docs="none", yes=True, json=True)
    payload = _last_json(capsys)
    assert payload["root"] == str(directory.resolve())
    assert len(payload["artifacts"]) > 0
    assert all(
        row["action"] in ("create", "insert", "skip") for row in payload["artifacts"]
    )


def test_s4_5_1_config_layer_merges_beneath_flags_and_records_source(
    tmp_path: Path,
) -> None:
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "config.toml").write_text("[ci]\nsonar = false\n", encoding="utf-8")

    directory = tmp_path / "demo-layered"
    commands.new(
        directory,
        archetype="python-tool",
        docs="none",
        config=str(layer_dir),
        yes=True,
    )

    written = tomllib.loads(
        (directory / ".rn-forge" / "kiln" / "config.toml").read_text(encoding="utf-8")
    )
    assert written["ci"]["sonar"] is False
    assert written["source"]["location"] == str(layer_dir)
