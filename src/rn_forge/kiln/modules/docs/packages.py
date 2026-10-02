"""Resolve links between a root docs tree and the package sites it includes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from pathspec.gitignore import GitIgnoreSpec
from rn_forge.commons.fs.documents import YamlUtils

__all__ = ["excluded_docs", "package_mounts", "read_mkdocs", "resolve_link"]


def read_mkdocs(mkdocs_yml: Path) -> dict[str, Any]:
    """The mapping in *mkdocs_yml*, or an empty one if it holds none."""
    config: Any = YamlUtils.read_file(mkdocs_yml)
    return cast(dict[str, Any], config) if isinstance(config, dict) else {}


def excluded_docs(mkdocs_yml: Path) -> GitIgnoreSpec:
    """The pages *mkdocs_yml*'s ``exclude_docs`` keeps out of the site.

    Args:
        mkdocs_yml: The site's ``mkdocs.yml``, which may not exist.

    Returns:
        A spec matched against paths relative to ``docs_dir``. It matches
        nothing when the file or the key is absent.
    """
    block = (
        read_mkdocs(mkdocs_yml).get("exclude_docs") if mkdocs_yml.is_file() else None
    )
    lines = block.splitlines() if isinstance(block, str) else []
    return GitIgnoreSpec.from_lines(lines)


def package_mounts(root: Path, packages: Sequence[str]) -> dict[str, Path]:
    """Map each package's ``site_name`` to its resolved docs directory.

    Args:
        root: The repository root.
        packages: Package directories, relative to *root*.

    Returns:
        The mounts. A package with no ``mkdocs.yml``, or whose ``mkdocs.yml``
        has no ``site_name``, is left out.
    """
    root = root.resolve()
    mounts: dict[str, Path] = {}
    for package in packages:
        mkdocs_yml = root / package / "mkdocs.yml"
        if not mkdocs_yml.is_file():
            continue
        config = read_mkdocs(mkdocs_yml)
        site_name = config.get("site_name")
        if not isinstance(site_name, str):
            continue
        docs_dir = str(config.get("docs_dir", "docs"))
        mounts[site_name] = (root / package / docs_dir).resolve()
    return mounts


def resolve_link(
    page: Path, target: str, docs_root: Path, mounts: Mapping[str, Path]
) -> Path:
    """Resolve *target* against *page*'s directory, following package mounts.

    Args:
        page: The page holding the link.
        target: The link's path, without its anchor.
        docs_root: The docs tree *page* belongs to.
        mounts: The package mounts, from :func:`package_mounts`.

    Returns:
        The resolved path. A path that does not exist, lies under *docs_root*
        and starts with a mount's name is remapped into that mount's docs
        directory.
    """
    resolved = (page.parent / target).resolve()
    if resolved.exists():
        return resolved
    try:
        relative = resolved.relative_to(docs_root.resolve())
    except ValueError:
        return resolved
    if relative.parts and relative.parts[0] in mounts:
        return mounts[relative.parts[0]].joinpath(*relative.parts[1:])
    return resolved
