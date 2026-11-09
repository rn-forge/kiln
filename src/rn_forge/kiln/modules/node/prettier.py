"""The Prettier configuration `node-lib` and `python-web-app` render."""

from __future__ import annotations

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.commons.generation.templated import TemplateArtifact, render_artifacts
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig

__all__ = ["PRETTIERIGNORE_BLOCK", "render"]

PRETTIERIGNORE_BLOCK = ManagedBlock("rn-forge kiln")
"""kiln's fenced block in the repo's `.prettierignore`."""


def render(config: KilnConfig) -> list[Artifact]:
    """Render `.prettierrc` and the `.prettierignore` block for a node archetype.

    Returns:
        The two artifacts for `node-lib` and `python-web-app`; `[]` otherwise.
    """
    if config.archetype not in {"node-lib", "python-web-app"}:
        return []
    engine = TemplateEngine.cached(package="rn_forge.kiln.modules.node")
    context = {
        "kiln_version": __version__,
        "docs": config.docs_profile == "mkdocs",
        "site_dir": config.docs_site_dir,
    }
    return render_artifacts(
        engine,
        context,
        [
            TemplateArtifact(".prettierrc", template="prettierrc.j2"),
            TemplateArtifact(
                ".prettierignore",
                ArtifactKind.BLOCK,
                template="prettierignore.j2",
                block=PRETTIERIGNORE_BLOCK,
            ),
        ],
    )
