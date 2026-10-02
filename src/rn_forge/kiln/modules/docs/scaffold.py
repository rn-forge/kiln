"""Scaffolding: the repo-owned body of `mkdocs.yml`.

Runs once, from `kiln new`, before the first `apply`. The body ends with the empty
derived-nav fence, which `kiln docs-generate` fills.
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
        ["packages/*/src"]
        if config.archetype == "python-lib"
        else ["src", *(f"{package}/src" for package in config.packages)]
    )
    engine = TemplateEngine(package="rn_forge.kiln.modules.docs")
    target.write_text(
        engine.render(
            "mkdocs.yml.j2",
            {
                "name": config.name,
                "archetype": config.archetype,
                "source_paths": ", ".join(sources),
            },
        ),
        encoding="utf-8",
    )
