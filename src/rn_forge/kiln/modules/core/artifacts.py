"""The artifacts `core` renders."""

from __future__ import annotations

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig

__all__ = ["GITIGNORE_BLOCK", "render"]

GITIGNORE_BLOCK = ManagedBlock("rn-forge kiln")
"""kiln's fenced block in the repo's `.gitignore`."""


def render(config: KilnConfig) -> list[Artifact]:
    """Render `.editorconfig` and the `.gitignore` block for *config*."""
    del config  # neither artifact varies by repo
    engine = TemplateEngine(package="rn_forge.kiln.modules.core")
    context = {"kiln_version": __version__}
    return [
        Artifact(
            ".editorconfig",
            ArtifactKind.MANAGED,
            engine.render("editorconfig.j2", context),
        ),
        Artifact(
            ".mdformat.toml",
            ArtifactKind.SEEDED,
            engine.render("mdformat.toml.j2", context),
        ),
        Artifact(
            ".gitignore",
            ArtifactKind.BLOCK,
            engine.render("gitignore.j2", context),
            block=GITIGNORE_BLOCK,
        ),
    ]
