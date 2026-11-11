"""Files kiln renders whole that another tool rewrites a region of.

The generation engine hashes whole files. For a file with a derived region
(`mkdocs.yml`'s nav, which `kiln docs-generate` rewrites), kiln records and
compares the hash of the file with that region's body emptied. This module is
render-free, so `kiln doctor` can use it; :mod:`~rn_forge.kiln.modules.core.settle`
adapts the engine's plan.
"""

from __future__ import annotations

from collections.abc import Mapping

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.fs.hashing import ContentHash

__all__ = ["DERIVED", "NAV_BLOCK", "managed_digest"]


class _NavBlock(ManagedBlock):
    """The nav's block: the closing marker sits at the margin, where the YAML
    formatter puts a comment that ends the file."""

    def _marker(self, keyword: str) -> str:
        if keyword == "END":
            return f"# END {self.name}"
        return super()._marker(keyword)


NAV_BLOCK = _NavBlock("derived nav", indent="  ")
"""The fenced block inside `mkdocs.yml`'s ``nav:`` that `kiln docs-generate` owns."""

DERIVED: Mapping[str, tuple[ManagedBlock, ...]] = {"mkdocs.yml": (NAV_BLOCK,)}
"""Each managed file with derived regions, by path."""


def managed_digest(path: str, text: str) -> str:
    """The hash of *text* with *path*'s derived regions emptied.

    Raises:
        AppException: A derived region's markers are malformed.
    """
    for block in DERIVED.get(path, ()):
        if block.extract(text) is not None:
            text = block.render(text, "")
    return ContentHash.of(text)
