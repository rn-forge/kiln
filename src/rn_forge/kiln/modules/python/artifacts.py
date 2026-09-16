"""The artifacts `python` renders: `.importlinter`."""

from __future__ import annotations

from pathlib import Path

from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig

__all__ = ["render", "root_package"]


def root_package(name: str) -> str:
    """The importable package name a repo-relative name renders to."""
    return name.replace("-", "_")


def render(config: KilnConfig) -> list[Artifact]:
    """Render `.importlinter` for *config*."""
    engine = TemplateEngine(package="rn_forge.kiln.modules.python")
    workspace = config.archetype == "python-lib"
    members = (
        [root_package(Path(package).name) for package in config.packages]
        if workspace
        else [root_package(config.name)]
    )
    context: dict[str, object] = {
        "kiln_version": __version__,
        "workspace": workspace,
        "members_block": "\n".join(f"    {member}" for member in members),
    }
    if not workspace:
        context["package"] = members[0]
    return [
        Artifact(
            ".importlinter",
            ArtifactKind.MANAGED,
            engine.render("importlinter.j2", context),
        )
    ]
