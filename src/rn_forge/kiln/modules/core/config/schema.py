"""The composed `config.toml` schema.

The root is `schema_version`, `[source]`, `[repository]` and the `[cli]` and
`[lifecycle]` tables rn-forge-cli and rn-forge-tooling read; every enabled module adds its own section.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import ConfigDict, Field, create_model
from rn_forge.commons.lang.models import StrictModel

if TYPE_CHECKING:
    from rn_forge.kiln.modules.base import KilnModule

__all__ = [
    "SCHEMA_VERSION",
    "ConfigModel",
    "KilnPin",
    "RepositoryConfig",
    "RootConfig",
    "SourceConfig",
    "compose",
]

SCHEMA_VERSION = 1
"""The config schema this kiln understands."""


class ConfigModel(StrictModel):
    """A strict config model whose attribute docstrings become field descriptions."""

    model_config: ClassVar[ConfigDict] = {
        **StrictModel.model_config,
        "use_attribute_docstrings": True,
    }


class RepositoryConfig(ConfigModel):
    """What the repository asserts about itself."""

    name: str
    """The repository's name. It names the package and the project, and is
    written into generated files; changing it renames them on `kiln apply`."""
    archetype: str
    """The repository's shape, which sets its modules, files and dependencies.
    Changing it re-renders most generated files, and `kiln apply` does not
    migrate the code itself."""
    lifecycle: bool = False
    """Whether the repository installs itself as a tool (`kiln self` verbs).
    `python-tool` always does. Changing it adds or removes the lifecycle files
    on `kiln apply`."""


class KilnPin(ConfigModel):
    """The kiln this repository runs."""

    ref: str
    """A kiln release tag, `v<version>`; a branch only before kiln's first
    release. `kiln apply` pins the dev dependency and the CI install to it."""


class SourceConfig(ConfigModel):
    """The layer the config was resolved from, as last resolved."""

    location: str
    """A local path or a `git+` URL. `kiln config-update` re-reads the config
    from here and keeps this repository's own overrides."""
    ref: str | None = None
    """The branch or tag fetched from `location`. Default: the remote's default
    branch."""
    commit: str | None = None
    """The commit `ref` resolved to, recorded by `kiln config-update`. Default:
    none until a source has been fetched."""


class RootConfig(ConfigModel):
    """The sections every kiln config has, whatever its modules."""

    schema_version: int
    """The config schema this file was written for. `kiln config-upgrade`
    raises it; do not edit it by hand."""
    source: SourceConfig | None = None
    """Where this config was resolved from. Absent for a hand-written config."""
    repository: RepositoryConfig
    kiln: KilnPin | None = None
    """The kiln this repository pins. Absent until the first kiln release."""
    cli: dict[str, Any] | None = None
    """The command line this repository exposes, read by rn-forge-cli's
    `CliApp.from_config` and carried as written. `kiln apply` does not read it."""
    lifecycle: dict[str, Any] | None = None
    """The lifecycle verbs mounted under the CLI, read by rn-forge-tooling's
    `build_tool_app` and carried as written. `kiln apply` does not read it."""


def compose(modules: Sequence[KilnModule]) -> type[RootConfig]:
    """The schema of a config whose archetype enables *modules*."""
    sections: dict[str, Any] = {
        module.section: (model, Field(default_factory=model))
        for module in modules
        if module.section is not None and (model := module.config_model) is not None
    }
    return create_model("KilnConfigDocument", __base__=RootConfig, **sections)
