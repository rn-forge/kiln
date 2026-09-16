"""The composed `config.toml` schema.

The root is `schema_version`, `[source]`, `[repository]` and the `[cli]` table
rn-forge-cli reads; every enabled module adds its own section.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from pydantic import Field, create_model
from rn_forge.commons.lang.models import StrictModel

if TYPE_CHECKING:
    from rn_forge.kiln.modules.base import KilnModule

__all__ = [
    "SCHEMA_VERSION",
    "RepositoryConfig",
    "RootConfig",
    "SourceConfig",
    "compose",
]

SCHEMA_VERSION = 1
"""The config schema this kiln understands."""


class RepositoryConfig(StrictModel):
    """`[repository]` — what the repo asserts about itself."""

    name: str
    archetype: str
    lifecycle: bool = False
    """Whether the repo installs itself; `python-tool` implies it."""


class SourceConfig(StrictModel):
    """`[source]` — the layer the config was resolved from, as last resolved."""

    location: str
    """A local path, or a `git+` URL."""
    ref: str | None = None
    commit: str | None = None
    """The commit `ref` resolved to."""


class RootConfig(StrictModel):
    """The sections every kiln config has, whatever its modules."""

    schema_version: int
    source: SourceConfig | None = None
    repository: RepositoryConfig
    cli: dict[str, Any] | None = None
    """rn-forge-cli's declared command line, carried as written."""


def compose(modules: Sequence[KilnModule]) -> type[RootConfig]:
    """The schema of a config whose archetype enables *modules*."""
    sections: dict[str, Any] = {
        module.section: (model, Field(default_factory=model))
        for module in modules
        if module.section is not None and (model := module.config_model) is not None
    }
    return create_model("KilnConfigDocument", __base__=RootConfig, **sections)
