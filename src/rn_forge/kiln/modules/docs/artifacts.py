"""The artifacts `docs` renders: the managed `_structure.md` rules and the seeded rest of the docs tree."""

from __future__ import annotations

from pathlib import Path

from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln import __version__
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
    "docs/guides/development.md",
    "docs/runbooks/_structure.md",
    "docs/runbooks/index.md",
    "docs/runbooks/adding-a-package.md",
    "docs/runbooks/recovering-from-drift.md",
    "docs/releases/_structure.md",
    "docs/releases/index.md",
    "docs/specs/_structure.md",
    "docs/specs/index.md",
    "docs/specs/ideas/index.md",
    "docs/specs/epics/index.md",
    "docs/reference/_structure.md",
    "docs/reference/index.md",
    "docs/reference/python-api.md",
    "docs/adr/_structure.md",
    "docs/adr/index.md",
)
"""Every docs path, each rendered from `templates/<path>.j2`; `_structure.md` is managed."""

_PACKAGE_SITE_SKIPS = ("docs/reference/",)
"""Seeds a `python-lib` repository does not carry: each package's reference
lives in its own site."""


_PYTHON_LIB_ONLY = ("docs/runbooks/adding-a-package.md",)
"""Seeds only a `python-lib` repository carries."""


_APP_TOOL_ONLY = ("docs/reference/python-api.md",)
"""Seeds only a `python-app` or `python-tool` repository carries."""


def render(config: KilnConfig, root: Path) -> list[Artifact]:
    """Render the seeded docs tree, for an `mkdocs` repo at *root*."""
    if config.docs_profile != "mkdocs":
        return []
    engine = TemplateEngine(package="rn_forge.kiln.modules.docs")
    context = {
        "name": config.name,
        "archetype": config.archetype,
        "module": config.module,
        "kiln_version": __version__,
    }
    skipped = (
        _PACKAGE_SITE_SKIPS if config.archetype == "python-lib" else _PYTHON_LIB_ONLY
    )
    if config.archetype not in ("python-app", "python-tool"):
        skipped += _APP_TOOL_ONLY
    return [
        Artifact(path, _kind(path), engine.render(f"{path}.j2", context))
        for path in SEEDS
        if not path.startswith(skipped)
    ]


def _kind(path: str) -> ArtifactKind:
    managed = path.endswith("/_structure.md")
    return ArtifactKind.MANAGED if managed else ArtifactKind.SEEDED
