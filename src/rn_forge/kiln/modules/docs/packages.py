"""Check the package docs sites of a repository."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from rn_forge.commons.findings import Finding
from rn_forge.commons.fs.documents import DocumentError, DocumentUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs import parsed
from rn_forge.kiln.modules.docs.findings import error
from rn_forge.kiln.modules.docs.mkdocs import read_mkdocs
from rn_forge.kiln.modules.docs.pages import nav_pages
from rn_forge.kiln.modules.docs.policy import KEBAB_NAME

__all__ = ["check_packages", "project_urls"]

GOVERNANCE_AREAS = ("adr", "specs", "releases", "plans", "runbooks")
URL_KEYS = ("Documentation", "Source", "Changelog", "Issues")
RELEASE_HEADING = re.compile(r"^## \[\d+\.\d+\.\d+\] - \d{4}-\d{2}-\d{2}$")


def _toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return DocumentUtils.read(path, missing_ok=True)
    except DocumentError:
        return {}


def _check_changelog(root: Path, package: str) -> list[Finding]:
    path = root / package / "CHANGELOG.md"
    if not path.is_file():
        return [error("package-changelog", path, "CHANGELOG.md does not exist")]
    headings = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("## ")
    ]
    findings = [
        error(
            "package-changelog",
            path,
            f"{line!r} is not '## [x.y.z] - YYYY-MM-DD'",
        )
        for line in headings
        if line != "## [Unreleased]" and not RELEASE_HEADING.match(line)
    ]
    if "## [Unreleased]" not in headings:
        findings.append(
            error("package-changelog", path, "no '## [Unreleased]' heading")
        )
    return findings


def _check_changelog_page(root: Path, package: str) -> list[Finding]:
    page = root / package / "docs" / "changelog.md"
    findings: list[Finding] = []
    if not page.is_file():
        findings.append(
            error("package-changelog-page", page, "docs/changelog.md does not exist")
        )
    elif f'--8<-- "{package}/CHANGELOG.md"' not in page.read_text(encoding="utf-8"):
        findings.append(
            error(
                "package-changelog-page",
                page,
                f'does not contain --8<-- "{package}/CHANGELOG.md"',
            )
        )
    mkdocs_yml = root / package / "mkdocs.yml"
    if mkdocs_yml.is_file() and "changelog.md" not in nav_pages(
        read_mkdocs(mkdocs_yml).get("nav")
    ):
        findings.append(
            error(
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


def project_urls(pyproject: Path) -> dict[str, object]:
    """The raw `[project.urls]` table of *pyproject*, or an empty one."""
    return _table(_toml(pyproject), "project", "urls")


def _check_urls(root: Path, package: str) -> list[Finding]:
    path = root / package / "pyproject.toml"
    urls = project_urls(path)
    return [
        error("package-urls", path, f"[project.urls] {key} must be an https:// URL")
        for key in URL_KEYS
        if not (isinstance(url := urls.get(key), str) and url.startswith("https://"))
    ]


def _check_readme(root: Path, package: str) -> list[Finding]:
    path = root / package / "README.md"
    if not path.is_file():
        return []
    return [
        error("package-readme-relative-link", path, f"{link} is a relative link")
        for link in parsed.local_links(path.read_text(encoding="utf-8"))
    ]


def _check_package(root: Path, package: str) -> list[Finding]:
    base = root / package
    docs = base / "docs"
    findings: list[Finding] = []
    if not (base / "mkdocs.yml").is_file():
        findings.append(error("package-missing-mkdocs", base, "no mkdocs.yml"))
    if not (docs / "index.md").is_file():
        findings.append(error("package-missing-index", docs, "no docs/index.md"))
    guides = docs / "guides"
    if not guides.is_dir():
        findings.append(error("package-missing-guides", guides, "no docs/guides/"))
    else:
        findings.extend(
            error("kebab-case", page, "not kebab-case")
            for page in sorted(guides.rglob("*.md"))
            if not page.name.startswith("_") and not KEBAB_NAME.match(page.name)
        )
    findings.extend(
        error(
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
    if config.is_workspace:
        findings = [
            f for package in config.packages for f in _check_package(root, package)
        ]
        findings.extend(
            error(
                "package-unlisted",
                root / member,
                f"{member} is a workspace member not listed in config.packages",
            )
            for member in members
            if member not in config.packages
        )
        return findings
    return [
        error(
            "package-docs-not-allowed",
            root / member,
            "package docs sites are python-lib only (kiln ADR-0008); "
            f"document {member} in the root site",
        )
        for member in dict.fromkeys([*members, *config.packages])
        if (root / member / "docs").is_dir() or (root / member / "mkdocs.yml").is_file()
    ]
