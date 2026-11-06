"""The test session must not inherit CI's UV_LOCKED."""

from __future__ import annotations

import os
import subprocess
import sys


def test_s16_1_5_1_uv_locked_is_not_inherited() -> None:
    assert "UV_LOCKED" not in os.environ
    out = subprocess.run(
        [sys.executable, "-c", "import os; print('UV_LOCKED' in os.environ)"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == "False"
