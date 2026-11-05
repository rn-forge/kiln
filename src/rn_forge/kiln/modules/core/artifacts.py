"""The artifacts `core` renders."""

from __future__ import annotations

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.commons.generation.templated import TemplateArtifact, render_artifacts
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.config import DocsConfig

__all__ = ["GITIGNORE_BLOCK", "render"]

GITIGNORE_BLOCK = ManagedBlock("rn-forge kiln")
"""kiln's fenced block in the repo's `.gitignore`."""


def render(config: KilnConfig) -> list[Artifact]:
    """Render `.editorconfig`, `.mdformat.toml`, `.taplo.toml`, the workspace file and the `.gitignore` block."""
    engine = TemplateEngine.cached(package="rn_forge.kiln.modules.core")
    docs = getattr(config.document, "docs", None)
    context = {
        "kiln_version": __version__,
        "python": config.archetype != "node-lib",
        "docs": config.docs_profile == "mkdocs",
        "site_dir": docs.site_dir if isinstance(docs, DocsConfig) else ".docs-site",
    }
    return render_artifacts(
        engine,
        context,
        [
            TemplateArtifact(".editorconfig", template="editorconfig.j2"),
            TemplateArtifact(
                ".mdformat.toml", ArtifactKind.SEEDED, template="mdformat.toml.j2"
            ),
            TemplateArtifact(
                ".taplo.toml", ArtifactKind.SEEDED, template="taplo.toml.j2"
            ),
            TemplateArtifact(
                f"{config.name}.code-workspace",
                ArtifactKind.SEEDED,
                template="code-workspace.j2",
            ),
            TemplateArtifact(
                ".gitignore",
                ArtifactKind.BLOCK,
                template="gitignore.j2",
                block=GITIGNORE_BLOCK,
            ),
        ],
    )
