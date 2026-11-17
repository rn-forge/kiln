"""The output mode is set in one module."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "rn_forge" / "kiln"
OUTPUT = SRC / "commands" / "output.py"

# The needles are built from pieces so that this file does not match itself.
NEEDLES = ("set_" + "mode(", "OutputMode" + ".JSON")


def test_output_mode_is_set_only_in_the_output_module() -> None:
    offenders = sorted(
        str(path.relative_to(ROOT))
        for path in SRC.rglob("*.py")
        if path != OUTPUT
        and any(n in path.read_text(encoding="utf-8") for n in NEEDLES)
    )
    assert offenders == []
