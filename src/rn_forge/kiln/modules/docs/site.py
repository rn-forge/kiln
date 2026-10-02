"""Validate documentation links, anchors, navigation targets, and reachability."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import YamlUtils

from rn_forge.kiln.modules.docs.markdown import headings, is_external, links
from rn_forge.kiln.modules.docs.packages import (
    package_mounts,
    read_mkdocs,
    resolve_link,
)

__all__ = ["Site", "check_site"]


def _error(code: str, path: Path | str, message: str) -> Finding:
    return Finding(
        code=f"docs.{code}", severity=Severity.ERROR, message=message, path=str(path)
    )


class Site:
    """A repository's docs tree, read the way MkDocs will read it."""

    def __init__(
        self,
        root: str | Path,
        *,
        docs_dir: str = "docs",
        packages: Sequence[str] = (),
        package: str | None = None,
    ) -> None:
        """Initialize :class:`Site`.

        Args:
            root: The repository root.
            docs_dir: The docs directory's name, relative to *root*.
            packages: Package site directories, relative to *root*, whose docs
                root links may name by ``site_name``.
            package: Set when this site is itself a package's: the package's
                path in the repository. A link out of its docs directory is
                then an error.
        """
        self.root = Path(root).resolve()
        self.docs_dir = self.root / docs_dir
        self.mounts = package_mounts(self.root, packages)
        self.package = package
        self.mkdocs_yml = self.root / "mkdocs.yml"
        self.generated = self._generated_prefixes()

    def _generated_prefixes(self) -> list[Path]:
        """Directories under docs/ that are gitignored — generator output, not prose."""
        gitignore = self.root / ".gitignore"
        if not gitignore.is_file():
            return []
        prefixes: list[Path] = []
        for raw in gitignore.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            candidate = (self.root / line.rstrip("/")).resolve()
            if candidate == self.docs_dir or self.docs_dir in candidate.parents:
                prefixes.append(candidate)
        return prefixes

    def is_generated(self, path: Path) -> bool:
        """Whether *path* is inside a gitignored, generated subtree."""
        return any(path == p or p in path.parents for p in self.generated)

    def markdown_files(self) -> list[Path]:
        """Every page that ships: not generated, not an underscore-prefixed include."""
        return sorted(
            path
            for path in self.docs_dir.rglob("*.md")
            if not self.is_generated(path) and not path.name.startswith("_")
        )

    def nav_paths(self) -> list[str]:
        """Every ``.md`` path named by `mkdocs.yml`'s nav, in nav order."""
        config: Any = YamlUtils.read_file(self.mkdocs_yml)
        paths: list[str] = []

        def walk(node: Any) -> None:
            if isinstance(node, str):
                if node.endswith(".md"):
                    paths.append(node)
            elif isinstance(node, dict):
                for value in node.values():  # pyright: ignore[reportUnknownVariableType]
                    walk(value)
            elif isinstance(node, list):
                for item in node:  # pyright: ignore[reportUnknownVariableType]
                    walk(item)

        document = cast(dict[str, Any], config) if isinstance(config, dict) else {}
        walk(document.get("nav", []))
        return paths

    def anchors_in(self, path: Path) -> set[str]:
        """Every heading anchor in *path*, or an empty set if it does not exist."""
        if not path.exists():
            return set()
        return headings(path.read_text(encoding="utf-8"))

    def linked_pages(self, path: Path) -> set[Path]:
        """Every existing Markdown page *path* links to."""
        targets: set[Path] = set()
        for link in links(path.read_text(encoding="utf-8")):
            if is_external(link):
                continue
            target, _, _anchor = link.partition("#")
            if not target.endswith(".md"):
                continue
            resolved = resolve_link(path, target, self.docs_dir, self.mounts)
            if resolved.exists():
                targets.add(resolved)
        return targets

    def check_nav_targets_exist(self) -> list[Finding]:
        """Every page the nav names exists."""
        return [
            _error(
                "nav-missing-page",
                self.mkdocs_yml,
                f"mkdocs.yml nav references missing page: {nav_path!r}",
            )
            for nav_path in self.nav_paths()
            if not (target := (self.docs_dir / nav_path).resolve()).exists()
            and not self.is_generated(target)
        ]

    def check_orphans(self) -> list[Finding]:
        """A page is reachable if the nav names it, or a reachable page links to it."""
        frontier = [
            resolved
            for nav_path in self.nav_paths()
            if (resolved := (self.docs_dir / nav_path).resolve()).exists()
        ]
        reachable = set(frontier)
        while frontier:
            for linked in self.linked_pages(frontier.pop()):
                if linked not in reachable:
                    reachable.add(linked)
                    frontier.append(linked)

        return [
            _error(
                "orphan-page",
                path,
                f"not reachable from mkdocs.yml nav: {path.relative_to(self.root)}",
            )
            for path in self.markdown_files()
            if path.resolve() not in reachable
        ]

    def _within_docs(self, path: Path) -> bool:
        return path == self.docs_dir or self.docs_dir in path.parents

    def check_links(self) -> list[Finding]:
        """Every relative link and anchor in a shipping page resolves."""
        findings: list[Finding] = []
        for path in self.markdown_files():
            for link in links(path.read_text(encoding="utf-8")):
                if is_external(link):
                    continue
                target, _, anchor = link.partition("#")
                resolved = (
                    path
                    if not target
                    else resolve_link(path, target, self.docs_dir, self.mounts)
                )
                if self.package is not None and not self._within_docs(resolved):
                    findings.append(
                        _error(
                            "package-link-escapes",
                            path,
                            f"links outside {self.package}/"
                            f"{self.docs_dir.relative_to(self.root)}: {link}",
                        )
                    )
                    continue
                if resolved.suffix and resolved.suffix != ".md":
                    continue  # a non-Markdown asset is not this check's job
                if not resolved.exists():
                    if not self.is_generated(resolved):
                        findings.append(
                            _error("broken-link", path, f"broken link to {link!r}")
                        )
                    continue
                if (
                    anchor
                    and not self.is_generated(resolved)
                    and anchor not in self.anchors_in(resolved)
                ):
                    findings.append(
                        _error("broken-anchor", path, f"broken anchor in {link!r}")
                    )
        return findings

    def check(self) -> list[Finding]:
        """Run every site check, in reporting order."""
        return [
            *self.check_nav_targets_exist(),
            *self.check_orphans(),
            *self.check_links(),
        ]


def check_site(
    root: str | Path, *, docs_dir: str = "docs", packages: Sequence[str] = ()
) -> list[Finding]:
    """Run every site check against the repository at *root*, then each package's."""
    root = Path(root).resolve()
    findings = Site(root, docs_dir=docs_dir, packages=packages).check()
    for package in packages:
        mkdocs_yml = root / package / "mkdocs.yml"
        if not mkdocs_yml.is_file():
            continue
        site = Site(
            root / package,
            docs_dir=str(read_mkdocs(mkdocs_yml).get("docs_dir", "docs")),
            package=package,
        )
        findings.extend(site.check())
    return findings
