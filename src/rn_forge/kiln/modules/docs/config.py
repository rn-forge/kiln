"""The `[docs]` config section."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
)

from rn_forge.kiln.modules.core.config.schema import ConfigModel

__all__ = ["DocsConfig", "DocsMkdocs"]

_KILN_THEME_KEYS = frozenset({"name", "features", "palette"})


class DocsMkdocs(ConfigModel):
    """Settings kiln adds to the rendered `mkdocs.yml`.

    The nav is not here; nav additions go in `docs/_areas.yml`.
    """

    plugins: list[str | dict[str, Any]] | None = None
    """Plugin entries, appended after kiln's own in `mkdocs.yml`. Changing the
    list rewrites `mkdocs.yml` on `kiln apply`."""
    markdown_extensions: list[str | dict[str, Any]] | None = None
    """Markdown extension entries, appended after kiln's own in `mkdocs.yml`.
    Changing the list rewrites `mkdocs.yml` on `kiln apply`."""
    theme: dict[str, Any] | None = None
    """Keys merged into `theme:` in `mkdocs.yml`; not `name`, `features` or
    `palette`, which kiln sets. Changing them rewrites `mkdocs.yml` on
    `kiln apply`."""
    extra: dict[str, Any] | None = None
    """The top-level `extra:` mapping of `mkdocs.yml`. Changing it rewrites
    `mkdocs.yml` on `kiln apply`."""
    extra_css: list[str] | None = None
    """The top-level `extra_css:` list of `mkdocs.yml`. Changing it rewrites
    `mkdocs.yml` on `kiln apply`."""
    extra_javascript: list[str | dict[str, Any]] | None = None
    """The top-level `extra_javascript:` list of `mkdocs.yml`. Changing it
    rewrites `mkdocs.yml` on `kiln apply`."""
    site_description: str | None = None
    """Replaces the `site_description` in `mkdocs.yml`. Changing it rewrites
    `mkdocs.yml` on `kiln apply`. Default: the description kiln renders."""

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


class DocsConfig(ConfigModel):
    """How the repo publishes its documentation."""

    profile: Literal["mkdocs", "external", "none"] = "none"
    """How the docs are published. `mkdocs` renders the docs tree, `mkdocs.yml`
    and the docs tasks and CI job; `external` links to docs hosted elsewhere;
    `none` has no docs. Changing it adds or removes those files on `kiln apply`."""
    site_dir: str = ".docs-site"
    """Where `mkdocs` builds the site. It is ignored by git and cleaned by
    `task clean`; changing it rewrites `.gitignore`, the docs tasks and the CI
    workflows on `kiln apply`. `mkdocs` only."""
    external_url: str = ""
    """Where the docs live, linked from the generated `CLAUDE.md` block. Changing
    it rewrites that block on `kiln apply`. `external` only."""
    mkdocs: DocsMkdocs = Field(default_factory=DocsMkdocs)
    """Settings added to the rendered `mkdocs.yml`. `mkdocs` only."""

    @model_serializer(mode="wrap")
    def _omit_empty_mkdocs(self, handler: SerializerFunctionWrapHandler) -> Any:
        data = handler(self)
        if not self.mkdocs.model_fields_set:
            data.pop("mkdocs", None)
        return data
