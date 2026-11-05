"""F15.3 — the pinned gitleaks release in `pins.toml`."""

from __future__ import annotations

import re
from typing import Any, cast

from rn_forge.kiln.modules.cicd.artifacts import load_pins


def test_s15_3_1_1_gitleaks_pin_shape() -> None:
    pin = cast("dict[str, Any]", load_pins()["gitleaks"])
    version = pin["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    for platform in ("linux_x64", "darwin_arm64"):
        entry = pin[platform]
        assert entry["url"].endswith(f"gitleaks_{version}_{platform}.tar.gz")
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
