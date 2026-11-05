"""Scaffolding: a package's own site, seeded by `kiln generate`."""

from __future__ import annotations

import textwrap
from pathlib import Path

from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig

__all__ = ["PACKAGE_SEEDS", "add_package"]

PACKAGE_SEEDS = (
    "mkdocs.yml",
    "docs/index.md",
    "docs/guides/usage.md",
    "docs/reference/api.md",
    "docs/changelog.md",
    "CHANGELOG.md",
    "README.md",
)
"""A package's seeded files, each rendered from `templates/package/<path>.j2`."""

_WRAP = 80
"""`.mdformat.toml`'s `wrap`; the README's links line is pre-wrapped to it."""


def add_package(root: Path, config: KilnConfig, name: str) -> list[Path]:
    """Seed `packages/<name>`'s site, changelog and README, skipping existing files.

    The README's links come from the package's `[project.urls]`, which the
    python scaffold has already written.

    Args:
        root: The repository root.
        config: The config, already listing the package.
        name: The package's distribution name.

    Returns:
        The files written, as paths under *root*.
    """
    if config.docs_profile != "mkdocs":
        return []
    package = f"packages/{name}"
    urls = _project_urls(root / package / "pyproject.toml")
    links = " · ".join(
        f"[{key}]({urls[key]})" for key in ("Documentation", "Changelog", "Source")
    )
    context = {
        "name": name,
        "module": config.module_for(package),
        "package": package,
        "links": textwrap.fill(
            links, width=_WRAP, break_long_words=False, break_on_hyphens=False
        ),
    }
    engine = TemplateEngine.cached(package="rn_forge.kiln.modules.docs")
    written: list[Path] = []
    for seed in PACKAGE_SEEDS:
        target = root / package / seed
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            engine.render(f"package/{seed}.j2", context), encoding="utf-8"
        )
        written.append(target)
    return written


def _project_urls(pyproject: Path) -> dict[str, str]:
    document = DocumentUtils.read(pyproject)
    return {
        key: str(value) for key, value in document["project"].get("urls", {}).items()
    }
