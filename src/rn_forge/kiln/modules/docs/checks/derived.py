"""`docs-generate` — the docs' derived regions are current.

The check half of `kiln docs-generate`, which rewrites them.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs import generate

__all__ = ["NAME", "check"]

NAME = "docs-generate"


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Fail if regenerating a derived region would change a file."""
    if config.docs_profile != "mkdocs":
        return []
    return generate.stale(root)
