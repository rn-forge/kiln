"""The artifacts `docs` renders: the seeded tree and `mkdocs.yml`'s nav block."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.nav import NAV_BLOCK, build_nav

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
    """Render the seeded docs tree and the nav block, for an `mkdocs` repo at *root*."""
    if config.docs_profile != "mkdocs":
        return []
    engine = TemplateEngine(package="rn_forge.kiln.modules.docs")
    context = {"name": config.name}
    seeds = [
        Artifact(path, ArtifactKind.SEEDED, engine.render(f"{path}.j2", context))
        for path in SEEDS
    ]
    return [
        *seeds,
        Artifact("mkdocs.yml", ArtifactKind.BLOCK, _nav(root, seeds), block=NAV_BLOCK),
    ]


def _nav(root: Path, seeds: list[Artifact]) -> str:
    """The nav for the tree as it will be once every absent seed is written."""
    absent = [seed for seed in seeds if not (root / seed.path).exists()]
    if not absent:
        return build_nav(root / "docs")
    # Rendering writes nothing, so the post-apply tree is assembled in a scratch copy.
    with tempfile.TemporaryDirectory() as scratch:
        docs = Path(scratch) / "docs"
        if (root / "docs").is_dir():
            shutil.copytree(root / "docs", docs)
        for seed in absent:
            target = Path(scratch) / seed.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(seed.content, encoding="utf-8")
        return build_nav(docs)
