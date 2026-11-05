"""The artifacts `docs` renders: the managed `_structure.md` rules and the seeded rest of the docs tree."""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.commons.generation.templated import TemplateArtifact, render_artifacts
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.derived import NAV_BLOCK
from rn_forge.kiln.modules.core.settle import DerivedArtifact
from rn_forge.kiln.modules.docs.config import DocsConfig
from rn_forge.kiln.modules.docs.nav import build_nav

__all__ = ["SEEDS", "render"]

SEEDS = (
    "docs/_areas.yml",
    "docs/_structure.md",
    "docs/index.md",
    "docs/architecture/_structure.md",
    "docs/architecture/index.md",
    "docs/guides/_structure.md",
    "docs/guides/index.md",
    "docs/guides/development.md",
    "docs/runbooks/_structure.md",
    "docs/runbooks/index.md",
    "docs/runbooks/adding-a-package.md",
    "docs/runbooks/recovering-from-drift.md",
    "docs/releases/_structure.md",
    "docs/releases/index.md",
    "docs/specs/_structure.md",
    "docs/specs/index.md",
    "docs/specs/ideas/index.md",
    "docs/specs/epics/index.md",
    "docs/reference/_structure.md",
    "docs/reference/index.md",
    "docs/reference/python-api.md",
    "docs/adr/_structure.md",
    "docs/adr/index.md",
)
"""Every docs path, each rendered from `templates/<path>.j2`; `_structure.md` is managed."""

_PACKAGE_SITE_SKIPS = ("docs/reference/",)
"""Seeds a `python-lib` repository does not carry: each package's reference
lives in its own site."""


_PYTHON_LIB_ONLY = ("docs/runbooks/adding-a-package.md",)
"""Seeds only a `python-lib` repository carries."""


_APP_TOOL_ONLY = ("docs/reference/python-api.md",)
"""Seeds only a `python-app` or `python-tool` repository carries."""


def render(config: KilnConfig, root: Path) -> list[Artifact]:
    """Render `mkdocs.yml` and the seeded docs tree, for an `mkdocs` repo at *root*."""
    if config.docs_profile != "mkdocs":
        return []
    engine = TemplateEngine.cached(package="rn_forge.kiln.modules.docs")
    context = {
        "name": config.name,
        "archetype": config.archetype,
        "module": config.module,
        "kiln_version": __version__,
    }
    skipped = (
        _PACKAGE_SITE_SKIPS if config.archetype == "python-lib" else _PYTHON_LIB_ONLY
    )
    if config.archetype not in ("python-app", "python-tool"):
        skipped += _APP_TOOL_ONLY
    rendered = render_artifacts(
        engine,
        context,
        [
            TemplateArtifact(path, _kind(path), enabled=not path.startswith(skipped))
            for path in SEEDS
        ],
    )
    return [_mkdocs_yml(engine, config, root), *rendered]


def _mkdocs_yml(engine: TemplateEngine, config: KilnConfig, root: Path) -> Artifact:
    """`mkdocs.yml`, rendered whole; the nav fence holds the nav of the tree as it is."""
    docs = getattr(config.document, "docs", None)
    if not isinstance(docs, DocsConfig):
        docs = DocsConfig()
    extra = docs.mkdocs
    packages = config.packages if config.archetype == "python-lib" else ()
    sources = (
        ["packages/*/src"]
        if config.archetype == "python-lib"
        else ["src", *(f"{package}/src" for package in config.packages)]
    )
    description = (
        extra.site_description
        or f"{config.name} — architecture, guides, and API reference."
    )
    text = engine.render(
        "mkdocs.yml.j2",
        {
            "name": config.name,
            "archetype": config.archetype,
            "kiln_version": __version__,
            "source_paths": ", ".join(sources),
            "site_dir": docs.site_dir,
            "site_description_line": _yaml({"site_description": description}).rstrip(),
            "theme_extra": _indent(_yaml(extra.theme)) if extra.theme else "",
            "plugins_extra": _indent(_yaml(extra.plugins)),
            "markdown_extensions_extra": _indent(_yaml(extra.markdown_extensions)),
            "top_level_extra": "".join(
                _yaml({key: value})
                for key, value in (
                    ("extra", extra.extra),
                    ("extra_css", extra.extra_css),
                    ("extra_javascript", extra.extra_javascript),
                )
                if value
            ),
        },
    )
    nav = (
        build_nav(root / "docs", packages)
        if (root / "docs" / "_areas.yml").is_file()
        else ""
    )
    return DerivedArtifact(
        "mkdocs.yml", ArtifactKind.MANAGED, NAV_BLOCK.render(text, nav)
    )


def _yaml(value: Mapping[str, Any] | Sequence[Any] | None) -> str:
    """*value* as block YAML, or `""` when it is empty."""
    return YamlUtils.serialize(value, width=sys.maxsize) if value else ""


def _indent(text: str) -> str:
    return "".join(f"  {line}\n" for line in text.splitlines())


def _kind(path: str) -> ArtifactKind:
    managed = path.endswith("/_structure.md")
    return ArtifactKind.MANAGED if managed else ArtifactKind.SEEDED
