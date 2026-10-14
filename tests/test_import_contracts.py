"""kiln's own `.importlinter` contracts (S4.7.1)."""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULES = REPO / "src" / "rn_forge" / "kiln" / "modules"
PREFIX = "importlinter:contract:"


def _config() -> configparser.ConfigParser:
    config = configparser.ConfigParser(interpolation=None)
    config.read(REPO / ".importlinter", encoding="utf-8")
    return config


def _lines(section: str, key: str) -> list[str]:
    return [
        line.strip()
        for line in _config()[PREFIX + section][key].splitlines()
        if line.strip()
    ]


def test_s4_7_1_1_contracts_are_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    """`lint-imports` keeps every contract in kiln's own `.importlinter`."""
    from importlinter import cli as importlinter_cli

    monkeypatch.chdir(REPO)
    assert (
        importlinter_cli.lint_imports(
            config_filename=str(REPO / ".importlinter"), no_cache=True
        )
        == importlinter_cli.EXIT_STATUS_SUCCESS
    )


def test_s4_7_1_1_three_contracts() -> None:
    """The file holds exactly the three named contracts."""
    sections = {
        s.removeprefix(PREFIX) for s in _config().sections() if s.startswith(PREFIX)
    }
    assert sections == {
        "no-kit-imports",
        "render-free-checks",
        "concern-modules-are-independent",
    }


def test_s4_7_1_2_render_free_covers_every_checks_package() -> None:
    """Every `modules/<m>/checks` package is a source module of render-free-checks."""
    sources = set(_lines("render-free-checks", "source_modules"))
    packages = sorted(MODULES.glob("*/checks/__init__.py"))
    assert packages
    for init in packages:
        assert f"rn_forge.kiln.modules.{init.parent.parent.name}.checks" in sources


def test_s4_7_1_3_independence_covers_every_concern_module() -> None:
    """The independence contract lists every concern module except `core`."""
    expected = {
        f"rn_forge.kiln.modules.{init.parent.name}"
        for init in MODULES.glob("*/__init__.py")
        if init.parent.name != "core"
    }
    assert set(_lines("concern-modules-are-independent", "modules")) == expected


def test_s4_7_1_4_task_lint_runs_lint_imports() -> None:
    """`task lint` runs `lint-imports`."""
    lines = (REPO / "tasks" / "quality.yml").read_text(encoding="utf-8").splitlines()
    assert "- uv run lint-imports" in [line.strip() for line in lines]
