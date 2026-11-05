"""The `[archetype.<name>]` config section."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from rn_forge.kiln.modules.core.config.schema import ConfigModel

__all__ = [
    "MODULE_PATTERN",
    "AppConfig",
    "ArchetypeConfig",
    "LibConfig",
    "PackagesConfig",
    "WebApiConfig",
    "WebAppConfig",
]

MODULE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$")
"""A dotted import module, as `[tool.uv.build-backend] module-name` takes it."""


class PackagesConfig(ConfigModel):
    """A Python archetype's workspace members."""

    packages: list[str] = Field(default_factory=list)
    """Workspace member directories, one per package. `kiln apply` renders each
    member's `pyproject.toml`, tasks and CI entries; adding one needs
    `kiln new` or `init` to create its files first."""
    modules: dict[str, str] = Field(default_factory=dict)
    """The import module of a member whose name differs from its directory,
    keyed by the member's path in `packages`. Changing it rewrites the member's
    build and import-contract settings on `kiln apply`."""

    @model_validator(mode="after")
    def _modules_name_packages(self) -> PackagesConfig:
        for package, module in self.modules.items():
            if package not in self.packages:
                raise ValueError(f"modules: {package!r} is not in packages")
            if not MODULE_PATTERN.match(module):
                raise ValueError(
                    f"modules: {module!r} is not a dotted import module name"
                )
        return self


class AppConfig(PackagesConfig):
    """The one package of a `python-app` or `python-tool` repository."""

    module: str | None = None
    """The package's dotted import module. Changing it rewrites the build
    backend, import contracts and test and Sonar paths on `kiln apply`. Default:
    the repository name with `-` as `_`."""

    @model_validator(mode="after")
    def _module_is_dotted(self) -> AppConfig:
        if self.module is not None and not MODULE_PATTERN.match(self.module):
            raise ValueError(
                f"module: {self.module!r} is not a dotted import module name"
            )
        return self


class LibConfig(PackagesConfig):
    """A `python-lib` workspace's members and import contracts."""

    import_contracts: Literal["kiln", "own"] = "kiln"
    """Who writes the workspace's `.importlinter`: `kiln` renders it, `own`
    leaves it to the repository. Changing it adds or stops managing the file on
    `kiln apply`."""


class WebApiConfig(ConfigModel):
    """The API workspace's selectors."""

    backend: Literal["fastapi", "django"] = "fastapi"
    """The backend framework. Changing it re-renders the API member's
    dependencies and starter files on `kiln apply`."""
    api_dir: str = "apps/api"
    """The API member's directory. Changing it moves where `kiln apply` renders
    the member's files; it does not move existing code."""
    admin_ui: bool = False
    """Whether the API serves an admin UI. Reserved: `kiln apply` renders
    nothing from it yet."""


class WebAppConfig(ConfigModel):
    """The API and frontend workspace's selectors."""

    backend: Literal["fastapi", "django"] = "fastapi"
    """The backend framework. Changing it re-renders the API member's
    dependencies and starter files on `kiln apply`."""
    frontend: Literal["angular", "react", "svelte"] = "angular"
    """The frontend framework. Changing it re-renders the frontend member's
    files and tasks on `kiln apply`."""
    api_dir: str = "apps/api"
    """The API member's directory. Changing it moves where `kiln apply` renders
    the member's files; it does not move existing code."""
    web_dir: str = "apps/web"
    """The frontend member's directory. Changing it moves where `kiln apply`
    renders the member's files; it does not move existing code."""


class ArchetypeConfig(ConfigModel):
    """Settings of the repository's archetype, in one table named for it."""

    python_app: AppConfig | None = Field(default=None, alias="python-app")
    """The `python-app` archetype's settings."""
    python_tool: AppConfig | None = Field(default=None, alias="python-tool")
    """The `python-tool` archetype's settings."""
    python_lib: LibConfig | None = Field(default=None, alias="python-lib")
    """The `python-lib` archetype's settings."""
    python_web_api: WebApiConfig | None = Field(default=None, alias="python-web-api")
    """The `python-web-api` archetype's settings."""
    python_web_app: WebAppConfig | None = Field(default=None, alias="python-web-app")
    """The `python-web-app` archetype's settings."""

    def _section(self, archetype: str) -> ConfigModel | None:
        for field_name, field in type(self).model_fields.items():
            if field.alias == archetype:
                return getattr(self, field_name)
        return None

    def packages_for(self, archetype: str) -> list[str]:
        """The `packages` list of *archetype*'s table, or empty without one."""
        section = self._section(archetype)
        return list(section.packages) if isinstance(section, PackagesConfig) else []

    def module_for(self, archetype: str, package: str) -> str:
        """The import module of *package*: its `modules` entry, or the name derived from its path."""
        section = self._section(archetype)
        if isinstance(section, PackagesConfig) and package in section.modules:
            return section.modules[package]
        return Path(package).name.replace("-", "_")

    def module_of(self, archetype: str) -> str | None:
        """The declared import module of a single-package *archetype*, or None."""
        section = self._section(archetype)
        return section.module if isinstance(section, AppConfig) else None

    def import_contracts_for(self, archetype: str) -> str:
        """Who writes *archetype*'s import contracts: `kiln`, or `own` for a library."""
        section = self._section(archetype)
        return section.import_contracts if isinstance(section, LibConfig) else "kiln"

    def web_for(self, archetype: str) -> WebApiConfig | WebAppConfig | None:
        """*archetype*'s web selectors table, or None without one or off one."""
        section = self._section(archetype)
        return section if isinstance(section, WebApiConfig | WebAppConfig) else None
