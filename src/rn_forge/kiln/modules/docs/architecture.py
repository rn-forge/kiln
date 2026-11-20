"""The architecture records `docs` renders, and kiln's block in the ADR index."""

from __future__ import annotations

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.commons.generation.templated import TemplateArtifact, render_artifacts
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.architecture import records_for

__all__ = ["ADR_BLOCK", "render"]

ADR_BLOCK = ManagedBlock("rn-forge kiln", comment="<!--")


def render(config: KilnConfig, engine: TemplateEngine) -> list[Artifact]:
    """Render kiln's block in `docs/adr/index.md`, each record and the records' index.

    Returns:
        Nothing when no record applies to *config*.
    """
    records = records_for(config)
    if not records:
        return []
    context = {
        "kiln_version": __version__,
        "records": [(record.id, record.title) for record in records],
    }
    return render_artifacts(
        engine,
        context,
        [
            TemplateArtifact(
                "docs/adr/index.md",
                ArtifactKind.BLOCK,
                template="docs/adr/index.block.md.j2",
                block=ADR_BLOCK,
            ),
            *(TemplateArtifact(f"docs/adr/kiln/{record.id}.md") for record in records),
            TemplateArtifact("docs/adr/kiln/index.md"),
        ],
    )
