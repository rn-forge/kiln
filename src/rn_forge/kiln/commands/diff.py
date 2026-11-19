"""`kiln diff`: unified diff of on-disk content against a fresh render."""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from pathlib import Path

from rn_forge.commons import generation
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import console

from rn_forge.kiln.commands import output
from rn_forge.kiln.modules.core import cycle, umbrella
from rn_forge.kiln.modules.core.inventory import KINDS, inventory

__all__ = ["diff"]


def diff(
    artifact: str | None = None, old: str | None = None, json: bool = False
) -> None:
    """Unified diff of on-disk content against a fresh render, writing nothing.

    With no `--artifact`, every managed and block artifact whose disk content
    differs from its fresh render is diffed; `--artifact` (a key or a path)
    limits it to one.

    `--old` is another repository's checkout: instead of diffing the artifacts,
    list every file of this (reference) repository and of that one with its
    class and whether the bytes match; exits 0.

    Raises:
        AppException: ARTIFACT names no known artifact, a difference was
            found — `diff(1)`'s own exit-1 convention — or `--old` is not a git
            repository or is given with `--artifact`.
    """
    output.use_json(json)
    if old is not None:
        if artifact is not None:
            raise AppException(
                "inventory.artifact-with-old: --artifact and --old exclude each other"
            )
        _diff_inventory(old)
        return
    _diff_artifacts(artifact)


def _diff_inventory(old: str) -> None:
    rows = inventory(umbrella.find_root(Path.cwd()), Path(old))

    def inventory_text() -> None:
        for row in rows:
            console.print(f"{row.kind:<11} {row.status:<15} {row.path}", markup=False)
        console.print(
            ", ".join(f"{sum(r.kind == kind for r in rows)} {kind}" for kind in KINDS),
            markup=False,
        )

    output.emit(
        {"inventory": [dataclasses.asdict(row) for row in rows]}, inventory_text
    )


def _diff_artifacts(artifact: str | None) -> None:
    root = umbrella.find_root(Path.cwd())
    changes = cycle.prepare(root).plan.changes

    if artifact is not None:
        changes = [c for c in changes if artifact in (c.key, c.path)]
        if not changes:
            raise AppException("{} is not a known artifact", artifact)

    diffs = _diffs(root, changes)

    def diff_text() -> None:
        for _, text in diffs:
            console.print(text, markup=False)

    output.emit(
        {"diffs": [{"path": path, "diff": text} for path, text in diffs]}, diff_text
    )

    if diffs:
        raise AppException("{} artifact(s) differ from disk", len(diffs))


def _diffs(root: Path, changes: Sequence[generation.Change]) -> list[tuple[str, str]]:
    """`(path, unified diff)` for every managed/block change that differs from disk."""
    results: list[tuple[str, str]] = []
    for change in changes:
        artifact = change.artifact
        if artifact is None or artifact.kind is generation.ArtifactKind.SEEDED:
            continue
        text = generation.diff(root, change)
        if text:
            results.append((artifact.path, text))
    return results
