"""The engine adapter for files with derived regions (see :mod:`~rn_forge.kiln.modules.core.derived`)."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.generation import (
    Action,
    Artifact,
    ArtifactKind,
    Change,
    Plan,
    StateEntry,
)

from rn_forge.kiln.modules.core.derived import DERIVED, managed_digest

__all__ = ["DerivedArtifact", "settle"]


@dataclasses.dataclass(frozen=True, slots=True)
class DerivedArtifact(Artifact):
    """A managed artifact whose recorded hash ignores its derived regions."""

    @property
    def content_hash(self) -> str:
        """`managed_digest` of the content."""
        return managed_digest(self.path, self.content)


def settle(root: Path, planned: Plan, entries: Mapping[str, StateEntry]) -> Plan:
    """*planned* with each derived file re-classified by its normalised hash.

    A rendered file is `unchanged` when its derived regions are the only
    difference from the recorded state and the disk equals the render,
    `update` when they differ from the render, and `drift` on any other edit
    or malformed markers. A stale entry is `delete` when clean, else `drift`
    with the deletion as its intent. `create`, `conflict`, `missing` and
    `forget` stand as the engine classified them.
    """
    return Plan(tuple(_settled(root, change, entries) for change in planned.changes))


def _settled(root: Path, change: Change, entries: Mapping[str, StateEntry]) -> Change:
    entry = entries.get(change.key)
    path = root / change.path
    if (
        change.kind is not ArtifactKind.MANAGED
        or change.path not in DERIVED
        or entry is None
        or not path.is_file()
    ):
        return change
    with path.open(encoding="utf-8", newline="") as handle:
        disk = handle.read()
    try:
        clean = managed_digest(change.path, disk) == entry.content_hash
    except AppException:
        clean = False
    artifact = change.artifact
    if artifact is None:
        return dataclasses.replace(
            change,
            action=Action.DELETE if clean else Action.DRIFT,
            intent=Action.DELETE,
        )
    if not clean:
        return dataclasses.replace(change, action=Action.DRIFT)
    return dataclasses.replace(
        change,
        action=Action.UNCHANGED if disk == artifact.content else Action.UPDATE,
    )
