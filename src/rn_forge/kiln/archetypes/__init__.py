"""What each archetype is: its modules, its dependency set, and its gate.

Each shipped archetype is a directory here holding an `archetype.toml`. A
repo's `config.toml` selects one by name; the `lifecycle` flag and the docs
profile then adjust what the manifest states.
"""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.lang.models import StrictModel

if TYPE_CHECKING:
    from rn_forge.kiln.config import KilnConfig

__all__ = [
    "KILN_GIT",
    "KILN_REF",
    "PYKIT_GIT",
    "RN_FORGE_PREFIX",
    "RN_FORGE_TAGS",
    "Archetype",
    "Dependencies",
    "ceiling",
    "floor",
    "for_config",
    "load",
    "pyproject_paths",
    "requirement",
    "shipped",
    "version_key",
]

RN_FORGE_PREFIX = "rn-forge-"
"""Every distribution the dependency contract governs starts with this."""

PYKIT_GIT = "git+https://github.com/rn-forge/pykit"
"""pykit's git source, without a ref."""
RN_FORGE_TAGS = {
    "rn-forge-commons": "rn-forge-commons-v0.10.1",
    "rn-forge-cli": "rn-forge-cli-v0.2.1",
    "rn-forge-tooling": "rn-forge-tooling-v0.4.0",
    "rn-forge-web": "rn-forge-web-v0.3.3",
    "rn-forge-auth": "rn-forge-auth-v0.2.1",
    "rn-forge-django": "rn-forge-django-v0.7.0",
    "rn-forge-fastapi": "rn-forge-fastapi-v0.5.2",
    "rn-forge-sqlalchemy": "rn-forge-sqlalchemy-v0.2.4",
    "rn-forge-data": "rn-forge-data-v0.1.6",
}
"""pykit's release tags, read from pykit on 2026-11-20
(`release-11`). A requirement's floor is its tag's version
([ADR-0018](https://github.com/rn-forge/kiln/blob/main/docs/adr/ADR-0018.md))."""
KILN_GIT = "git+https://github.com/rn-forge/kiln"
KILN_REF = "feature/v1"
"""The ref `kiln new` pins, until a kiln release is tagged."""


def kiln_command(ref: str, script: str = "kiln") -> str:
    """The command that runs kiln's *script* at *ref*, in its own environment."""
    return f'uvx --from "rn-forge-kiln @ {KILN_GIT}@{ref}" {script}'


_MANIFEST = "archetype.toml"
_TOOLING = "rn-forge-tooling"

_MKDOCS_VALIDATE = ("docs:build",)


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
    entrypoint_exempt: list[str] = Field(default_factory=list)
    """Workflow `run:` texts, stripped, that `ci-entrypoint` lets through."""
    required_validate: list[str]
    """Tasks that must stay reachable from `validate` — a render test holds it."""
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
    if name not in shipped():
        raise AppException(
            "Unknown archetype {!r} — this kiln ships {}", name, ", ".join(shipped())
        )
    document = DocumentUtils.read(manifest)
    return Archetype.parse(document, source=f"archetype {name!r}")


def for_config(config: KilnConfig) -> Archetype:
    """The archetype *config* names, adjusted by its flags.

    `lifecycle = true` adds `rn-forge-tooling` to the dependency set,
    `config.backend` (a web archetype only) adds `rn-forge-<backend>`, and
    `docs.profile = "mkdocs"` adds the docs gate and an enabled licences check
    adds its task to `required_validate`.

    Raises:
        AppException: The config names an archetype this kiln does not ship.
    """
    archetype = load(config.archetype)
    required = list(archetype.dependencies.required)
    allowed = list(archetype.dependencies.allowed)
    if config.backend:
        framework = f"{RN_FORGE_PREFIX}{config.backend}"
        required += [framework] if framework not in required else []
        allowed += [framework] if framework not in allowed else []
    if config.lifecycle:
        required += [_TOOLING] if _TOOLING not in required else []
        allowed += [_TOOLING] if _TOOLING not in allowed else []

    required_validate = list(archetype.required_validate)
    if config.docs_profile == "mkdocs":
        required_validate += _MKDOCS_VALIDATE
    if config.licenses_enabled:
        stack = "node" if config.archetype == "node-lib" else "python"
        required_validate.append(f"{stack}:lint:licenses")

    return archetype.model_copy(
        update={
            "dependencies": Dependencies(required=required, allowed=allowed),
            "required_validate": required_validate,
        }
    )


def ceiling(version: str) -> str:
    """The next breaking version after *version*: the next minor before 1.0, the next major after."""
    major, minor, _ = (int(part) for part in version.split("."))
    return f"0.{minor + 1}" if major == 0 else str(major + 1)


def requirement(distribution: str) -> str:
    """The version range pykit's *distribution* resolves to from PyPI.

    Raises:
        KeyError: *distribution* has no release tag in `RN_FORGE_TAGS`.
    """
    version = RN_FORGE_TAGS[distribution].rpartition("-v")[2]
    return f"{distribution}>={version},<{ceiling(version)}"


def floor(requirement: str) -> str | None:
    """Return the lower bound declared by a requirement or git tag, if any."""
    specifier, _, url = requirement.partition(";")[0].partition("@")
    if url:
        source, _, ref = url.strip().partition("#")[0].rpartition("@")
        if not source.startswith("git+"):
            return None
        match = re.search(r"-v(\d+\.\d+\.\d+)", ref)
    else:
        specifier = re.sub(r"^\s*[\w.-]+\s*(?:\[[^\]]*\])?", "", specifier)
        match = re.search(r"(?:>=|==|~=)\s*(\d+(?:\.\d+)*)", specifier)
    return match.group(1) if match else None


def version_key(version: str) -> tuple[int, ...]:
    """Return numeric version parts padded to at least three components."""
    parts = tuple(int(part) for part in version.split("."))
    return parts + (0,) * (3 - len(parts))


def pyproject_paths(config: KilnConfig) -> tuple[Path, ...]:
    """Every `pyproject.toml` in the repo: the root, plus each workspace member."""
    return (
        Path("pyproject.toml"),
        *(Path(p) / "pyproject.toml" for p in config.packages),
    )
