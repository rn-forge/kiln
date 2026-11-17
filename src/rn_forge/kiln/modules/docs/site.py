"""Validate documentation links, anchors, navigation targets, and reachability."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rn_forge.commons.findings import Finding
from rn_forge.commons.text.markdown import MarkdownUtils

from rn_forge.kiln.modules.docs import parsed
from rn_forge.kiln.modules.docs.findings import error
from rn_forge.kiln.modules.docs.mkdocs import (
    excluded_docs,
    package_mounts,
    read_mkdocs,
    resolve_link,
)
from rn_forge.kiln.modules.docs.pages import nav_pages

__all__ = ["Site", "check_site"]


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
        self.excluded = excluded_docs(self.mkdocs_yml)

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

    def is_excluded(self, path: Path) -> bool:
        """Whether *path* is a page under docs_dir that ``exclude_docs`` drops."""
        try:
            relative = path.relative_to(self.docs_dir)
        except ValueError:
            return False
        return self.excluded.match_file(relative.as_posix())

    def markdown_files(self) -> list[Path]:
        """Every page that ships: not generated, not excluded, not an underscore include."""
        return sorted(
            path
            for path in self.docs_dir.rglob("*.md")
            if not self.is_generated(path)
            and not path.name.startswith("_")
            and not self.is_excluded(path)
        )

    def nav_paths(self) -> list[str]:
        """Every ``.md`` path named by `mkdocs.yml`'s nav, in nav order."""
        return [
            page
            for page in nav_pages(read_mkdocs(self.mkdocs_yml).get("nav", []))
            if page.endswith(".md")
        ]

    def anchors_in(self, path: Path) -> set[str]:
        """Every heading anchor in *path*, or an empty set if it does not exist."""
        if not path.exists():
            return set()
        return set(parsed.anchors(path.read_text(encoding="utf-8")))

    def linked_pages(self, path: Path) -> set[Path]:
        """Every existing Markdown page *path* links to."""
        targets: set[Path] = set()
        for link in parsed.local_links(path.read_text(encoding="utf-8")):
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
            error(
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
            error(
                "orphan-page",
                path,
                f"not reachable from mkdocs.yml nav: {path.relative_to(self.root)}",
            )
            for path in self.markdown_files()
            if path.resolve() not in reachable
        ]

    def _within_docs(self, path: Path) -> bool:
        return path == self.docs_dir or self.docs_dir in path.parents

    def _escape_finding(self, path: Path, link: str, resolved: Path) -> Finding | None:
        """The finding for a link out of its docs tree, or `None` when it stays in."""
        if self._within_docs(resolved):
            return None
        if self.package is not None:
            return error(
                "package-link-escapes",
                path,
                f"links outside {self.package}/"
                f"{self.docs_dir.relative_to(self.root)}: {link}",
            )
        if any(
            mount == resolved or mount in resolved.parents
            for mount in self.mounts.values()
        ):
            return None
        return error(
            "link-leaves-docs",
            path,
            f"links outside {self.docs_dir.name}/: {link}; use an absolute URL",
        )

    def _link_finding(self, path: Path, link: str) -> Finding | None:
        """The first problem with *link* in *path*, or `None`."""
        target, _, anchor = link.partition("#")
        resolved = (
            path
            if not target
            else resolve_link(path, target, self.docs_dir, self.mounts)
        )
        escape = self._escape_finding(path, link, resolved)
        if escape is not None:
            return escape
        if resolved.suffix and resolved.suffix != ".md":
            return None  # a non-Markdown asset is not this check's job
        if resolved.suffix == ".md" and self.is_excluded(resolved):
            return error(
                "broken-link", path, f"links to a page excluded from the site: {link}"
            )
        if not resolved.exists():
            if self.is_generated(resolved):
                return None
            return error("broken-link", path, f"broken link to {link!r}")
        if (
            anchor
            and not self.is_generated(resolved)
            and anchor not in self.anchors_in(resolved)
        ):
            return error("broken-anchor", path, f"broken anchor in {link!r}")
        return None

    def check_links(self) -> list[Finding]:
        """Every relative link and anchor in a shipping page resolves."""
        findings: list[Finding] = []
        for path in self.markdown_files():
            for link in parsed.links(path.read_text(encoding="utf-8")):
                if MarkdownUtils.is_external(link):
                    continue
                finding = self._link_finding(path, link)
                if finding is not None:
                    findings.append(finding)
        return findings

    def check(self) -> list[Finding]:
        """Run every site check, in reporting order."""
        if not self.mkdocs_yml.is_file():
            return [error("missing-config", self.mkdocs_yml, "mkdocs.yml is missing")]
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
