"""The first of two trivial workspace packages.

`python-lib` exists as a separate archetype because a workspace of published
packages needs a per-package verify and a per-package release tag, not because
its packages are interesting. Two of them is the smallest number that proves the
CI matrix is a matrix.

Each package depends on `rn-forge-commons` and uses it, because every rn-forge
repo is built on the component libraries (kiln ADR-0009) and a dependency a
package never exercises proves nothing about the archetype.
"""

from __future__ import annotations

from rn_forge.commons import ListUtils


def first(values: list[int], *, default: int = 0) -> int:
    """Return the first of ``values``, or ``default`` when there are none."""
    return int(ListUtils.get(values, 0, default=default))
