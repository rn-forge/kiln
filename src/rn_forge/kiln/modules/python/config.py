"""The `[archetype.<name>]` config section."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from rn_forge.commons.lang.models import StrictModel

__all__ = ["ArchetypeConfig", "PackagesConfig", "WebApiConfig", "WebAppConfig"]


class PackagesConfig(StrictModel):
    """A Python archetype's workspace members."""

    packages: list[str] = Field(default_factory=list)


class WebApiConfig(StrictModel):
    """`[archetype.python-web-api]` — the API workspace's selectors."""

    backend: Literal["fastapi", "django"] = "fastapi"
    api_dir: str = "apps/api"
    admin_ui: bool = False


class WebAppConfig(StrictModel):
    """`[archetype.python-web-app]` — the API + frontend workspace's selectors."""

    backend: Literal["fastapi", "django"] = "fastapi"
    frontend: Literal["angular", "react", "svelte"] = "angular"
    api_dir: str = "apps/api"
    web_dir: str = "apps/web"
    nx_cloud: bool = False


class ArchetypeConfig(StrictModel):
    """Per-archetype settings, one table per archetype name."""

    python_app: PackagesConfig | None = Field(default=None, alias="python-app")
    python_tool: PackagesConfig | None = Field(default=None, alias="python-tool")
    python_lib: PackagesConfig | None = Field(default=None, alias="python-lib")
    python_web_api: WebApiConfig | None = Field(default=None, alias="python-web-api")
    python_web_app: WebAppConfig | None = Field(default=None, alias="python-web-app")

    def _section(self, archetype: str) -> StrictModel | None:
        for field_name, field in type(self).model_fields.items():
            if field.alias == archetype:
                return getattr(self, field_name)
        return None

    def packages_for(self, archetype: str) -> list[str]:
        """The `packages` list of *archetype*'s table, or empty without one."""
        section = self._section(archetype)
        return list(section.packages) if isinstance(section, PackagesConfig) else []

    def web_for(self, archetype: str) -> WebApiConfig | WebAppConfig | None:
        """*archetype*'s web selectors table, or None without one or off one."""
        section = self._section(archetype)
        return section if isinstance(section, WebApiConfig | WebAppConfig) else None
