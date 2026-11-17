"""The pinned gitleaks release in `pins.toml`."""

from __future__ import annotations

import re
from typing import Any, cast

from rn_forge.kiln.modules.core.pins import load_pins


def test_gitleaks_pin_shape() -> None:
    pin = cast("dict[str, Any]", load_pins()["gitleaks"])
    version = pin["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    for platform in ("linux_x64", "darwin_arm64"):
        entry = pin[platform]
        assert entry["url"].endswith(f"gitleaks_{version}_{platform}.tar.gz")
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])


def test_scorecard_pins_have_full_sha() -> None:
    pins = load_pins()
    for key in ("scorecard", "upload-sarif"):
        pin = pins[key]
        assert re.fullmatch(r"[0-9a-f]{40}", pin["sha"]), key
        assert pin["uses"] and pin["version"], key


def test_no_template_names_the_old_pins_path() -> None:
    from pathlib import Path

    modules = (
        Path(__file__).resolve().parents[3] / "src" / "rn_forge" / "kiln" / "modules"
    )
    offenders = [
        str(path.relative_to(modules))
        for path in sorted(modules.glob("*/templates/**/*.j2"))
        if "cicd/pins.toml" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
