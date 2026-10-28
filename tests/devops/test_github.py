"""Tests for the GitHub Actions adapter's Sonar target selection."""

from __future__ import annotations

import pytest

from rn_forge.kiln.devops import github


@pytest.mark.parametrize(
    ("event", "ref_name", "expected"),
    [
        ("push", "main", "main"),
        ("workflow_dispatch", "feature/release-2", "feature/release-2"),
        ("workflow_dispatch", "fix/a_b.c-1/x+y", "fix/a_b.c-1/x+y"),
        ("workflow_dispatch", "main", "main"),
    ],
)
def test_s6_7_2_branch_targets_exact_ref_name(
    event: str, ref_name: str, expected: str
) -> None:
    assert github.sonar_branch(event, "branch", ref_name) == expected


@pytest.mark.parametrize("ref_name", ["12/merge", "feature/x"])
def test_s6_7_2_pull_request_passes_no_branch(ref_name: str) -> None:
    # Fork PRs are skipped by the job's `if:`; the event alone decides here.
    assert github.sonar_branch("pull_request", "branch", ref_name) == ""


@pytest.mark.parametrize("event", ["workflow_dispatch", "push"])
def test_s6_7_2_tag_ref_is_unsupported(event: str) -> None:
    with pytest.raises(ValueError, match="unsupported ref"):
        github.sonar_branch(event, "tag", "v1.0")


def test_s6_7_2_unsupported_event() -> None:
    with pytest.raises(ValueError, match="unsupported event"):
        github.sonar_branch("schedule", "branch", "main")


def test_s6_7_4_3_a_schedule_trigger_raises() -> None:
    with pytest.raises(ValueError):
        github.sonar_branch("schedule", "branch", "main")


def test_s6_7_5_1_release_state_covers_every_case() -> None:
    cases = [
        (None, False, ("true", "false", "false")),
        ("true", True, ("true", "true", "true")),
        ("true", False, ("true", "true", "false")),
        ("false", True, ("false", "false", "true")),
    ]
    for draft, tagged, (should, is_draft, is_tagged) in cases:
        state = github.release_state("v1.2.3", draft, tagged)
        assert list(state) == ["tag", "should-release", "draft", "tagged"]
        assert state == {
            "tag": "v1.2.3",
            "should-release": should,
            "draft": is_draft,
            "tagged": is_tagged,
        }


def test_s6_7_5_2_publish_commands_covers_every_case() -> None:
    files = ["dist/b.whl", "dist/a.tar.gz"]

    def call(draft: str | None, tagged: bool) -> list[list[str]]:
        return github.publish_commands("v1", "Title", "abc123", files, draft, tagged)

    assert call("false", True) == []
    assert call("true", True) == [
        ["gh", "release", "delete", "v1", "--yes"],
        [
            "gh", "release", "create", "v1", *files, "--verify-tag",
            "--title", "Title", "--generate-notes",
        ],
    ]  # fmt: skip
    assert call(None, False) == [
        [
            "gh", "release", "create", "v1", *files, "--target", "abc123",
            "--title", "Title", "--generate-notes",
        ]
    ]  # fmt: skip
    assert call("true", False)[0][:3] == ["gh", "release", "delete"]


def test_s7_6_3_1_publish_commands_with_notes_are_not_latest() -> None:
    files = ["dist/a.whl"]
    notes = ["--title", "T", "--notes-file", "n.md", "--latest=false"]
    for tagged, where in ((True, ["--verify-tag"]), (False, ["--target", "abc"])):
        commands = github.publish_commands(
            "v1", "T", "abc", files, None, tagged, notes="n.md"
        )
        assert commands == [["gh", "release", "create", "v1", *files, *where, *notes]]
