"""S18.9.3: the instructions and tasks renderers do one job per function."""

from __future__ import annotations

from tests.conftest import oversized


def test_s18_9_3_1_no_renderer_function_is_large() -> None:
    assert oversized("modules/instructions", "modules/tasks") == []
