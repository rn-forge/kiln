"""Markdown parses cached by text, so each page is parsed once per run."""

from __future__ import annotations

import functools

from rn_forge.commons.text.markdown import MarkdownHeading, MarkdownUtils

__all__ = ["anchors", "headings", "links"]


@functools.lru_cache(maxsize=2048)
def headings(text: str) -> tuple[MarkdownHeading, ...]:
    """Return the headings of *text*, outside fenced code."""
    return tuple(MarkdownUtils.headings(text))


@functools.lru_cache(maxsize=2048)
def links(text: str) -> tuple[str, ...]:
    """Return the link targets of *text*."""
    return tuple(MarkdownUtils.links(text))


def anchors(text: str) -> frozenset[str]:
    """Return the heading anchors of *text*."""
    return frozenset(heading.anchor for heading in headings(text))
