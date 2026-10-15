"""The artifacts `python` renders: kiln's block in `.importlinter`."""

from __future__ import annotations

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig

__all__ = ["IMPORTLINTER_BLOCK", "render", "root_package"]

IMPORTLINTER_BLOCK = ManagedBlock("rn-forge kiln")
"""kiln's fenced block in the repo's `.importlinter`."""


def root_package(name: str) -> str:
    """The importable package name a repo-relative name renders to."""
    return name.replace("-", "_")


_FORBIDDEN_FRAMEWORKS = ("typer", "jinja2", "click", "django", "fastapi")


def render(config: KilnConfig) -> list[Artifact]:
    """Render `.importlinter` for *config*."""
    engine = TemplateEngine(package="rn_forge.kiln.modules.python")
    workspace = config.archetype == "python-lib"
    web = config.archetype in {"python-web-api", "python-web-app"}
    if workspace:
        members = [config.module_for(package) for package in config.packages]
    elif web:
        members = [root_package(f"{config.name}-api")]
    else:
        members = [root_package(config.name)]
    forbidden = [m for m in _FORBIDDEN_FRAMEWORKS if m != config.backend]
    context: dict[str, object] = {
        "kiln_version": __version__,
        "workspace": workspace,
        "members_block": "\n".join(f"    {member}" for member in members),
        "forbidden_block": "\n".join(f"    {module}" for module in forbidden),
    }
    if not workspace:
        context["package"] = members[0]
    return [
        Artifact(
            ".importlinter",
            ArtifactKind.BLOCK,
            engine.render("importlinter.j2", context),
            block=IMPORTLINTER_BLOCK,
        )
    ]
