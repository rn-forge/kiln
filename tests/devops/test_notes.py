"""Tests for `rn_forge.kiln.devops.notes`."""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.kiln.devops.notes import changelog_section

FIXTURES = Path(__file__).parent / "fixtures"
NX = """# Changelog

## 0.3.0 (2026-10-25)

- Three.

## 0.1.20 (2026-10-20)

- Twenty.

## 10.1.2 (2026-10-10)

- Ten.

## 0.1.2

- Two.
"""

CHANGELOG = """# Changelog

## [Unreleased]

### Added

- Next.

## [0.7.10] - 2026-10-30

### Changed

- Ten.

## [0.7.1] - 2026-10-26

### Changed

- One.

## [0.7.0]

### Added

- Zero.
"""


def test_s7_6_2_1_section_stops_at_next_heading() -> None:
    assert changelog_section(CHANGELOG, "0.7.1") == "### Changed\n\n- One."


def test_s7_6_2_2_last_section_runs_to_end_of_file() -> None:
    assert changelog_section(CHANGELOG, "0.7.0") == "### Added\n\n- Zero."


def test_s7_6_2_3_dated_heading_matches() -> None:
    assert "- Ten." in changelog_section(CHANGELOG, "0.7.10")


def test_s7_6_2_4_version_matches_exactly() -> None:
    assert "- Ten." not in changelog_section(CHANGELOG, "0.7.1")


def test_s7_6_2_5_missing_version_raises() -> None:
    with pytest.raises(ValueError, match="0.9.0"):
        changelog_section(CHANGELOG, "0.9.0")


def test_s7_6_2_6_empty_section_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        changelog_section("## [1.0.0] - 2026-01-01\n\n## [0.9.0]\n\n- x\n", "1.0.0")


def test_s9_4_3_1_nx_dated_heading() -> None:
    assert changelog_section(NX, "0.3.0") == "- Three."


def test_s9_4_3_2_nx_heading_without_date() -> None:
    assert changelog_section(NX, "0.1.2") == "- Two."


def test_s9_4_3_3_nx_version_matches_whole_token() -> None:
    nx = NX.replace("## 0.1.2\n\n- Two.\n", "")
    with pytest.raises(ValueError, match="0.1.2"):
        changelog_section(nx, "0.1.2")


def test_s9_4_3_5_nx_changelog_matches_release_notes_mjs() -> None:
    changelog = (FIXTURES / "changelog-nx.md").read_text(encoding="utf-8")
    printed = (FIXTURES / "changelog-nx-0.3.0.txt").read_text(encoding="utf-8")
    heading, body = printed.split("\n", 1)
    assert heading == "## 0.3.0 (2026-10-25)"
    assert changelog_section(changelog, "0.3.0") == body.strip()
