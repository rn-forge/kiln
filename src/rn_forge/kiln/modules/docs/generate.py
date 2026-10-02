"""Derived regions: the parts of a docs repo that kiln rewrites from its inputs."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.blocks import ManagedBlock

from rn_forge.kiln.modules.docs.nav import update_nav
from rn_forge.kiln.modules.docs.work import (
    BOARD_BLOCK,
    SCOPE_BLOCK,
    load_work,
    render_board,
    render_scope,
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

    def region(path: Path, block: ManagedBlock, body: str, code: str) -> None:
        current = path.read_text(encoding="utf-8")
        updated = block.render(current, body)
        if updated != current:
            writes[path] = updated
            stale_findings.append(
                _error(
                    code,
                    f"the derived {block.name.removeprefix('derived ')} is stale {_RERUN}",
                    path.relative_to(root).as_posix(),
                )
            )

    region(index, BOARD_BLOCK, render_board(work), "docs.board-stale")
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
    return writes, [*markers, *validate(work, root)], stale_findings


def generate(root: Path) -> tuple[list[Path], list[Finding]]:
    """Rewrite every stale derived region under *root*.

    Returns the files written, and the findings that remain after writing: the
    work-model metadata findings and any fence-marker findings.
    """
    written: list[Path] = []
    mkdocs = root / "mkdocs.yml"
    if mkdocs.exists():
        updated, changed = update_nav(mkdocs, root / "docs")
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


def stale(root: Path) -> list[Finding]:
    """A finding for each derived region under *root* that regenerating would change."""
    findings: list[Finding] = []
    mkdocs = root / "mkdocs.yml"
    if mkdocs.exists() and update_nav(mkdocs, root / "docs")[1]:
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
