"""S17.3.7 — kiln's own CI caches the pnpm store the Nx scaffolds install from."""

from __future__ import annotations

import tomllib
from pathlib import Path

from rn_forge.commons.fs.documents import YamlUtils

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / ".github/actions/setup-node/action.yml"
PINS = ROOT / "src/rn_forge/kiln/modules/cicd/pins.toml"


def test_s17_3_7_1_setup_node_caches_the_pnpm_store() -> None:
    steps = YamlUtils.load(ACTION.read_text(encoding="utf-8"))["runs"]["steps"]
    names = [step["name"] for step in steps]
    assert names == [
        "Install pnpm",
        "Install Node",
        "Locate the pnpm store",
        "Cache the pnpm store",
    ]
    locate, cache = steps[2], steps[3]
    assert locate["id"] == "pnpm-store"
    assert "pnpm store path" in locate["run"]
    pin = tomllib.loads(PINS.read_text(encoding="utf-8"))["cache"]
    assert cache["uses"] == f"actions/cache@{pin['sha']}"
    assert cache["with"]["path"] == "${{ steps.pnpm-store.outputs.path }}"
    key = "pnpm-store-${{ runner.os }}-"
    assert cache["with"]["key"] == (
        key + "${{ hashFiles('src/rn_forge/kiln/modules/node/*.py') }}"
    )
    assert cache["with"]["restore-keys"] == key
