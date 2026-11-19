"""Plan and apply changes to rn-forge requirements."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from rn_forge.commons.fs.documents import DocumentUtils

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.python import ranges

COMMONS = "rn-forge-commons"
OLD = "rn-forge-commons>=0.9.0,<0.10"
NEW = archetypes.requirement(COMMONS)


@pytest.fixture
def root(rendered_copy: Callable[..., Path]) -> Path:
    return rendered_copy("python-tool")


def _dependencies(root: Path, *entries: str) -> None:
    path = root / "pyproject.toml"
    document = DocumentUtils.read_document(path)
    document["project"]["dependencies"] = list(entries)
    DocumentUtils.write_document(path, document)


def test_an_old_range_moves_to_the_pin_table(root: Path) -> None:
    _dependencies(root, OLD)

    (move,) = ranges.plan(KilnConfig.load(root), root)

    assert move == ranges.Move("pyproject.toml", COMMONS, OLD, NEW, "0.9.0", True)


def test_a_move_keeps_extras_and_marker(root: Path) -> None:
    _dependencies(
        root, 'rn-forge-commons[pydantic]>=0.9.0,<0.10; python_version >= "3.12"'
    )

    (move,) = ranges.plan(KilnConfig.load(root), root)

    assert move.new == (
        'rn-forge-commons[pydantic]>=0.10.0,<0.11; python_version >= "3.12"'
    )


def test_a_git_pin_becomes_a_range(root: Path) -> None:
    _dependencies(
        root,
        "rn-forge-cli @ git+https://github.com/rn-forge/pykit@rn-forge-cli-v0.1.3"
        "#subdirectory=packages/rn-forge-cli",
    )

    (move,) = ranges.plan(KilnConfig.load(root), root)

    assert move.new == "rn-forge-cli>=0.2.0,<0.3"
    assert move.old_floor == "0.1.3"
    assert move.breaking


def test_a_floor_at_or_above_the_table_is_left_alone(root: Path) -> None:
    _dependencies(root, NEW, NEW.replace("0.10.0", "0.10.1"))

    assert ranges.plan(KilnConfig.load(root), root) == []


def test_non_rn_forge_and_workspace_members_are_left_alone(
    rendered_copy: Callable[..., Path],
) -> None:
    root = rendered_copy("python-lib")
    path = root / "packages/lib-alpha/pyproject.toml"
    document = DocumentUtils.read_document(path)
    document["project"]["name"] = COMMONS
    document["project"]["dependencies"] = []
    DocumentUtils.write_document(path, document)
    _dependencies(root / "packages/lib-beta", "httpx>=0.28", OLD)

    assert ranges.plan(KilnConfig.load(root), root) == []


def test_groups_and_optional_dependencies_move(root: Path) -> None:
    path = root / "pyproject.toml"
    document = DocumentUtils.read_document(path)
    document["project"]["optional-dependencies"] = {"x": [OLD]}
    document["dependency-groups"]["dev"] = [
        {"include-group": "workspace"},
        "rn-forge-cli>=0.1.3,<0.2",
    ]
    DocumentUtils.write_document(path, document)

    moves = ranges.plan(KilnConfig.load(root), root)

    assert [move.new for move in moves] == [NEW, "rn-forge-cli>=0.2.0,<0.3"]


def test_write_changes_only_the_moved_strings(root: Path) -> None:
    _dependencies(root, OLD, "httpx>=0.28", "rn-forge-cli>=0.1.3,<0.2")
    path = root / "pyproject.toml"
    before = path.read_text(encoding="utf-8")
    moves = ranges.plan(KilnConfig.load(root), root)

    ranges.write(root, moves)

    assert path.read_text(encoding="utf-8") == before.replace(OLD, NEW).replace(
        "rn-forge-cli>=0.1.3,<0.2", "rn-forge-cli>=0.2.0,<0.3"
    )


def test_release_notes_are_the_sections_between_the_floors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changelog = (
        "## [Unreleased]\n\nUpcoming changes\n\n"
        "## [0.10.0]\n\nBreaking changes\n\n"
        "## [0.9.1]\n\nFixes\n\n"
        "## [0.9.0]\n\nOld changes\n"
    )
    monkeypatch.setattr(ranges, "_fetch", lambda url: changelog)
    move = ranges.Move("pyproject.toml", COMMONS, OLD, NEW, "0.9.0", True)

    assert ranges.release_notes(move) == (
        "## [0.10.0]\n\nBreaking changes\n\n## [0.9.1]\n\nFixes"
    )


def test_unreachable_release_notes_give_the_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ranges, "_fetch", lambda url: None)
    move = ranges.Move("pyproject.toml", COMMONS, OLD, NEW, "0.9.0", True)

    assert ranges.release_notes(move).startswith(
        "release notes: https://raw.githubusercontent.com/rn-forge/pykit/"
    )
