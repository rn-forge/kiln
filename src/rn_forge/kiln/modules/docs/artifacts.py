"""The artifacts `docs` renders: the seeded docs tree."""

from __future__ import annotations

from pathlib import Path

from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig

__all__ = ["SEEDS", "render"]

SEEDS = (
    "docs/_areas.yml",
    "docs/_structure.md",
    "docs/index.md",
    "docs/architecture/_structure.md",
    "docs/architecture/index.md",
    "docs/guides/_structure.md",
    "docs/guides/index.md",
    "docs/runbooks/_structure.md",
    "docs/runbooks/index.md",
    "docs/releases/_structure.md",
    "docs/releases/index.md",
    "docs/specs/_structure.md",
    "docs/specs/index.md",
    "docs/adr/_structure.md",
    "docs/adr/index.md",
)
"""Every seeded docs path, each rendered from `templates/<path>.j2`."""


def render(config: KilnConfig, root: Path) -> list[Artifact]:
    """Render the seeded docs tree, for an `mkdocs` repo at *root*."""
    if config.docs_profile != "mkdocs":
        return []
    engine = TemplateEngine(package="rn_forge.kiln.modules.docs")
    context = {"name": config.name}
    return [
        Artifact(path, ArtifactKind.SEEDED, engine.render(f"{path}.j2", context))
        for path in SEEDS
    ]
