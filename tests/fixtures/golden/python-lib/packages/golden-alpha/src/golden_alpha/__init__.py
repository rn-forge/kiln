"""The first of two trivial workspace packages."""

from __future__ import annotations

from rn_forge.commons import ListUtils


def first(values: list[int], *, default: int = 0) -> int:
    """Return the first of ``values``, or ``default`` when there are none."""
    return int(ListUtils.get(values, 0, default=default))
