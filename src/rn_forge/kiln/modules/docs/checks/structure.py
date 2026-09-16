"""`docs-structure` — the docs tree matches its area model and kiln's policy."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.policy import POLICY
from rn_forge.kiln.modules.docs.structure import check_structure

__all__ = ["NAME", "check"]

NAME = "docs-structure"


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Check `docs/` against `docs/_areas.yml`, for a repo with an MkDocs site."""
    if config.docs_profile != "mkdocs":
        return []
    return check_structure(root, root / "docs", POLICY)
