"""`parsed` caches the Markdown parse so the docs checks read each page once."""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.commons.text.markdown import MarkdownUtils
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs import parsed
from rn_forge.kiln.modules.docs.checks import derived, structure
from rn_forge.kiln.modules.docs.site import check_site

ROOT = Path(__file__).resolve().parents[3]

_TEXT = (
    "Setext\n======\n\n"
    "## Same\n\n## Same\n\n"
    "```\n# not a heading\n```\n\n"
    "[inline](a.md) ![img](b.png) [ref][r]\n\n[r]: c.md\n"
)


def _recording(name: str, seen: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    original = getattr(MarkdownUtils, name)

    def wrapper(text: str):
        seen.append(text)
        return original(text)

    monkeypatch.setattr(MarkdownUtils, name, staticmethod(wrapper))


def test_s17_3_3_1_same_text_is_parsed_once(monkeypatch: pytest.MonkeyPatch) -> None:
    parsed.headings.cache_clear()
    parsed.links.cache_clear()
    seen: list[str] = []
    _recording("headings", seen, monkeypatch)
    parsed.headings("# A\n")
    parsed.headings("# A\n")
    parsed.anchors("# A\n")
    assert len(seen) == 1
    seen_links: list[str] = []
    _recording("links", seen_links, monkeypatch)
    parsed.links("[x](a.md)\n")
    parsed.links("[x](a.md)\n")
    assert len(seen_links) == 1


def test_s17_3_3_2_results_equal_the_library() -> None:
    parsed.headings.cache_clear()
    parsed.links.cache_clear()
    assert parsed.headings(_TEXT) == tuple(MarkdownUtils.headings(_TEXT))
    assert parsed.links(_TEXT) == tuple(MarkdownUtils.links(_TEXT))
    assert parsed.anchors(_TEXT) == MarkdownUtils.anchors(_TEXT)


def test_s17_3_3_3_no_docs_module_calls_the_library_directly() -> None:
    docs = ROOT / "src" / "rn_forge" / "kiln" / "modules" / "docs"
    banned = (
        "MarkdownUtils.headings(",
        "MarkdownUtils.links(",
        "MarkdownUtils.anchors(",
    )
    offenders = [
        str(path.relative_to(ROOT))
        for path in docs.rglob("*.py")
        if path.name != "parsed.py"
        and any(call in path.read_text(encoding="utf-8") for call in banned)
    ]
    assert offenders == []


def test_s17_3_3_4_the_docs_checks_parse_each_page_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parsed.headings.cache_clear()
    parsed.links.cache_clear()
    headings: list[str] = []
    links: list[str] = []
    _recording("headings", headings, monkeypatch)
    _recording("links", links, monkeypatch)
    config = KilnConfig.load(ROOT)
    assert structure.check(config, ROOT) == []
    assert check_site(ROOT) == []
    assert derived.check(config, ROOT) == []
    assert len(headings) == len(set(headings))
    assert len(links) == len(set(links))
