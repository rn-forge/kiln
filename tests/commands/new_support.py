"""Helpers shared by the `kiln new` tests."""

from __future__ import annotations
import json
import pytest
from typing import Any


def _last_json(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    out = capsys.readouterr().out.strip().splitlines()
    return json.loads(out[-1])
