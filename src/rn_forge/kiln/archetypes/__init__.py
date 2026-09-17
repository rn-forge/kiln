"""What each archetype is: its modules, its dependency set, and its gate.

Each shipped archetype is a directory here holding an `archetype.toml`. A
repo's `config.toml` selects one by name; the `lifecycle` flag and the docs
profile then adjust what the manifest states.
"""

from __future__ import annotations

import tomllib
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.lang.models import StrictModel

if TYPE_CHECKING:
    from rn_forge.kiln.config import KilnConfig

__all__ = [
    "KILN_SOURCE",
    "RN_FORGE_PREFIX",
    "RN_FORGE_SOURCE",
    "Archetype",
    "Dependencies",
    "for_config",
    "load",
    "pyproject_paths",
    "requirement",
    "shipped",
]

RN_FORGE_PREFIX = "rn-forge-"
"""Every distribution the dependency contract governs starts with this."""

RN_FORGE_SOURCE = "git+https://github.com/rn-forge/pykit@feature/upgrade"
"""pykit's git source. Flipping to tags (E7) is a change to this constant alone."""
KILN_SOURCE = "git+https://github.com/rn-forge/kiln@feature/v1"
"""kiln's own git source, for the `rn-forge-kiln` dev dependency it scaffolds."""

_MANIFEST = "archetype.toml"
_TOOLING = "rn-forge-tooling"

_MKDOCS_VALIDATE = (
    "quality:lint:docs",
    "quality:lint:docs-structure",
    "quality:lint:docs-nav",
    "docs:build",
)


class Dependencies(StrictModel):
    """The rn-forge dependency set an archetype holds a repo to."""

    required: list[str] = Field(default_factory=list)
    """Distributions some distributable in the repo must depend on."""
    allowed: list[str] = Field(default_factory=list)
    """Every rn-forge distribution the repo may name, for any purpose."""


class Archetype(StrictModel):
    """One archetype's manifest."""

    name: str
    modules: list[str]
    """The modules this archetype enables, in apply order."""
    dependencies: Dependencies
    forbidden_tools: list[str]
    """Tools a CI step may never invoke directly."""
    required_validate: list[str]
    """Tasks that must stay reachable from `validate` — the `gate.shrunk` rule."""
    untested: dict[str, list[str]] = Field(default_factory=dict)
    """`kiln new` flag name to the values of it this kiln has not exercised yet."""


def shipped() -> tuple[str, ...]:
    """The name of every archetype this kiln ships, sorted."""
    root = files(__name__)
    return tuple(
        sorted(
            entry.name.replace("_", "-")
            for entry in root.iterdir()
            if entry.is_dir() and entry.joinpath(_MANIFEST).is_file()
        )
    )


def load(name: str) -> Archetype:
    """The manifest of the archetype called *name*.

    Raises:
        AppException: This kiln ships no such archetype, or its manifest is invalid.
    """
    manifest = files(__name__).joinpath(name.replace("-", "_"), _MANIFEST)
    if not name or not manifest.is_file():
        raise AppException(
            "Unknown archetype {!r} — this kiln ships {}", name, ", ".join(shipped())
        )
    document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    return Archetype.parse(document, source=f"archetype {name!r}")


def for_config(config: KilnConfig) -> Archetype:
    """The archetype *config* names, adjusted by its flags.

    `lifecycle = true` adds `rn-forge-tooling` to the dependency set, and
    `docs.profile = "mkdocs"` adds the docs gate to `required_validate`.

    Raises:
        AppException: The config names an archetype this kiln does not ship.
    """
    archetype = load(config.archetype)
    required = list(archetype.dependencies.required)
    allowed = list(archetype.dependencies.allowed)
    if config.lifecycle:
        required += [_TOOLING] if _TOOLING not in required else []
        allowed += [_TOOLING] if _TOOLING not in allowed else []

    required_validate = list(archetype.required_validate)
    if config.docs_profile == "mkdocs":
        required_validate += _MKDOCS_VALIDATE

    return archetype.model_copy(
        update={
            "dependencies": Dependencies(required=required, allowed=allowed),
            "required_validate": required_validate,
        }
    )


def requirement(distribution: str) -> str:
    """The pinned PEP 508 requirement line pykit's *distribution* resolves to."""
    return f"{distribution} @ {RN_FORGE_SOURCE}#subdirectory=packages/{distribution}"


def pyproject_paths(config: KilnConfig) -> tuple[Path, ...]:
    """Every `pyproject.toml` in the repo: the root, plus each workspace member."""
    return (
        Path("pyproject.toml"),
        *(Path(p) / "pyproject.toml" for p in config.packages),
    )
