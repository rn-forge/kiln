"""`docs-site` — links, anchors, nav targets and orphan pages all resolve."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.site import check_site

__all__ = ["NAME", "check"]

NAME = "docs-site"


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Check the site MkDocs would build, for a repo with an MkDocs site."""
    if config.docs_profile != "mkdocs":
        return []
    return check_site(root)
