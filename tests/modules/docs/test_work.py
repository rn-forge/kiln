"""Tests for rn_forge.kiln.modules.docs.work."""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.kiln.modules.docs.work import load_work, read_metadata, validate

TABLE = "|  |  |\n| -- | -- |\n"
EPIC = (
    "# E1 — Epic\n\n" + TABLE + "| **State** | Active |\n"
    "| **Start Date** | 2026-01-01 |\n\n"
    "| ID | Feature | State | Tags |\n| -- | -- | -- | -- |\n"
    "| [F1.1](F1.1-a.md) | A | Active | |\n"
    "| [F1.2](F1.2-b.md) | B | New | deferred |\n"
)
ACTIVE = (
    "# F1.1 — A\n\n" + TABLE + "| **State** | Active |\n| **Parent** | E1 |\n"
    "| **Iteration** | [release-1](../../../releases/release-1/index.md) |\n"
    "| **Predecessors** | none |\n"
)
DEFERRED = (
    "# F1.2 — B\n\n" + TABLE + "| **State** | New |\n| **Parent** | E1 |\n"
    "| **Tags** | deferred |\n| **Predecessors** | none |\n"
    "| **Entry criteria** | later |\n"
)
RELEASE = "# Release 1\n\n" + TABLE + "| **Status** | in progress |\n"

VALID = {
    "specs/epics/E1-x/index.md": EPIC,
    "specs/epics/E1-x/F1.1-a.md": ACTIVE,
    "specs/epics/E1-x/F1.2-b.md": DEFERRED,
    "releases/release-1/index.md": RELEASE,
}


def codes(tmp_path: Path, files: dict[str, str]) -> list[str]:
    docs = tmp_path / "docs"
    for name, text in files.items():
        path = docs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return [f.code for f in validate(load_work(docs), tmp_path)]


def broken(tmp_path: Path, name: str, old: str, new: str) -> list[str]:
    return codes(tmp_path, {**VALID, name: VALID[name].replace(old, new)})


def test_s13_2_1_read_metadata_accepts_both_table_styles() -> None:
    plain = "# T\n\n| | |\n| --- | --- |\n| **State** | New |\n| **Tags** | a, b |\n"
    mdformat = "# T\n\n|  |  |\n| -- | -- |\n| **State** | New |\n| **Tags** | a, b |\n"
    expected = [("State", "New"), ("Tags", "a, b")]
    assert read_metadata(plain) == expected
    assert read_metadata(mdformat) == expected


def test_s13_2_1_read_metadata_none_after_a_paragraph() -> None:
    assert read_metadata("# T\n\ntext\n\n" + TABLE + "| **State** | New |\n") is None


def test_s13_2_1_valid_tree_has_no_findings(tmp_path: Path) -> None:
    assert codes(tmp_path, VALID) == []


E = "specs/epics/E1-x/index.md"
F1 = "specs/epics/E1-x/F1.1-a.md"
F2 = "specs/epics/E1-x/F1.2-b.md"
R = "releases/release-1/index.md"


@pytest.mark.parametrize(
    ("code", "name", "old", "new"),
    [
        ("no-metadata", F1, TABLE, "text\n\n" + TABLE),
        (
            "unknown-key",
            F1,
            "| **Parent** | E1 |",
            "| **Parent** | E1 |\n| **Bogus** | x |",
        ),
        (
            "repeated-key",
            F1,
            "| **Parent** | E1 |",
            "| **Parent** | E1 |\n| **Parent** | E1 |",
        ),
        (
            "key-order",
            F1,
            "| **State** | Active |\n| **Parent** | E1 |",
            "| **Parent** | E1 |\n| **State** | Active |",
        ),
        ("missing-key", F1, "| **Parent** | E1 |\n", ""),
        ("invalid-state", E, "| **State** | Active |", "| **State** | Done |"),
        ("dates", E, "| **Start Date** | 2026-01-01 |\n", ""),
        (
            "dates",
            R,
            "in progress |",
            "in progress |\n| **Finish Date** | 2026-02-02 |",
        ),
        ("entry-criteria", F2, "| **Tags** | deferred |\n", ""),
        (
            "iteration",
            F1,
            "| **Iteration** | [release-1](../../../releases/release-1/index.md) |\n",
            "",
        ),
        ("iteration", F1, "release-1](", "release-9]("),
        (
            "no-state-column",
            E,
            "| ID | Feature | State | Tags |",
            "| ID | Feature | Status | Tags |",
        ),
        ("state-mismatch", E, "| A | Active |", "| A | New |"),
    ],
)
def test_s13_2_1_each_rule_reports_one_finding(
    tmp_path: Path, code: str, name: str, old: str, new: str
) -> None:
    assert old in VALID[name]
    assert broken(tmp_path, name, old, new) == [f"docs.work-{code}"]


def test_s13_2_1_duplicate_ids(tmp_path: Path) -> None:
    files = {**VALID, "specs/epics/E1-x/F1.1-dup.md": ACTIVE}
    assert codes(tmp_path, files) == ["docs.work-duplicate-id"]


def test_s13_2_1_reports_every_broken_page(tmp_path: Path) -> None:
    files = {
        **VALID,
        E: EPIC.replace("| **State** | Active |", "| **State** | Done |"),
        R: RELEASE.replace("in progress", "later"),
    }
    assert sorted(codes(tmp_path, files)) == ["docs.work-invalid-state"] * 2


def test_s13_2_1_bare_id_row_is_never_compared(tmp_path: Path) -> None:
    files = {**VALID, E: EPIC.replace("[F1.1](F1.1-a.md)", "F1.1")}
    assert codes(tmp_path, files) == []
