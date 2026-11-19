"""Derived regions: the parts of a docs repo that kiln rewrites from its inputs."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding
from rn_forge.commons.fs.blocks import HTML_COMMENT, ManagedBlock

from rn_forge.kiln.modules.docs.findings import error
from rn_forge.kiln.modules.docs.nav import update_nav
from rn_forge.kiln.modules.docs.policy import POLICY
from rn_forge.kiln.modules.docs.work import (
    BOARD_BLOCK,
    EPICS_BLOCK,
    FEATURES_BLOCK,
    SCOPE_BLOCK,
    STORIES_BLOCK,
    Page,
    Work,
    load_work,
    metadata_end,
    render_board,
    render_epics,
    render_features,
    render_scope,
    render_stories,
    validate,
)

if TYPE_CHECKING:
    from rn_forge.kiln.config import KilnConfig

__all__ = ["finalizer", "generate", "stale"]

_RERUN = "— run `task docs:generate`"

CI_MATRIX_BLOCK = ManagedBlock("derived ci-matrix", comment=HTML_COMMENT)
"""The checks matrix in `docs/architecture/ci.md`, filled from the check registry."""

_CI_PAGE = Path("docs") / "architecture" / "ci.md"

_Row = tuple[Path, ManagedBlock, Callable[[], str], str, Page | None]


def _fenced(block: ManagedBlock, text: str) -> bool:
    """Whether *text* holds one complete, well-ordered fence for *block*."""
    try:
        return block.extract(text) is not None
    except AppException:
        return False


def _with_fence(text: str, block: ManagedBlock) -> str | None:
    """*text* with an empty *block* fence after its metadata table.

    Returns *text* unchanged when it already holds both markers, and `None` when
    it holds exactly one, or has no metadata table.
    """
    try:
        if block.extract(text) is not None:
            return text
    except AppException:
        return None
    lines = text.splitlines()
    end = metadata_end(lines)
    if end is None:
        return None
    head = "\n".join(lines[:end])
    tail = "\n".join(lines[end:]).lstrip("\n")
    if tail and text.endswith("\n"):
        tail += "\n"
    return f"{head}\n\n{block.render('', '')}" + (f"\n{tail}" if tail else "")


def _ci_matrix(root: Path, matrix: str | None) -> tuple[dict[Path, str], list[Finding]]:
    """The new text of the CI page and its stale finding, when it carries the fence."""
    if matrix is None:
        return {}, []
    path = root / _CI_PAGE
    if not path.exists():
        return {}, []
    on_disk = path.read_text(encoding="utf-8")
    if not _fenced(CI_MATRIX_BLOCK, on_disk):
        return {}, []
    updated = CI_MATRIX_BLOCK.render(on_disk, f"\n{matrix}\n\n")
    if updated == on_disk:
        return {}, []
    return {path: updated}, [
        error(
            "ci-matrix-stale",
            _CI_PAGE.as_posix(),
            f"the derived ci-matrix is stale {_RERUN}",
        )
    ]


@dataclass(frozen=True)
class Region:
    """One derived region of one page: its new text, and what it reports."""

    path: Path
    text: str | None
    stale: Finding | None = None
    markers: Finding | None = None


def _region(
    root: Path,
    path: Path,
    block: ManagedBlock,
    body: str,
    name: str,
    current: str | None = None,
) -> Region:
    on_disk = path.read_text(encoding="utf-8")
    updated = block.render(on_disk if current is None else current, body)
    if updated == on_disk:
        return Region(path, None)
    return Region(
        path,
        updated,
        stale=error(
            f"{name}-stale",
            path.relative_to(root).as_posix(),
            f"the derived {block.name.removeprefix('derived ')} is stale {_RERUN}",
        ),
    )


def _page_region(
    root: Path,
    path: Path,
    block: ManagedBlock,
    render: Callable[[], str],
    name: str,
    page: Page | None,
) -> Region:
    """The region of *path*; a *page* means a missing fence is added, not reported."""
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(root).as_posix()
    if page is None:
        if not _fenced(block, text):
            return Region(
                path,
                None,
                markers=error(
                    f"{name}-markers", rel, f"has no complete derived {name} fence"
                ),
            )
        return _region(root, path, block, render(), name)
    fenced = _with_fence(text, block)
    if fenced is None:
        marker = (
            error(f"{name}-markers", rel, f"has an incomplete derived {name} fence")
            if page.meta
            else None
        )
        return Region(path, None, markers=marker)
    return _region(root, path, block, render(), name, fenced)


def _rows(work: Work, docs: Path, index: Path) -> list[_Row]:
    """The derived regions of the work pages, in the order they are reported."""
    epics = docs / POLICY.nested[0].path / "index.md"
    rows: list[_Row] = [(index, BOARD_BLOCK, lambda: render_board(work), "board", None)]
    if epics.exists():
        rows.append((epics, EPICS_BLOCK, lambda: render_epics(work), "epics", None))
    rows += [
        (
            release.page.path,
            SCOPE_BLOCK,
            lambda release=release: render_scope(work, release),
            "scope",
            None,
        )
        for release in work.releases
    ]
    rows += [
        (
            epic.page.path,
            FEATURES_BLOCK,
            lambda epic=epic: render_features(work, epic),
            "features",
            epic.page,
        )
        for epic in work.epics
        if any(f.epic_dir == epic.dir for f in work.features)
    ]
    rows += [
        (
            feature.page.path,
            STORIES_BLOCK,
            lambda feature=feature: render_stories(feature),
            "stories",
            feature.page,
        )
        for feature in work.features
    ]
    return rows


def _work_regions(
    root: Path,
) -> tuple[dict[Path, str], list[Finding], list[Finding]] | None:
    """The new text of each stale page, the findings that remain, and the stale ones.

    Returns `None` when `docs/specs/index.md` carries no board fence. The
    remaining findings are fence-marker and metadata findings; writing the new
    text fixes the stale ones.
    """
    docs = root / "docs"
    index = docs / "specs" / "index.md"
    if not index.exists():
        return None
    text = index.read_text(encoding="utf-8")
    if BOARD_BLOCK.begin not in text and BOARD_BLOCK.end not in text:
        return None
    if not _fenced(BOARD_BLOCK, text):
        marker = error(
            "board-markers",
            index.relative_to(root).as_posix(),
            "has an incomplete derived board fence",
        )
        return {}, [marker], []

    work = load_work(docs)
    rows = _rows(work, docs, index)
    regions = [_page_region(root, *row) for row in rows]
    writes = {r.path: r.text for r in regions if r.text is not None}
    markers = [r.markers for r in regions if r.markers is not None]
    stale_findings = [r.stale for r in regions if r.stale is not None]
    return writes, [*markers, *validate(work, root)], stale_findings


def generate(
    root: Path, packages: Sequence[str] = (), *, ci_matrix: str | None = None
) -> tuple[list[Path], list[Finding]]:
    """Rewrite every stale derived region under *root*.

    Returns the files written, and the findings that remain after writing: the
    work-model metadata findings and any fence-marker findings. A `None`
    *ci_matrix* leaves the CI page's matrix region alone.
    """
    written: list[Path] = []
    mkdocs = root / "mkdocs.yml"
    if mkdocs.exists():
        updated, changed = update_nav(mkdocs, root / "docs", packages)
        if changed:
            mkdocs.write_text(updated, encoding="utf-8")
            written.append(mkdocs)
    matrix, _ = _ci_matrix(root, ci_matrix)
    for path, text in matrix.items():
        path.write_text(text, encoding="utf-8")
        written.append(path)
    regions = _work_regions(root)
    if regions is None:
        return written, []
    writes, remaining, _ = regions
    for path, text in writes.items():
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written, remaining


def stale(
    root: Path, packages: Sequence[str] = (), *, ci_matrix: str | None = None
) -> list[Finding]:
    """A finding for each derived region under *root* that regenerating would change.

    A `None` *ci_matrix* skips the CI page's matrix region.
    """
    findings: list[Finding] = []
    mkdocs = root / "mkdocs.yml"
    if mkdocs.exists() and update_nav(mkdocs, root / "docs", packages)[1]:
        findings.append(
            error("nav-stale", "mkdocs.yml", f"the derived nav is stale {_RERUN}")
        )
    findings.extend(_ci_matrix(root, ci_matrix)[1])
    regions = _work_regions(root)
    if regions is None:
        return findings
    _, remaining, stale_findings = regions
    return [*findings, *stale_findings, *remaining]


def finalizer(root: Path, config: KilnConfig) -> Callable[[], None] | None:
    """A callback that regenerates *root*'s derived docs regions, or `None` without MkDocs."""
    if config.docs_profile != "mkdocs":
        return None

    def finalize() -> None:
        generate(
            root,
            config.docs_packages,
            ci_matrix=config.ci_matrix(every_archetype=True),
        )

    return finalize
