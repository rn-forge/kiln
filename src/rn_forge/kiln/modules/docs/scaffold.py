"""Scaffolding: the repo-owned body of `mkdocs.yml`.

Runs once, from `kiln new`, before the first `apply`. The body carries no nav
markers and ends in `nav:`, so the apply that follows inserts the generated nav
block beneath it.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig

__all__ = ["scaffold"]


def scaffold(root: Path, config: KilnConfig) -> None:
    """Write `mkdocs.yml`'s body into *root*, for an `mkdocs` repo that has none."""
    target = root / "mkdocs.yml"
    if config.docs_profile != "mkdocs" or target.exists():
        return
    sources = (
        [f"{package}/src" for package in config.packages]
        if config.archetype == "python-lib"
        else ["src"]
    )
    engine = TemplateEngine(package="rn_forge.kiln.modules.docs")
    target.write_text(
        engine.render(
            "mkdocs.yml.j2", {"name": config.name, "source_paths": ", ".join(sources)}
        ),
        encoding="utf-8",
    )
