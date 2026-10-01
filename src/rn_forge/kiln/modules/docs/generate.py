"""Derived regions: the parts of a docs repo that kiln rewrites from its inputs."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln.modules.docs.nav import update_nav

__all__ = ["generate", "stale"]


def generate(root: Path) -> list[Path]:
    """Rewrite every stale derived region under *root*; return the files written.

    Does nothing unless `root / "mkdocs.yml"` exists.
    """
    mkdocs = root / "mkdocs.yml"
    if not mkdocs.exists():
        return []
    updated, changed = update_nav(mkdocs, root / "docs")
    if not changed:
        return []
    mkdocs.write_text(updated, encoding="utf-8")
    return [mkdocs]


def stale(root: Path) -> list[Finding]:
    """A finding for each derived region under *root* that regenerating would change."""
    mkdocs = root / "mkdocs.yml"
    if not mkdocs.exists():
        return []
    _, changed = update_nav(mkdocs, root / "docs")
    if not changed:
        return []
    return [
        Finding(
            "docs.nav-stale",
            Severity.ERROR,
            "the derived nav is stale — run `task docs:generate`",
            path="mkdocs.yml",
        )
    ]
