"""Markdown parses cached by text, so each page is parsed once per run."""

from __future__ import annotations

import functools
import re

from rn_forge.commons.text.markdown import MarkdownHeading, MarkdownUtils

__all__ = [
    "EPIC_RANGE",
    "anchors",
    "epic_range",
    "headings",
    "links",
    "local_links",
    "range_label",
    "title_markup",
]

EPIC_RANGE = 10
"""How many epic numbers one range of the epic list spans."""


@functools.lru_cache(maxsize=2048)
def headings(text: str) -> tuple[MarkdownHeading, ...]:
    """Return the headings of *text*, outside fenced code."""
    return tuple(MarkdownUtils.headings(text))


@functools.lru_cache(maxsize=2048)
def links(text: str) -> tuple[str, ...]:
    """Return the link targets of *text*."""
    return tuple(MarkdownUtils.links(text))


def local_links(text: str) -> tuple[str, ...]:
    """Return the link targets of *text* that are not external."""
    return tuple(link for link in links(text) if not MarkdownUtils.is_external(link))


def anchors(text: str) -> frozenset[str]:
    """Return the heading anchors of *text*."""
    return frozenset(heading.anchor for heading in headings(text))


def title_markup(text: str) -> str | None:
    """The source text of the first level-1 heading, markup kept, or `None`."""
    heading = next((h for h in headings(text) if h.level == 1), None)
    if heading is None:
        return None
    line = text.splitlines()[heading.line].strip()
    if not line.startswith("#"):
        return heading.text
    return re.sub(r"\s+#+$", "", line.lstrip("#").strip())


def epic_range(number: int) -> tuple[int, int]:
    """The inclusive `(lo, hi)` epic numbers of the range holding *number*."""
    lo = (number - 1) // EPIC_RANGE * EPIC_RANGE + 1
    return lo, lo + EPIC_RANGE - 1


def range_label(lo: int, hi: int) -> str:
    """The heading text of a range, such as `E1–E10`."""
    return f"E{lo}\u2013E{hi}"
