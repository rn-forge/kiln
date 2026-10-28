"""Tests for the `kiln-devops` console script."""

from __future__ import annotations

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
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc", "a.whl", "b.gz"]
    assert cli.main(argv) == 0
    assert capsys.readouterr().out == ""
    assert calls == [
        ["gh", "release", "delete", "v1", "--yes"],
        [
            "gh", "release", "create", "v1", "a.whl", "b.gz", "--target", "abc",
            "--title", "T", "--generate-notes",
        ],
    ]  # fmt: skip


def test_s6_7_5_3_release_publish_of_a_published_release_runs_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _release_stubs(monkeypatch, "false", True)
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc", "a.whl"]
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
    argv = ["release-publish", "v1", "--title", "T", "--target", "abc", "a.whl"]
    with pytest.raises(SystemExit) as exit_info:
        cli.main(argv)
    assert exit_info.value.code == 7
