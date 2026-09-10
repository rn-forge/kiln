"""The second of two trivial workspace packages.

It depends on nothing in this workspace, including golden-alpha: the
independence contract in `.importlinter` is what keeps two separately released
packages separately releasable, and a fixture that wired its own packages
together would be testing uv's workspace resolution rather than the standard.

It does depend on `rn-forge-commons`, like every rn-forge distributable
(kiln ADR-0005).
"""

from __future__ import annotations

from rn_forge.commons import DictUtils

DEFAULTS: dict[str, int] = {"factor": 2}


def scale(value: int, **overrides: int) -> int:
    """Return ``value`` multiplied by ``factor``, which defaults to 2."""
    settings = DictUtils.merge(dict(DEFAULTS), overrides)
    return value * settings["factor"]
