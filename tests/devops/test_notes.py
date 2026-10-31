"""Tests for `rn_forge.kiln.devops.notes`."""

from __future__ import annotations

import pytest

from rn_forge.kiln.devops.notes import changelog_section

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
