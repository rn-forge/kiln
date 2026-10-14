"""Tests for rn_forge.kiln.modules.docs.work."""

from __future__ import annotations

from pathlib import Path

import mdformat
import pytest

from rn_forge.kiln.modules.docs.work import (
    BOARD_BLOCK,
    EPIC_RANGE,
    EPICS_BLOCK,
    SCOPE_BLOCK,
    STORIES_BLOCK,
    STORY_HEADING_RE,
    Story,
    Work,
    epic_range,
    load_work,
    range_label,
    read_metadata,
    read_stories,
    render_board,
    render_epics,
    render_scope,
    render_stories,
    validate,
)

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


def _tree(tmp_path: Path, files: dict[str, str]):
    docs = tmp_path / "docs"
    for name, text in files.items():
        path = docs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return load_work(docs)


def _stable(block, body: str) -> None:
    fenced = f"{block.begin}\n{body}{block.end}\n"
    assert (
        mdformat.text(
            fenced,
            options={"wrap": 80, "compact_tables": True},
            extensions={"gfm", "tables", "mkdocs"},
        )
        == fenced
    )


RELEASE_2 = "# Release 2\n\n" + TABLE + "| **Status** | planned |\n"


def test_s13_2_2_render_board_lists_releases_newest_first_and_the_backlog(
    tmp_path: Path,
) -> None:
    work = _tree(tmp_path, {**VALID, "releases/release-2/index.md": RELEASE_2})
    board = render_board(work)
    assert board == (
        "\n## Releases\n\n"
        "| Release | Status | Features |\n| -- | -- | -- |\n"
        "| [Release 2](../releases/release-2/index.md) | planned | — |\n"
        "| [Release 1](../releases/release-1/index.md) | in progress | 1 Active |\n"
        "\n## Backlog\n\nFeatures with no Iteration, by State and epic.\n"
        "\n### Deferred\n\n"
        "| Epic | Features | Entry criteria |\n| -- | -- | -- |\n"
        "| [E1 — Epic](epics/E1-x/index.md) | [F1.2](epics/E1-x/F1.2-b.md) "
        "| Per feature; see the epic. |\n\n"
    )
    _stable(BOARD_BLOCK, board)


def test_s13_2_2_render_board_of_an_empty_tree(tmp_path: Path) -> None:
    board = render_board(_tree(tmp_path, {}))
    assert board == (
        "\n## Releases\n\n| Release | Status | Features |\n| -- | -- | -- |\n"
        "\n## Backlog\n\nEvery feature is on a release or Removed.\n\n"
    )
    _stable(BOARD_BLOCK, board)


def test_s13_2_2_render_board_new_rows_and_fileless_and_empty_epics(
    tmp_path: Path,
) -> None:
    epic2 = "# E2 — Two\n\n" + TABLE + "| **State** | New |\n"
    epic3 = (
        "# E3 — Three\n\n" + TABLE + "| **State** | Closed |\n"
        "| **Start Date** | 2026-01-01 |\n| **Closed Date** | 2026-02-01 |\n\n"
        "| ID | Feature | State | Tags |\n| -- | -- | -- | -- |\n"
        "| F3.1 | Old | New | |\n| F3.2 | Gone | Removed | |\n"
        "| F3.3 | Later | New | deferred |\n"
    )
    work = _tree(
        tmp_path,
        {
            **VALID,
            "specs/epics/E2-y/index.md": epic2,
            "specs/epics/E3-z/index.md": epic3,
        },
    )
    board = render_board(work)
    assert (
        "### New\n\n| Epic | Features |\n| -- | -- |\n"
        "| [E2 — Two](epics/E2-y/index.md) | — |\n"
        "| [E3 — Three](epics/E3-z/index.md) | F3.1 |\n"
    ) in board
    assert (
        "| [E3 — Three](epics/E3-z/index.md) | F3.3 | Per feature; see the epic. |"
        in board
    )
    assert "F3.2" not in board
    _stable(BOARD_BLOCK, board)


def test_s13_2_2_a_bare_row_with_a_file_is_listed_once(tmp_path: Path) -> None:
    epic = EPIC.replace("[F1.2](F1.2-b.md)", "F1.2")
    board = render_board(_tree(tmp_path, {**VALID, "specs/epics/E1-x/index.md": epic}))
    assert (
        "| [E1 — Epic](epics/E1-x/index.md) | [F1.2](epics/E1-x/F1.2-b.md) "
        "| Per feature; see the epic. |\n"
    ) in board
    _stable(BOARD_BLOCK, board)


def test_s13_2_2_render_scope_orders_features_numerically(tmp_path: Path) -> None:
    def feature(fid: str, state: str) -> str:
        return (
            f"# {fid} — T\n\n" + TABLE + f"| **State** | {state} |\n"
            "| **Parent** | E1 |\n"
            "| **Iteration** | [Release 1](../../../releases/release-1/index.md) |\n"
            "| **Predecessors** | none |\n"
        )

    work = _tree(
        tmp_path,
        {
            **VALID,
            "specs/epics/E1-x/F10.1-c.md": feature("F10.1", "New"),
            "specs/epics/E1-x/F2.1-d.md": feature("F2.1", "Closed"),
        },
    )
    scope = render_scope(work, work.releases[0])
    assert (
        scope
        == (
            "\n| Feature | Epic | State |\n| -- | -- | -- |\n"
            "| [F1.1](../../specs/epics/E1-x/F1.1-a.md) | E1 | Active |\n"
            "| [F2.1](../../specs/epics/E1-x/F2.1-d.md) | E1 | Closed |\n"
            "| [F10.1](../../specs/epics/E1-x/F10.1-c.md) | E1 | New |\n"
        )
        + "\n"
    )
    _stable(SCOPE_BLOCK, scope)


def test_s13_2_2_render_scope_of_an_empty_release_keeps_the_header(
    tmp_path: Path,
) -> None:
    work = _tree(tmp_path, {**VALID, "releases/release-2/index.md": RELEASE_2})
    scope = render_scope(work, work.releases[1])
    assert scope == "\n| Feature | Epic | State |\n| -- | -- | -- |\n\n"
    _stable(SCOPE_BLOCK, scope)


def test_s13_3_1_seeded_board_is_current() -> None:
    seed = (
        Path(__file__).parents[3]
        / "src/rn_forge/kiln/modules/docs/templates/docs/specs/index.md.j2"
    ).read_text(encoding="utf-8")
    body = seed.split(f"{BOARD_BLOCK.begin}\n", 1)[1].split(BOARD_BLOCK.end, 1)[0]
    assert body == render_board(Work((), (), ()))


def test_s14_1_2_epic_range_groups_by_tens() -> None:
    assert EPIC_RANGE == 10
    assert [epic_range(n) for n in (1, 4, 10, 11, 13, 20, 21)] == [
        (1, 10),
        (1, 10),
        (1, 10),
        (11, 20),
        (11, 20),
        (11, 20),
        (21, 30),
    ]
    assert range_label(11, 20) == "E11\u2013E20"


def _epic(number: int, state: str, rest: str = "", title: str = "T") -> str:
    start = "| **Start Date** | 2026-01-01 |\n" if state == "Active" else ""
    return (
        f"# E{number} \u2014 {title}\n\n"
        + TABLE
        + f"| **State** | {state} |\n"
        + (start + rest)
    )


def test_s14_1_2_1_render_epics_puts_each_range_under_its_own_heading(
    tmp_path: Path,
) -> None:
    work = _tree(
        tmp_path,
        {
            **VALID,
            "specs/epics/E12-z/index.md": _epic(12, "New", title="Twelve"),
        },
    )
    body = render_epics(work)
    assert body.startswith(
        "\nJump to: [E1\u2013E10](#e1e10) \u00b7 [E11\u2013E20](#e11e20)\n\n## E1\u2013E10\n\n"
    )
    assert body.index("## E1\u2013E10") < body.index("## E11\u2013E20")
    assert "| [E12 \u2014 Twelve](E12-z/index.md) | New | \u2014 | \u2014 |" in body
    _stable(EPICS_BLOCK, body)


def test_s14_1_2_1_one_epic_gives_one_range_and_one_jump_link(tmp_path: Path) -> None:
    body = render_epics(_tree(tmp_path, VALID))
    assert body.count("## E") == 1
    assert body.count("](#") == 1
    assert "Jump to: [E1\u2013E10](#e1e10)\n" in body
    _stable(EPICS_BLOCK, body)


def test_s14_1_2_2_features_count_files_or_rows_and_deferred_is_marked(
    tmp_path: Path,
) -> None:
    rows = (
        "\n| ID | Feature | State | Tags |\n| -- | -- | -- | -- |\n"
        "| F3.1 | A | Closed | |\n| F3.2 | B | New | |\n| F3.3 | C | New | |\n"
    )
    deferred = "| **Tags** | deferred |\n| **Entry criteria** | later |\n"
    work = _tree(
        tmp_path,
        {
            **VALID,
            "specs/epics/E3-y/index.md": _epic(3, "New", deferred + rows),
        },
    )
    body = render_epics(work)
    # E1 has files F1.1 (Active, release-1) and F1.2 (New): the file states win.
    assert (
        "| [E1 \u2014 Epic](E1-x/index.md) | Active | 1 Active \u00b7 1 New | release-1 |"
        in body
    )
    assert (
        "| [E3 \u2014 T](E3-y/index.md) | New (deferred) | 2 New \u00b7 1 Closed | \u2014 |"
        in body
    )
    _stable(EPICS_BLOCK, body)


def test_s14_1_2_iterations_are_distinct_and_sorted_by_release(tmp_path: Path) -> None:
    def feature(fid: str, release: int) -> str:
        return (
            f"# {fid} \u2014 T\n\n"
            + TABLE
            + "| **State** | New |\n| **Parent** | E1 |\n"
            f"| **Iteration** | [r](../../../releases/release-{release}/index.md) |\n"
            "| **Predecessors** | none |\n"
        )

    work = _tree(
        tmp_path,
        {
            **VALID,
            "releases/release-2/index.md": RELEASE_2,
            "releases/release-10/index.md": RELEASE_2,
            "specs/epics/E1-x/F1.3-c.md": feature("F1.3", 10),
            "specs/epics/E1-x/F1.4-d.md": feature("F1.4", 2),
        },
    )
    assert "| release-1, release-2, release-10 |" in render_epics(work)


def test_s14_1_2_no_epics_says_so() -> None:
    assert render_epics(Work((), (), ())) == "\nNo epics yet.\n\n"
    _stable(EPICS_BLOCK, render_epics(Work((), (), ())))


def test_s14_1_2_seeded_epic_list_is_current() -> None:
    seed = (
        Path(__file__).parents[3]
        / "src/rn_forge/kiln/modules/docs/templates/docs/specs/epics/index.md.j2"
    ).read_text(encoding="utf-8")
    body = seed.split(f"{EPICS_BLOCK.begin}\n", 1)[1].split(EPICS_BLOCK.end, 1)[0]
    assert body == render_epics(Work((), (), ()))


def test_s14_2_1_1_read_stories_reads_id_title_state_and_depends_on() -> None:
    text = (
        "# F9.9 \u2014 F\n\n## S4.5.9 \u2014 x\n\n"
        "**State:** Closed (2026-09-26) \u00b7 **Depends on:** S4.5.1, S5.2.4\n\n"
        "**Build:**\n\n## S4.5.10 \u2014 y `z`: w\n\n**State:** New\n"
    )
    assert read_stories(text) == (
        Story("S4.5.9", "x", "Closed (2026-09-26)", "S4.5.1, S5.2.4"),
        Story("S4.5.10", "y `z`: w", "New", ""),
    )
    assert STORY_HEADING_RE.match("## S1.2.3 \u2014 t")


def test_s14_2_1_1_read_stories_ignores_fenced_code_and_stops_state_at_a_dot() -> None:
    text = (
        "## S1.1.1 \u2014 a\n\n"
        "**State:** Closed (2026-09-26) \u00b7 **Unblocked 2026-09-25:** pykit\n\n"
        "```markdown\n## S1.1.2 \u2014 example\n\n**State:** New\n```\n\n"
        "## S1.1.3 \u2014 no state line\n"
    )
    assert read_stories(text) == (
        Story("S1.1.1", "a", "Closed (2026-09-26)", ""),
        Story("S1.1.3", "no state line", "", ""),
    )


def _feature_with(tmp_path: Path, body: str):
    work = _tree(tmp_path, {**VALID, "specs/epics/E1-x/F1.1-a.md": ACTIVE + body})
    return next(f for f in work.features if f.id == "F1.1")


def test_s14_2_1_2_render_stories_counts_links_and_dashes(tmp_path: Path) -> None:
    feature = _feature_with(
        tmp_path,
        "\n## S1.1.1 \u2014 `kiln new`: a | b\n\n**State:** Closed (2026-09-16)\n"
        "\n## S1.1.2 \u2014 Two\n\n**State:** New \u00b7 **Depends on:** S1.1.1\n"
        "\n## S1.1.3 \u2014 Three\n\n**State:** New\n",
    )
    body = render_stories(feature)
    assert body == (
        "\n**Stories:** 2 New \u00b7 1 Closed\n\n"
        "| Story | State | Depends on |\n| -- | -- | -- |\n"
        "| [S1.1.1 \u2014 `kiln new`: a \\| b](#s111-kiln-new-a-b) "
        "| Closed (2026-09-16) | \u2014 |\n"
        "| [S1.1.2 \u2014 Two](#s112-two) | New | S1.1.1 |\n"
        "| [S1.1.3 \u2014 Three](#s113-three) | New | \u2014 |\n\n"
    )
    _stable(STORIES_BLOCK, body)


def test_s14_2_1_2_a_feature_without_stories_says_so(tmp_path: Path) -> None:
    body = render_stories(_feature_with(tmp_path, ""))
    assert body == "\nNo stories yet.\n\n"
    _stable(STORIES_BLOCK, body)
