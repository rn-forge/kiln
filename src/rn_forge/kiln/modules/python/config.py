"""The `[archetype.<name>]` config section."""

from __future__ import annotations

from pydantic import Field
from rn_forge.commons.lang.models import StrictModel

__all__ = ["ArchetypeConfig", "PackagesConfig"]


class PackagesConfig(StrictModel):
    """A Python archetype's workspace members."""

    packages: list[str] = Field(default_factory=list)


class ArchetypeConfig(StrictModel):
    """Per-archetype settings, one table per archetype name."""

    python_app: PackagesConfig | None = Field(default=None, alias="python-app")
    python_tool: PackagesConfig | None = Field(default=None, alias="python-tool")
    python_lib: PackagesConfig | None = Field(default=None, alias="python-lib")

    def packages_for(self, archetype: str) -> list[str]:
        """The `packages` list of *archetype*'s table, or empty without one."""
        for field_name, field in type(self).model_fields.items():
            if field.alias == archetype:
                section = getattr(self, field_name)
                return (
                    list(section.packages)
                    if isinstance(section, PackagesConfig)
                    else []
                )
        return []
