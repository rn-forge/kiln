"""Which files of a docs directory are content pages, and what a nav names."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

__all__ = ["content_pages", "is_content_page", "nav_pages"]


def is_content_page(path: Path) -> bool:
    """Whether *path* is a page that is neither an `index.md` nor `_`-prefixed."""
    return path.name != "index.md" and not path.name.startswith("_")


def content_pages(directory: Path) -> list[Path]:
    """The content pages directly in *directory*, sorted."""
    return sorted(p for p in directory.glob("*.md") if is_content_page(p))


def nav_pages(nav: object) -> list[str]:
    """Every string leaf of a nav tree, in order."""
    if isinstance(nav, str):
        return [nav]
    if isinstance(nav, dict):
        return [
            page for v in cast(dict[str, Any], nav).values() for page in nav_pages(v)
        ]
    if isinstance(nav, list):
        return [page for v in cast(list[Any], nav) for page in nav_pages(v)]
    return []
