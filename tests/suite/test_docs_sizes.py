"""The docs module's files and functions are small."""

from __future__ import annotations

import re

from tests.conftest import SRC, oversized


def test_no_docs_file_or_function_is_large() -> None:
    assert oversized("modules/docs", max_lines=400) == []


def test_nav_imports_no_render_helper_from_work() -> None:
    text = (SRC / "modules/docs/nav.py").read_text(encoding="utf-8")
    block = re.search(
        r"from rn_forge\.kiln\.modules\.docs\.work import \(?([^)]*?)(?:\)|\n\n)",
        text,
        re.S,
    )
    imported = block.group(1) if block else ""
    for name in ("title_markup", "epic_range", "range_label"):
        assert name not in imported
