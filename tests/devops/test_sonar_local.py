"""Tests for `kiln-devops sonar-local` with git, task and the scanner faked."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

from rn_forge.kiln.devops import cli, sonar

TOKEN = "s3cret-token-value"


class Fake:
    """Stands in for `subprocess.run`, recording each call."""

    def __init__(self) -> None:
        self.branch = "feature/x"
        self.dirty = ""
        self.calls: list[tuple[list[str], dict[str, Any]]] = []
        self.test_status = 0
        self.scan_status = 0

    def __call__(
        self, cmd: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        assert isinstance(cmd, list)
        assert not kwargs.get("shell")
        self.calls.append((cmd, kwargs))
        out, status = "", 0
        if cmd[:2] == ["git", "branch"]:
            out = self.branch + "\n"
        elif cmd[:2] == ["git", "status"]:
            out = self.dirty
        elif cmd[0] == "task":
            status = self.test_status
        elif cmd[0] == "sonar-scanner":
            status = self.scan_status
        return subprocess.CompletedProcess(cmd, status, out, "")

    def ran(self, name: str) -> list[tuple[list[str], dict[str, Any]]]:
        return [c for c in self.calls if c[0][0] == name]


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> Fake:
    fake = Fake()
    monkeypatch.setattr(subprocess, "run", fake)
    monkeypatch.setattr(sonar.shutil, "which", lambda _name: "/bin/sonar-scanner")
    monkeypatch.setenv("SONAR_TOKEN", TOKEN)
    return fake


def _main(*args: str) -> int:
    return cli.main(["sonar-local", *args])


def test_s6_10_2_1_dry_run_prints_target_and_commands_and_runs_nothing(
    fake: Fake, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SONAR_TOKEN")
    monkeypatch.setattr(sonar.shutil, "which", lambda _name: None)
    assert _main("--dry-run") == 0
    out = capsys.readouterr().out
    assert "target: feature/x" in out
    assert "task test:coverage" in out
    assert "sonar-scanner -Dsonar.branch.name=feature/x" in out
    assert "-Dsonar.qualitygate.wait=true" in out
    assert not fake.ran("task") and not fake.ran("sonar-scanner")


def test_s6_10_2_2_full_run_runs_coverage_then_scanner(fake: Fake) -> None:
    assert _main() == 0
    names = [c[0][0] for c in fake.calls if c[0][0] in ("task", "sonar-scanner")]
    assert names == ["task", "sonar-scanner"]
    assert fake.ran("task")[0][0] == ["task", "test:coverage"]
    assert fake.ran("sonar-scanner")[0][0] == [
        "sonar-scanner",
        "-Dsonar.branch.name=feature/x",
        "-Dsonar.qualitygate.wait=true",
    ]


def test_s6_10_2_3_missing_token_exits_2(
    fake: Fake, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SONAR_TOKEN")
    assert _main() == 2
    assert "SONAR_TOKEN" in capsys.readouterr().err
    assert not fake.ran("task")


def test_s6_10_2_4_missing_scanner_exits_2(
    fake: Fake, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sonar.shutil, "which", lambda _name: None)
    assert _main() == 2
    assert "sonar-scanner is not installed" in capsys.readouterr().err
    assert not fake.ran("task")


@pytest.mark.parametrize(
    ("branch", "argv"),
    [("main", []), ("main", ["--branch", "main"]), ("", ["--branch", "main"])],
)
def test_s6_10_2_5_main_is_refused(
    fake: Fake, branch: str, argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    fake.branch = branch
    assert _main(*argv) == 2
    assert "main" in capsys.readouterr().err
    assert not fake.ran("task") and not fake.ran("sonar-scanner")


def test_s6_10_2_6_detached_head_needs_branch(
    fake: Fake, capsys: pytest.CaptureFixture[str]
) -> None:
    fake.branch = ""
    assert _main() == 2
    assert "detached HEAD" in capsys.readouterr().err
    assert _main("--branch", "feature/y") == 0
    assert "-Dsonar.branch.name=feature/y" in fake.ran("sonar-scanner")[0][0]


def test_s6_10_2_7_branch_must_match_checked_out(
    fake: Fake, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _main("--branch", "feature/other") == 2
    assert "differs" in capsys.readouterr().err
    assert not fake.ran("task")
    assert _main("--branch", "feature/x") == 0


def test_s6_10_2_8_dirty_tree_is_scanned_with_a_note(
    fake: Fake, capsys: pytest.CaptureFixture[str]
) -> None:
    fake.dirty = " M file.py\n"
    assert _main() == 0
    assert "not CI evidence" in capsys.readouterr().out
    assert fake.ran("sonar-scanner")


def test_s6_10_2_9_scanner_environment_drops_ci_metadata(
    fake: Fake, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REF", "refs/pull/1/merge")
    monkeypatch.setenv("KEEP_ME", "1")
    assert _main() == 0
    env = fake.ran("sonar-scanner")[0][1]["env"]
    assert not {"CI", "GITHUB_ACTIONS", "GITHUB_REF"} & env.keys()
    assert env["KEEP_ME"] == "1"
    assert env["SONAR_TOKEN"] == TOKEN


def test_s6_10_2_10_token_is_never_in_arguments_or_output(
    fake: Fake, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _main() == 0
    assert _main("--dry-run") == 0
    captured = capsys.readouterr()
    assert TOKEN not in captured.out + captured.err
    assert all(TOKEN not in part for cmd, _ in fake.calls for part in cmd)


def test_s6_10_2_11_failing_tests_stop_before_the_scan(fake: Fake) -> None:
    fake.test_status = 3
    assert _main() == 3
    assert not fake.ran("sonar-scanner")


def test_s6_10_2_12_scanner_status_propagates(fake: Fake) -> None:
    fake.scan_status = 4
    assert _main() == 4


def test_s6_10_2_13_unknown_option_is_a_usage_error(fake: Fake) -> None:
    with pytest.raises(SystemExit) as exit_info:
        _main("--nope")
    assert exit_info.value.code == 2
