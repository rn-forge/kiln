"""`docs-nav` — `mkdocs.yml`'s generated nav block is current.

The check half of `kiln docs-nav`, which rewrites the block.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.nav import update_nav

__all__ = ["NAME", "check"]

NAME = "docs-nav"


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Fail if regenerating the nav would change `mkdocs.yml`."""
    if config.docs_profile != "mkdocs":
        return []
    _, stale = update_nav(root / "mkdocs.yml", root / "docs")
    if not stale:
        return []
    return [
        Finding(
            "docs.nav-stale",
            Severity.ERROR,
            "the generated nav is stale — run `task docs:nav`",
            path="mkdocs.yml",
        )
    ]
