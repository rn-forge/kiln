"""Tests for the `kiln-devops` console script."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from rn_forge.kiln.devops import cli, github


def _env(monkeypatch: pytest.MonkeyPatch, event: str, ref_type: str, name: str) -> None:
    monkeypatch.setenv("EVENT_NAME", event)
    monkeypatch.setenv("REF_TYPE", ref_type)
    monkeypatch.setenv("REF_NAME", name)


def test_s6_7_2_cli_prints_branch_argument(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _env(monkeypatch, "workflow_dispatch", "branch", "feature/release-2")
    monkeypatch.setattr("sys.argv", ["kiln-devops", "sonar-target"])
    assert cli.main() == 0
    assert capsys.readouterr().out == (
        "branch-arg=-Dsonar.branch.name=feature/release-2\n"
    )


def test_s6_7_2_cli_prints_empty_argument_for_pull_request(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _env(monkeypatch, "pull_request", "branch", "12/merge")
    monkeypatch.setattr("sys.argv", ["kiln-devops", "sonar-target"])
    assert cli.main() == 0
    assert capsys.readouterr().out == "branch-arg=\n"


def test_s6_7_2_cli_exits_with_message_for_tag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _env(monkeypatch, "workflow_dispatch", "tag", "v1.0")
    monkeypatch.setattr("sys.argv", ["kiln-devops", "sonar-target"])
    with pytest.raises(SystemExit) as exit_info:
        cli.main()
    assert "unsupported ref" in str(exit_info.value.code)
    assert capsys.readouterr().out == ""


def test_verify_release_without_a_tag_passes_validation() -> None:
    args = cli._parser().parse_args(["verify-release", "--source", "pypi"])
    assert args.tag is None
    cli._validate(args)
    assert args.tag is None


def test_verify_release_rejects_a_malformed_tag() -> None:
    args = cli._parser().parse_args(
        ["verify-release", "--source", "pypi", "--", "-bad"]
    )
    with pytest.raises(ValueError, match="invalid tag"):
        cli._validate(args)


def _adapter_workspace(root: Path, extras: str) -> None:
    (root / "pkgs/data/src/data").mkdir(parents=True)
    (root / "pkgs/data/src/data/pandas.py").write_text("")
    (root / "pyproject.toml").write_text('[tool.uv.workspace]\nmembers = ["pkgs/*"]\n')
    (root / "pkgs/data/pyproject.toml").write_text(
        '[project]\nname = "data"\nversion = "1"\n\n'
        f"[project.optional-dependencies]\n{extras}\n\n"
        '[tool.workspace-ci]\nadapters = ["pandas"]\n'
    )


def test_s6_7_2_cli_adapters_is_silent_when_they_are_declared_correctly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _adapter_workspace(tmp_path, "pandas = []")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["adapters"]) == 0
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


def test_s6_7_2_cli_adapters_prints_each_problem_to_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _adapter_workspace(tmp_path, "excel = []")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["adapters"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "data: adapter pandas has no extra pandas\n"


def test_s6_7_2_3_prog_is_kiln_devops(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(["--help"])
    assert raised.value.code == 0
    assert capsys.readouterr().out.startswith("usage: kiln-devops")


def _real(name: str) -> str:
    return os.path.realpath(name)


def _release_stubs(
    monkeypatch: pytest.MonkeyPatch, draft: str | None, tagged: bool
) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="abc123\n")

    monkeypatch.setattr(github, "release_draft", lambda tag: draft)
    monkeypatch.setattr(github, "remote_tag_exists", lambda tag: tagged)
    monkeypatch.setattr(github.subprocess, "run", run)
    return calls


def test_s6_7_5_3_release_state_prints_the_four_lines(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _release_stubs(monkeypatch, "true", True)
    assert cli.main(["release-state", "v1"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "tag=v1\nshould-release=true\ndraft=true\ntagged=true\n"
    assert captured.err == ""
    assert calls == []


def test_s6_7_5_3_release_state_of_a_published_release_says_so_on_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _release_stubs(monkeypatch, "false", True)
    assert cli.main(["release-state", "v1"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "tag=v1\nshould-release=false\ndraft=false\ntagged=true\n"
    assert captured.err == "Release v1 already published; nothing to do.\n"


def test_s6_7_5_3_release_source_checks_out_an_existing_tag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _release_stubs(monkeypatch, None, True)
    assert cli.main(["release-source", "v1"]) == 0
    assert capsys.readouterr().out == "sha=abc123\n"
    assert calls == [
        ["git", "fetch", "--no-tags", "origin", "refs/tags/v1:refs/tags/v1"],
        ["git", "checkout", "--detach", "v1"],
        ["git", "rev-parse", "HEAD"],
    ]


def test_s6_7_5_3_release_source_without_a_tag_only_reports_head(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _release_stubs(monkeypatch, None, False)
    assert cli.main(["release-source", "v1"]) == 0
    assert capsys.readouterr().out == "sha=abc123\n"
    assert calls == [["git", "rev-parse", "HEAD"]]


def test_s6_7_5_3_release_publish_replaces_a_draft_and_prints_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _release_stubs(monkeypatch, "true", False)
    argv = [
        "release-publish",
        "v1",
        "--title",
        "T",
        "--target",
        "abc1234",
        "a.whl",
        "b.gz",
    ]
    assert cli.main(argv) == 0
    assert capsys.readouterr().out == ""
    assert calls == [
        ["gh", "release", "delete", "v1", "--yes"],
        [
            "gh", "release", "create", "v1", _real("a.whl"), _real("b.gz"),
            "--target", "abc1234",
            "--title", "T", "--generate-notes",
        ],
    ]  # fmt: skip


def test_s7_6_3_2_release_publish_passes_notes_file_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _release_stubs(monkeypatch, None, False)
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc1234"]
    assert cli.main([*argv, "--notes-file", "n.md", "a.whl"]) == 0
    assert calls == [
        [
            "gh", "release", "create", "v1", _real("a.whl"), "--target", "abc1234",
            "--title", "T", "--notes-file", _real("n.md"), "--latest=false",
        ]
    ]  # fmt: skip


def test_s6_7_5_3_release_publish_of_a_published_release_runs_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _release_stubs(monkeypatch, "false", True)
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc1234", "a.whl"]
    assert cli.main(argv) == 0
    captured = capsys.readouterr()
    assert (captured.out, calls) == ("", [])
    assert captured.err == "Release v1 already published; nothing to do.\n"


def test_s6_7_5_3_a_failing_command_ends_with_its_exit_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(github, "release_draft", lambda tag: None)
    monkeypatch.setattr(github, "remote_tag_exists", lambda tag: False)
    monkeypatch.setattr(github.subprocess, "run", run)
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc1234", "a.whl"]
    with pytest.raises(SystemExit) as exit_info:
        cli.main(argv)
    assert exit_info.value.code == 7


def test_s7_6_2_7_cli_notes_prints_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [1.0.0] - 2026-01-01\n\n- Done.\n", encoding="utf-8")
    assert cli.main(["notes", str(changelog), "1.0.0"]) == 0
    assert capsys.readouterr().out == "- Done.\n"


def test_s7_6_2_8_cli_notes_exits_1_on_missing_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [1.0.0]\n\n- Done.\n", encoding="utf-8")
    assert cli.main(["notes", str(changelog), "2.0.0"]) == 1
    captured = capsys.readouterr()
    assert "2.0.0" in captured.err
    assert captured.out == ""


def _upload_stubs(
    monkeypatch: pytest.MonkeyPatch,
    draft: str | None,
    tagged: bool,
    on_index: bool,
    upload_status: int = 0,
) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        status = upload_status if command[0] == "uv" else 0
        return subprocess.CompletedProcess(command, status)

    def release_draft(tag: str) -> str | None:
        calls.append(["release_draft", tag])
        return draft

    def remote_tag_exists(tag: str) -> bool:
        calls.append(["remote_tag_exists", tag])
        return tagged

    def on_index_stub(host: str, name: str, version: str) -> bool:
        calls.append(["on_index", host, name, version])
        return on_index

    monkeypatch.setattr(github, "release_draft", release_draft)
    monkeypatch.setattr(github, "remote_tag_exists", remote_tag_exists)
    monkeypatch.setattr(github, "on_index", on_index_stub)
    monkeypatch.setattr(github.subprocess, "run", run)
    return calls


PUBLISH = ["release-publish", "pkg-a-v1.2.0", "--title", "T", "--target", "abc1234"]


def test_s7_6_4_13_upload_pypi_runs_before_gh_release_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _upload_stubs(monkeypatch, None, False, False)
    assert cli.main([*PUBLISH, "--upload", "pypi", "a.whl", "a.cdx.json"]) == 0
    commands = [c for c in calls if c[0] in ("uv", "gh")]
    assert ["on_index", "pypi.org", "pkg-a", "1.2.0"] in calls
    assert commands[0] == [
        "uv", "publish", "--trusted-publishing", "always", _real("a.whl")
    ]  # fmt: skip
    assert commands[1][:4] == ["gh", "release", "create", "pkg-a-v1.2.0"]
    assert len(commands) == 2


def test_s6_8_3_4_release_assets_leave_out_attestations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _upload_stubs(monkeypatch, None, False, False)
    files = ["a.whl", "a.whl.publish.attestation", "a.cdx.json"]
    assert cli.main([*PUBLISH, "--upload", "pypi", *files]) == 0
    commands = [c for c in calls if c[0] in ("uv", "gh")]
    assert commands[0][4:] == [
        _real("a.whl"),
        _real("a.whl.publish.attestation"),
    ]
    assert commands[1][3:5] == ["pkg-a-v1.2.0", _real("a.whl")]
    assert _real("a.whl.publish.attestation") not in commands[1]
    assert _real("a.cdx.json") in commands[1]


def test_s7_6_4_14_upload_pypi_skips_a_version_already_on_the_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _upload_stubs(monkeypatch, None, False, True)
    assert cli.main([*PUBLISH, "--upload", "pypi", "a.whl"]) == 0
    assert [c[0] for c in calls if c[0] in ("uv", "gh")] == ["gh"]


def test_s7_6_4_15_upload_pypi_leaves_a_published_release_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _upload_stubs(monkeypatch, "false", True, False)
    assert cli.main([*PUBLISH, "--upload", "pypi", "a.whl"]) == 0
    assert [c for c in calls if c[0] in ("uv", "gh", "on_index")] == []


def test_s7_6_4_16_upload_testpypi_runs_no_gh_and_no_release_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _upload_stubs(monkeypatch, "false", True, False)
    assert cli.main([*PUBLISH, "--upload", "testpypi", "a.whl"]) == 0
    assert ["on_index", "test.pypi.org", "pkg-a", "1.2.0"] in calls
    assert [c[0] for c in calls if c[0] not in ("on_index",)] == ["uv"]
    assert "--publish-url" in calls[-1]


def test_s7_6_4_17_a_failed_upload_exits_before_any_gh_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _upload_stubs(monkeypatch, None, False, False, upload_status=3)
    with pytest.raises(SystemExit) as exit_info:
        cli.main([*PUBLISH, "--upload", "pypi", "a.whl"])
    assert exit_info.value.code == 3
    assert [c for c in calls if c[0] == "gh"] == []


def _rejected(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    message: str,
) -> None:
    calls = _release_stubs(monkeypatch, None, False)
    seen: list[str] = []
    monkeypatch.setattr(github, "release_draft", lambda tag: seen.append(tag))
    assert cli.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.err == f"kiln-devops: {message}\n"
    assert captured.out == ""
    assert (calls, seen) == ([], [])


@pytest.mark.parametrize("command", ["release-state", "release-source"])
@pytest.mark.parametrize("tag", ["--repo=x", "-v1", "a b", ""])
def test_s6_7_7_1_a_bad_tag_exits_2_before_any_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    tag: str,
) -> None:
    _rejected(monkeypatch, capsys, [command, "--", tag], f"invalid tag '{tag}'")


def test_s6_7_7_1_a_bad_publish_tag_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["release-publish", "--title", "T", "--target", "abc1234", "--"]
    _rejected(monkeypatch, capsys, [*argv, "a b", "a.whl"], "invalid tag 'a b'")


@pytest.mark.parametrize("tag", ["v0.1.0", "rn-forge-commons-v1.2.3"])
def test_s6_7_7_1_good_tags_pass(monkeypatch: pytest.MonkeyPatch, tag: str) -> None:
    _release_stubs(monkeypatch, "true", True)
    assert cli.main(["release-state", tag]) == 0


@pytest.mark.parametrize(
    "target", ["abc", "ABC1234", "abc123g", "--x=1234567", "a" * 41]
)
def test_s6_7_7_2_a_bad_target_exits_2(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    target: str,
) -> None:
    argv = ["release-publish", "v1", "--title", "T", f"--target={target}", "a.whl"]
    _rejected(monkeypatch, capsys, argv, f"invalid target '{target}'")


@pytest.mark.parametrize("title", ["-x", "a\nb", "", "a\x7fb"])
def test_s6_7_7_3_a_bad_title_exits_2(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    title: str,
) -> None:
    argv = ["release-publish", "v1", f"--title={title}", "--target", "abc1234", "a.whl"]
    _rejected(monkeypatch, capsys, argv, f"invalid title '{title}'")


def test_s6_7_7_3_a_title_with_spaces_and_dots_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _release_stubs(monkeypatch, None, False)
    argv = ["release-publish", "v1", "--title", "rn-forge-commons v1.2.3"]
    assert cli.main([*argv, "--target", "abc1234", "a.whl"]) == 0
    assert "rn-forge-commons v1.2.3" in calls[0]


def test_s6_7_7_4_a_release_file_outside_the_working_directory_exits_2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc1234"]
    _rejected(
        monkeypatch,
        capsys,
        [*argv, "../outside.whl"],
        "'../outside.whl' is outside the working directory",
    )


def test_s6_7_7_4_a_sibling_directory_with_the_same_prefix_is_outside(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "work").mkdir()
    monkeypatch.chdir(tmp_path / "work")
    sibling = str(tmp_path / "work2" / "a.whl")
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc1234", sibling]
    _rejected(
        monkeypatch, capsys, argv, f"'{sibling}' is outside the working directory"
    )


def test_s6_7_7_4_a_symlink_out_of_the_working_directory_is_outside(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    (work / "link.whl").symlink_to(tmp_path / "elsewhere.whl")
    monkeypatch.chdir(work)
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc1234"]
    _rejected(
        monkeypatch,
        capsys,
        [*argv, "link.whl"],
        "'link.whl' is outside the working directory",
    )


def test_s6_7_7_4_a_file_below_the_working_directory_is_passed_on_resolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    calls = _release_stubs(monkeypatch, None, False)
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc1234"]
    assert cli.main([*argv, "dist/../dist/a.whl"]) == 0
    assert os.path.realpath(tmp_path / "dist" / "a.whl") in calls[0]


def test_s6_7_7_4_notes_changelog_outside_the_working_directory_exits_2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "work").mkdir()
    monkeypatch.chdir(tmp_path / "work")
    assert cli.main(["notes", "../CHANGELOG.md", "1.0.0"]) == 2
    captured = capsys.readouterr()
    assert captured.err == (
        "kiln-devops: '../CHANGELOG.md' is outside the working directory\n"
    )
    assert captured.out == ""


def test_s6_7_7_5_notes_file_may_be_below_the_temp_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    temp = tmp_path / "tmp"
    temp.mkdir()
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(temp))
    calls = _release_stubs(monkeypatch, None, False)
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc1234"]
    assert cli.main([*argv, "--notes-file", str(temp / "n.md"), "a.whl"]) == 0
    assert os.path.realpath(temp / "n.md") in calls[0]


def test_s6_7_7_5_notes_file_elsewhere_exits_2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "work").mkdir()
    (tmp_path / "tmp").mkdir()
    monkeypatch.chdir(tmp_path / "work")
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path / "tmp"))
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc1234"]
    path = str(tmp_path / "n.md")
    _rejected(
        monkeypatch,
        capsys,
        [*argv, "--notes-file", path, "a.whl"],
        f"'{path}' is outside the working directory",
    )
