"""Resolve links between a root docs tree and the package sites it includes."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from pathspec.gitignore import GitIgnoreSpec
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import YamlUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.markdown import is_external, links
from rn_forge.kiln.modules.docs.policy import KEBAB_NAME

__all__ = [
    "check_packages",
    "excluded_docs",
    "package_mounts",
    "read_mkdocs",
    "resolve_link",
]

GOVERNANCE_AREAS = ("adr", "specs", "releases", "plans", "runbooks")
URL_KEYS = ("Documentation", "Source", "Changelog", "Issues")
RELEASE_HEADING = re.compile(r"^## \[\d+\.\d+\.\d+\] - \d{4}-\d{2}-\d{2}$")


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


def _error(code: str, path: Path, message: str) -> Finding:
    return Finding(
        code=f"docs.{code}", severity=Severity.ERROR, message=message, path=str(path)
    )


def _toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}


def _nav_names(node: object, page: str) -> bool:
    if isinstance(node, str):
        return node == page
    if isinstance(node, Mapping):
        return any(_nav_names(v, page) for v in cast(Mapping[str, Any], node).values())
    if isinstance(node, list):
        return any(_nav_names(v, page) for v in cast(list[Any], node))
    return False


def _check_changelog(root: Path, package: str) -> list[Finding]:
    path = root / package / "CHANGELOG.md"
    if not path.is_file():
        return [_error("package-changelog", path, "CHANGELOG.md does not exist")]
    headings = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("## ")
    ]
    findings = [
        _error(
            "package-changelog",
            path,
            f"{line!r} is not '## [x.y.z] - YYYY-MM-DD'",
        )
        for line in headings
        if line != "## [Unreleased]" and not RELEASE_HEADING.match(line)
    ]
    if "## [Unreleased]" not in headings:
        findings.append(
            _error("package-changelog", path, "no '## [Unreleased]' heading")
        )
    return findings


def _check_changelog_page(root: Path, package: str) -> list[Finding]:
    page = root / package / "docs" / "changelog.md"
    findings: list[Finding] = []
    if not page.is_file():
        findings.append(
            _error("package-changelog-page", page, "docs/changelog.md does not exist")
        )
    elif f'--8<-- "{package}/CHANGELOG.md"' not in page.read_text(encoding="utf-8"):
        findings.append(
            _error(
                "package-changelog-page",
                page,
                f'does not contain --8<-- "{package}/CHANGELOG.md"',
            )
        )
    mkdocs_yml = root / package / "mkdocs.yml"
    if mkdocs_yml.is_file() and not _nav_names(
        read_mkdocs(mkdocs_yml).get("nav"), "changelog.md"
    ):
        findings.append(
            _error(
                "package-changelog-page", mkdocs_yml, "nav does not name changelog.md"
            )
        )
    return findings


def _table(data: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    """The nested table at *keys* in *data*, or an empty one."""
    node: Any = data
    for key in keys:
        node = cast(dict[str, Any], node).get(key) if isinstance(node, dict) else None
    return cast(dict[str, Any], node) if isinstance(node, dict) else {}


def _check_urls(root: Path, package: str) -> list[Finding]:
    path = root / package / "pyproject.toml"
    urls = _table(_toml(path), "project", "urls")
    return [
        _error("package-urls", path, f"[project.urls] {key} must be an https:// URL")
        for key in URL_KEYS
        if not (isinstance(urls.get(key), str) and urls[key].startswith("https://"))
    ]


def _check_readme(root: Path, package: str) -> list[Finding]:
    path = root / package / "README.md"
    if not path.is_file():
        return []
    return [
        _error("package-readme-relative-link", path, f"{link} is a relative link")
        for link in links(path.read_text(encoding="utf-8"))
        if not is_external(link)
    ]


def _check_package(root: Path, package: str) -> list[Finding]:
    base = root / package
    docs = base / "docs"
    findings: list[Finding] = []
    if not (base / "mkdocs.yml").is_file():
        findings.append(_error("package-missing-mkdocs", base, "no mkdocs.yml"))
    if not (docs / "index.md").is_file():
        findings.append(_error("package-missing-index", docs, "no docs/index.md"))
    guides = docs / "guides"
    if not guides.is_dir():
        findings.append(_error("package-missing-guides", guides, "no docs/guides/"))
    else:
        findings.extend(
            _error("kebab-case", page, "not kebab-case")
            for page in sorted(guides.rglob("*.md"))
            if not page.name.startswith("_") and not KEBAB_NAME.match(page.name)
        )
    findings.extend(
        _error(
            "package-governance-area",
            docs / name,
            f"{name}/ belongs in the root docs, not in a package site",
        )
        for name in GOVERNANCE_AREAS
        if (docs / name).exists()
    )
    findings.extend(_check_changelog(root, package))
    findings.extend(_check_changelog_page(root, package))
    findings.extend(_check_urls(root, package))
    findings.extend(_check_readme(root, package))
    return findings


def _workspace_members(root: Path) -> list[str]:
    """The root workspace's members, with globs expanded, relative to *root*."""
    patterns: Any = _table(
        _toml(root / "pyproject.toml"), "tool", "uv", "workspace"
    ).get("members", [])
    members: list[str] = []
    for pattern in cast(list[str], patterns) if isinstance(patterns, list) else []:
        members.extend(
            path.relative_to(root).as_posix()
            for path in sorted(root.glob(pattern))
            if path.is_dir()
        )
    return members


def check_packages(root: Path, config: KilnConfig) -> list[Finding]:
    """Check the package docs sites of a repository.

    Args:
        root: The repository root.
        config: The repository's kiln config.

    Returns:
        The findings. For ``python-lib``, each ``config.packages`` entry is
        checked and each workspace member that is not listed is reported; for
        any other archetype, a workspace member or package with a ``docs/``
        directory or a ``mkdocs.yml`` is reported.
    """
    root = root.resolve()
    members = _workspace_members(root)
    if config.archetype == "python-lib":
        findings = [
            f for package in config.packages for f in _check_package(root, package)
        ]
        findings.extend(
            _error(
                "package-unlisted",
                root / member,
                f"{member} is a workspace member not listed in config.packages",
            )
            for member in members
            if member not in config.packages
        )
        return findings
    return [
        _error(
            "package-docs-not-allowed",
            root / member,
            "package docs sites are python-lib only (kiln ADR-0008); "
            f"document {member} in the root site",
        )
        for member in dict.fromkeys([*members, *config.packages])
        if (root / member / "docs").is_dir() or (root / member / "mkdocs.yml").is_file()
    ]
