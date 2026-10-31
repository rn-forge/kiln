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


PYPI_FILES = ["dist/a/a.whl", "dist/a/a.cdx.json", "dist/a/a.tar.gz"]


def test_s7_6_4_7_upload_to_pypi_when_not_on_the_index() -> None:
    assert github.upload_commands("pypi", "a", "1.0", PYPI_FILES, False) == [
        [
            "uv", "publish", "--trusted-publishing", "always",
            "dist/a/a.whl", "dist/a/a.tar.gz",
        ]
    ]  # fmt: skip


def test_s7_6_4_8_upload_to_testpypi_names_the_index() -> None:
    assert github.upload_commands("testpypi", "a", "1.0", PYPI_FILES, False) == [
        [
            "uv", "publish", "--trusted-publishing", "always",
            "--publish-url", "https://test.pypi.org/legacy/",
            "dist/a/a.whl", "dist/a/a.tar.gz",
        ]
    ]  # fmt: skip


@pytest.mark.parametrize("index", ["pypi", "testpypi"])
def test_s7_6_4_9_nothing_is_uploaded_when_the_index_has_the_version(
    index: str,
) -> None:
    assert github.upload_commands(index, "a", "1.0", PYPI_FILES, True) == []


def test_s7_6_4_10_only_wheels_and_sdists_are_uploaded() -> None:
    (command,) = github.upload_commands(
        "pypi", "a", "1.0", ["x.cdx.json", "x.whl", "notes.md"], False
    )
    assert command[-1:] == ["x.whl"]
    assert not any(part.endswith((".cdx.json", ".md")) for part in command)


class _Response:
    status = 200

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def test_s7_6_4_11_on_index_reads_the_json_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urls: list[str] = []

    def urlopen(url: str, **kwargs: object) -> _Response:
        urls.append(url)
        return _Response()

    monkeypatch.setattr(github.urllib.request, "urlopen", urlopen)
    assert github.on_index("pypi.org", "a", "1.0") is True
    assert urls == ["https://pypi.org/pypi/a/1.0/json"]


@pytest.mark.parametrize(("code", "expected"), [(404, False), (500, None)])
def test_s7_6_4_12_on_index_is_false_on_404_and_raises_otherwise(
    monkeypatch: pytest.MonkeyPatch, code: int, expected: bool | None
) -> None:
    def urlopen(url: str, **kwargs: object) -> _Response:
        raise github.urllib.error.HTTPError(url, code, "x", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(github.urllib.request, "urlopen", urlopen)
    if expected is None:
        with pytest.raises(github.urllib.error.HTTPError):
            github.on_index("test.pypi.org", "a", "1.0")
    else:
        assert github.on_index("test.pypi.org", "a", "1.0") is expected
