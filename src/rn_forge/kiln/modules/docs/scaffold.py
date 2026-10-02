"""Scaffolding: the repo-owned body of `mkdocs.yml`.

Runs once, from `kiln new`, before the first `apply`. The body ends with the empty
derived-nav fence, which `kiln docs-generate` fills.
"""

from __future__ import annotations

import textwrap
import tomllib
from pathlib import Path

from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig

__all__ = ["PACKAGE_SEEDS", "add_package", "scaffold"]

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


def scaffold(root: Path, config: KilnConfig) -> None:
    """Write `mkdocs.yml`'s body into *root*, for an `mkdocs` repo that has none."""
    target = root / "mkdocs.yml"
    if config.docs_profile != "mkdocs" or target.exists():
        return
    sources = (
        ["packages/*/src"]
        if config.archetype == "python-lib"
        else ["src", *(f"{package}/src" for package in config.packages)]
    )
    engine = TemplateEngine(package="rn_forge.kiln.modules.docs")
    target.write_text(
        engine.render(
            "mkdocs.yml.j2",
            {
                "name": config.name,
                "archetype": config.archetype,
                "source_paths": ", ".join(sources),
            },
        ),
        encoding="utf-8",
    )


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
        "module": name.replace("-", "_"),
        "package": package,
        "links": textwrap.fill(
            links, width=_WRAP, break_long_words=False, break_on_hyphens=False
        ),
    }
    engine = TemplateEngine(package="rn_forge.kiln.modules.docs")
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
    document = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return {
        key: str(value) for key, value in document["project"].get("urls", {}).items()
    }
