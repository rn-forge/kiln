"""The `[docs]` config section."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
)
from rn_forge.commons.lang.models import StrictModel

__all__ = ["DocsConfig", "DocsMkdocs"]

_KILN_THEME_KEYS = frozenset({"name", "features", "palette"})


class DocsMkdocs(StrictModel):
    """The `[docs.mkdocs]` table: settings kiln adds to the rendered `mkdocs.yml`.

    The nav is not here; nav additions go in `docs/_areas.yml`.
    """

    plugins: list[str | dict[str, Any]] | None = None
    """Plugin entries, appended after kiln's own."""
    markdown_extensions: list[str | dict[str, Any]] | None = None
    """Markdown extension entries, appended after kiln's own."""
    theme: dict[str, Any] | None = None
    """Keys merged into `theme:`; not `name`, `features` or `palette`, which kiln sets."""
    extra: dict[str, Any] | None = None
    """The top-level `extra:` mapping."""
    extra_css: list[str] | None = None
    """The top-level `extra_css:` list."""
    extra_javascript: list[str | dict[str, Any]] | None = None
    """The top-level `extra_javascript:` list."""
    site_description: str | None = None
    """Replaces the rendered default `site_description`."""

    @field_validator("theme")
    @classmethod
    def _theme_keys_kiln_does_not_set(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        taken = sorted(set(value or {}) & _KILN_THEME_KEYS)
        if taken:
            msg = f"docs.mkdocs.theme cannot set {', '.join(taken)}: kiln renders them"
            raise ValueError(msg)
        return value


class DocsConfig(StrictModel):
    """How the repo publishes its documentation."""

    profile: Literal["mkdocs", "external", "none"] = "none"
    site_dir: str = ".docs-site"
    """Where `mkdocs` builds the site; `mkdocs` only."""
    external_url: str = ""
    """Where the docs live; `external` only."""
    mkdocs: DocsMkdocs = Field(default_factory=DocsMkdocs)
    """Settings added to the rendered `mkdocs.yml`; `mkdocs` only."""

    @model_serializer(mode="wrap")
    def _omit_empty_mkdocs(self, handler: SerializerFunctionWrapHandler) -> Any:
        data = handler(self)
        if not self.mkdocs.model_fields_set:
            data.pop("mkdocs", None)
        return data
