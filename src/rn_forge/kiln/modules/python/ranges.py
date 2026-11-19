"""Plan, write and describe upgrades to rn-forge requirements."""

from __future__ import annotations

import re
import urllib.request
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.lang.collections import DictUtils

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.python.checks.rn_forge_deps import (
    distribution,
    governed,
    workspace_members,
)

__all__ = ["Move", "plan", "release_notes", "write"]

_NAME_AND_EXTRAS = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\s*(\[[^\]]*\]))?")
_RELEASE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]")


@dataclass(frozen=True)
class Move:
    """A requirement that moves to the version range in the pin table."""

    path: str
    distribution: str
    old: str
    new: str
    old_floor: str | None
    breaking: bool


def _arrays(document: Mapping[str, object]) -> Iterator[list[object]]:
    for value in (
        DictUtils.get(document, "project.dependencies"),
        *DictUtils.get_mapping(document, "project.optional-dependencies").values(),
        *DictUtils.get_mapping(document, "dependency-groups").values(),
    ):
        if isinstance(value, list):
            yield cast("list[object]", value)


def _move(relative: Path, entry: str, members: frozenset[str]) -> Move | None:
    name = distribution(entry)
    if not governed(name) or name not in archetypes.RN_FORGE_TAGS or name in members:
        return None

    version = archetypes.RN_FORGE_TAGS[name].rpartition("-v")[2]
    old_floor = archetypes.floor(entry)
    if old_floor is not None and archetypes.version_key(
        old_floor
    ) >= archetypes.version_key(version):
        return None

    requirement, _, marker = entry.partition(";")
    prefix = _NAME_AND_EXTRAS.match(requirement)
    assert prefix is not None
    specifier = requirement[prefix.end() :].strip().strip("()")
    ceiling = archetypes.ceiling(version)
    breaking = specifier.startswith("@") or f"<{ceiling}" not in [
        "".join(clause.split()) for clause in specifier.split(",")
    ]
    written_name, extras = prefix.groups()
    new = f"{written_name}{extras or ''}>={version},<{ceiling}"
    if marker.strip():
        new += f"; {marker.strip()}"
    return Move(relative.as_posix(), name, entry, new, old_floor, breaking)


def plan(config: KilnConfig, root: Path) -> list[Move]:
    """Find all requirements below kiln's pin table in the repository."""
    members = workspace_members(config, root)
    moves: list[Move] = []
    for relative in archetypes.pyproject_paths(config):
        path = root / relative
        if path.exists():
            for entries in _arrays(DocumentUtils.read(path)):
                for entry in entries:
                    if isinstance(entry, str) and (
                        move := _move(relative, entry, members)
                    ):
                        moves.append(move)
    return moves


def write(root: Path, moves: list[Move]) -> None:
    """Replace the planned requirements in place, preserving TOML layout."""
    by_path: dict[str, dict[str, str]] = {}
    for move in moves:
        by_path.setdefault(move.path, {})[move.old] = move.new

    for relative, replacements in by_path.items():
        path = root / relative
        document = DocumentUtils.read_document(path)
        for entries in _arrays(document):
            for index, entry in enumerate(entries):
                if isinstance(entry, str) and entry in replacements:
                    entries[index] = replacements[entry]
        DocumentUtils.write_document(path, document)


def _fetch(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode("utf-8")
    except OSError:
        return None


def release_notes(move: Move) -> str:
    """Return the changelog sections for a move, or the URL if unavailable."""
    name = move.distribution
    tag = archetypes.RN_FORGE_TAGS[name]
    url = f"https://raw.githubusercontent.com/rn-forge/pykit/{tag}/packages/{name}/CHANGELOG.md"
    changelog = _fetch(url)
    if changelog is None:
        return f"release notes: {url}"

    old = archetypes.version_key(move.old_floor) if move.old_floor is not None else ()
    new = archetypes.version_key(tag.rpartition("-v")[2])
    sections: list[str] = []
    for section in re.split(r"(?m)(?=^## )", changelog):
        heading = _RELEASE.match(section)
        if heading and old < archetypes.version_key(heading.group(1)) <= new:
            sections.append(section.rstrip())
    return "\n\n".join(sections)
