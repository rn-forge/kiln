"""The second of two trivial workspace packages.

It depends on nothing in this workspace, including golden-alpha: the
independence contract in `.importlinter` keeps the two packages separately
releasable.
"""

from __future__ import annotations

from rn_forge.commons import DictUtils

DEFAULTS: dict[str, int] = {"factor": 2}


def scale(value: int, **overrides: int) -> int:
    """Return ``value`` multiplied by ``factor``, which defaults to 2."""
    settings = DictUtils.merge(dict(DEFAULTS), overrides)
    return value * settings["factor"]
