"""Scaffolding: a package's own site, seeded by `kiln generate`."""

from __future__ import annotations

import textwrap
from pathlib import Path

from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.architecture import records_for
from rn_forge.kiln.modules.docs.artifacts import ADR_INDEX, seed_context
from rn_forge.kiln.modules.docs.packages import project_urls

__all__ = ["PACKAGE_SEEDS", "add_package", "scaffold_adr_index"]

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
    urls = project_urls(root / package / "pyproject.toml")
    links = " · ".join(
        f"[{key}]({urls[key]!s})" for key in ("Documentation", "Changelog", "Source")
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


def scaffold_adr_index(root: Path, config: KilnConfig) -> None:
    """Write `docs/adr/index.md` when records render and the file is absent.

    Does nothing unless the docs profile is `mkdocs` and a record applies; kiln's
    block is then appended by the next apply.
    """
    target = root / ADR_INDEX
    if config.docs_profile != "mkdocs" or not records_for(config) or target.exists():
        return
    engine = TemplateEngine.cached(package="rn_forge.kiln.modules.docs")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        engine.render(f"{ADR_INDEX}.j2", seed_context(config)), encoding="utf-8"
    )
