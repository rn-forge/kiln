"""Derived regions: the parts of a docs repo that kiln rewrites from its inputs."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.blocks import ManagedBlock

from rn_forge.kiln.modules.docs.nav import update_nav
from rn_forge.kiln.modules.docs.work import (
    BOARD_BLOCK,
    EPICS_BLOCK,
    FEATURES_BLOCK,
    SCOPE_BLOCK,
    STORIES_BLOCK,
    Page,
    load_work,
    metadata_end,
    render_board,
    render_epics,
    render_features,
    render_scope,
    render_stories,
    validate,
)

__all__ = ["generate", "stale"]

_RERUN = "— run `task docs:generate`"


def _error(code: str, message: str, path: str) -> Finding:
    return Finding(code, Severity.ERROR, message, path=path)


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
        return (
            {},
            [
                _error(
                    "docs.board-markers",
                    "has an incomplete derived board fence",
                    index.relative_to(root).as_posix(),
                )
            ],
            [],
        )

    work = load_work(docs)
    writes: dict[Path, str] = {}
    markers: list[Finding] = []
    stale_findings: list[Finding] = []

    def region(
        path: Path,
        block: ManagedBlock,
        body: str,
        code: str,
        current: str | None = None,
    ) -> None:
        on_disk = path.read_text(encoding="utf-8")
        updated = block.render(on_disk if current is None else current, body)
        if updated != on_disk:
            writes[path] = updated
            stale_findings.append(
                _error(
                    code,
                    f"the derived {block.name.removeprefix('derived ')} is stale {_RERUN}",
                    path.relative_to(root).as_posix(),
                )
            )

    def summary(page: Page, block: ManagedBlock, body: str, name: str) -> None:
        path = page.path
        fenced = _with_fence(path.read_text(encoding="utf-8"), block)
        if fenced is None:
            if page.meta:
                markers.append(
                    _error(
                        f"docs.{name}-markers",
                        f"has an incomplete derived {name} fence",
                        path.relative_to(root).as_posix(),
                    )
                )
            return
        region(path, block, body, f"docs.{name}-stale", fenced)

    region(index, BOARD_BLOCK, render_board(work), "docs.board-stale")
    epics = docs / "specs" / "epics" / "index.md"
    if epics.exists():
        if not _fenced(EPICS_BLOCK, epics.read_text(encoding="utf-8")):
            markers.append(
                _error(
                    "docs.epics-markers",
                    "has no complete derived epics fence",
                    epics.relative_to(root).as_posix(),
                )
            )
        else:
            region(epics, EPICS_BLOCK, render_epics(work), "docs.epics-stale")
    for release in work.releases:
        path = release.page.path
        if not _fenced(SCOPE_BLOCK, path.read_text(encoding="utf-8")):
            markers.append(
                _error(
                    "docs.scope-markers",
                    "has no complete derived scope fence",
                    path.relative_to(root).as_posix(),
                )
            )
            continue
        region(path, SCOPE_BLOCK, render_scope(work, release), "docs.scope-stale")
    for epic in work.epics:
        if any(f.epic_dir == epic.dir for f in work.features):
            summary(epic.page, FEATURES_BLOCK, render_features(work, epic), "features")
    for feature in work.features:
        summary(feature.page, STORIES_BLOCK, render_stories(feature), "stories")
    return writes, [*markers, *validate(work, root)], stale_findings


def generate(
    root: Path, packages: Sequence[str] = ()
) -> tuple[list[Path], list[Finding]]:
    """Rewrite every stale derived region under *root*.

    Returns the files written, and the findings that remain after writing: the
    work-model metadata findings and any fence-marker findings.
    """
    written: list[Path] = []
    mkdocs = root / "mkdocs.yml"
    if mkdocs.exists():
        updated, changed = update_nav(mkdocs, root / "docs", packages)
        if changed:
            mkdocs.write_text(updated, encoding="utf-8")
            written.append(mkdocs)
    regions = _work_regions(root)
    if regions is None:
        return written, []
    writes, remaining, _ = regions
    for path, text in writes.items():
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written, remaining


def stale(root: Path, packages: Sequence[str] = ()) -> list[Finding]:
    """A finding for each derived region under *root* that regenerating would change."""
    findings: list[Finding] = []
    mkdocs = root / "mkdocs.yml"
    if mkdocs.exists() and update_nav(mkdocs, root / "docs", packages)[1]:
        findings.append(
            _error(
                "docs.nav-stale",
                f"the derived nav is stale {_RERUN}",
                "mkdocs.yml",
            )
        )
    regions = _work_regions(root)
    if regions is None:
        return findings
    _, remaining, stale_findings = regions
    return [*findings, *stale_findings, *remaining]
