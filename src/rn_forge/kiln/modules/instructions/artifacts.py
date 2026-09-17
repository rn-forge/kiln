"""The artifacts `instructions` renders: the kiln block in `CLAUDE.md`, and `standard.md`."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.config import CiConfig
from rn_forge.kiln.modules.docs.config import DocsConfig

__all__ = ["KILN_BLOCK", "context", "render"]

KILN_BLOCK = ManagedBlock("rn-forge kiln", comment="<!--")
"""kiln's fenced block in the repo's `CLAUDE.md`."""

_PACKAGE = "rn_forge.kiln.modules.instructions"


def context(config: KilnConfig) -> dict[str, object]:
    """The template context every `instructions` template renders with."""
    docs = getattr(config.document, "docs", None)
    ci = getattr(config.document, "ci", None)
    ci = ci if isinstance(ci, CiConfig) else CiConfig()
    lifecycle = config.lifecycle
    web = config.archetype in {"python-web-api", "python-web-app"}
    web_app = config.archetype == "python-web-app"
    web_dir = config.web_dir
    return {
        "kiln_version": __version__,
        "name": config.name,
        "display_archetype": (
            "python-tool"
            if config.archetype == "python-app" and lifecycle
            else config.archetype
        ),
        "lifecycle": lifecycle,
        "workspace": config.archetype == "python-lib",
        "packages": [Path(package).name for package in config.packages],
        "docs_profile": config.docs_profile,
        "docs": config.docs_profile == "mkdocs",
        "external_url": docs.external_url if isinstance(docs, DocsConfig) else "",
        "sonar": ci.sonar,
        "release": ci.release,
        "web": web,
        "web_app": web_app,
        "backend": config.backend,
        "frontend": config.frontend,
        "api_dir": config.api_dir,
        "web_dir": web_dir,
        "web_project": Path(web_dir).name if web_dir else None,
    }


def render(config: KilnConfig) -> list[Artifact]:
    """Render the kiln block in `CLAUDE.md` and `.rn-forge/kiln/standard.md`."""
    engine = TemplateEngine(package=_PACKAGE)
    values = context(config)
    return [
        Artifact(
            "CLAUDE.md",
            ArtifactKind.BLOCK,
            engine.render("block.md.j2", values),
            block=KILN_BLOCK,
        ),
        Artifact(
            ".rn-forge/kiln/standard.md",
            ArtifactKind.MANAGED,
            engine.render("standard.md.j2", values),
        ),
    ]
