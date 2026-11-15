"""`kiln new`: staging, retention and the git repository it leaves."""

from __future__ import annotations
import inspect
import json
import os
import pytest
import subprocess
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.kiln import commands
from tests.conftest import new_repo
from typing import Any
from tests.commands.new_support import _last_json


@pytest.fixture(autouse=True)
def _in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`kiln new` stages beneath the current directory; keep that out of the repo."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


def _hashes(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


def test_s4_5_9_1_success_retains_staging_and_target_equals_workspace(
    tmp_path: Path,
) -> None:
    target = tmp_path / "out" / "demo"
    new_repo(target, archetype="python-tool", docs="none", yes=True)

    run = tmp_path / ".staging" / "demo"
    assert all((run / part).is_dir() for part in ("backend", "frontend", "workspace"))
    assert (run / "backend" / "pyproject.toml").is_file()
    state = ".rn-forge/kiln/state.json"
    staged, final = _hashes(run / "workspace"), _hashes(target)
    # `new` records the scaffolded list in the target's state.json last (S16.9.6).
    for hashes in (staged, final):
        document = json.loads(hashes[state])
        document["metadata"].pop("scaffolded", None)
        hashes[state] = json.dumps(document, sort_keys=True).encode()
    assert staged == final
    assert (tmp_path / ".staging" / ".gitignore").read_text(encoding="utf-8") == "/*\n"


def test_s4_5_9_2_workspace_holds_only_reconciled_files(tmp_path: Path) -> None:
    new_repo(tmp_path / "demo", archetype="python-tool", docs="none", yes=True)

    run = tmp_path / ".staging" / "demo"
    raw = (run / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    assembled = (run / "workspace" / "pyproject.toml").read_text(encoding="utf-8")
    assert raw != assembled
    assert "[tool.pyright]" in assembled
    assert "[tool.pyright]" not in raw
    assert not (run / "backend" / ".rn-forge").exists()
    assert not (run / "backend" / "README.md").exists()


def test_s4_5_9_3_staging_is_ignored_inside_a_git_worktree(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    new_repo(tmp_path / "demo", archetype="python-tool", docs="none", yes=True)

    check = subprocess.run(
        ["git", "check-ignore", ".staging/demo/workspace"], cwd=tmp_path, check=False
    )
    assert check.returncode == 0
    assert not (tmp_path / ".gitignore").exists()


@pytest.mark.parametrize("target_exists", [False, True])
def test_s4_5_9_4_failure_retains_staging_and_writes_no_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target_exists: bool
) -> None:
    def boom(*_args: object) -> None:
        raise AppException("boom")

    monkeypatch.setattr(commands, "instructions_scaffold", boom)
    target = tmp_path / "demo"
    if target_exists:
        target.mkdir()

    with pytest.raises(AppException, match="boom"):
        new_repo(target, archetype="python-tool", docs="none", yes=True)

    assert (tmp_path / ".staging" / "demo" / "backend" / "pyproject.toml").is_file()
    assert target.exists() is target_exists
    assert not target_exists or list(target.iterdir()) == []


def test_s4_5_9_5_existing_staging_is_refused_untouched(tmp_path: Path) -> None:
    run = tmp_path / ".staging" / "demo"
    run.mkdir(parents=True)
    (run / "keep").write_text("review state", encoding="utf-8")

    with pytest.raises(AppException, match="already exists"):
        new_repo(tmp_path / "demo", archetype="python-tool", docs="none", yes=True)

    assert [p.name for p in run.iterdir()] == ["keep"]
    assert not (tmp_path / "demo").exists()


def test_s4_5_11_1_success_leaves_a_git_repository_without_commits(
    tmp_path: Path,
) -> None:
    target = tmp_path / "demo"
    new_repo(target, archetype="python-tool", docs="none", yes=True)

    top = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert Path(top).resolve() == target.resolve()
    head = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        check=False,
    )
    assert head.returncode != 0
    remotes = subprocess.run(
        ["git", "-C", str(target), "remote"], capture_output=True, text=True
    )
    assert remotes.stdout == ""


def test_s4_5_11_2_dry_run_writes_no_git(tmp_path: Path) -> None:
    target = tmp_path / "preview"
    new_repo(target, archetype="python-tool", docs="none", yes=True, dry_run=True)
    assert not target.exists()


def test_s4_5_11_3_failure_or_refusal_creates_no_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    full = tmp_path / "full"
    full.mkdir()
    (full / "x").write_text("x", encoding="utf-8")
    with pytest.raises(AppException):
        new_repo(full, archetype="python-tool", docs="none", yes=True)
    assert not (full / ".git").exists()

    def boom(*_args: object) -> None:
        raise AppException("boom")

    monkeypatch.setattr(commands, "instructions_scaffold", boom)
    failed = tmp_path / "failed"
    with pytest.raises(AppException, match="boom"):
        new_repo(failed, archetype="python-tool", docs="none", yes=True)
    assert not (failed / ".git").exists()


def test_s4_5_11_4_json_plan_does_not_list_git(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    new_repo(
        tmp_path / "demo", archetype="python-tool", docs="none", yes=True, json=True
    )
    payload = _last_json(capsys)
    assert not any(".git" in str(row).split("/") for row in payload["artifacts"])


@pytest.mark.parametrize("archetype", ["python-lib", "python-app"])
def test_s4_5_11_5_other_archetypes_get_git(tmp_path: Path, archetype: str) -> None:
    new_repo(tmp_path / "demo", archetype=archetype, docs="none", yes=True)
    assert (tmp_path / "demo" / ".git").is_dir()


def test_s4_5_9_6_no_retention_or_cleanup_flag_and_no_rnf_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert set(inspect.signature(commands.new).parameters) == {
        "directory",
        "archetype",
        "docs",
        "backend",
        "frontend",
        "module",
        "config",
        "owner",
        "allow_untested",
        "dry_run",
        "yes",
        "json",
    }

    seen: list[bool] = []

    def stop(*_args: object) -> None:
        seen.append("RNF_HOME" in os.environ)
        raise AppException("stop")

    monkeypatch.delenv("RNF_HOME", raising=False)
    monkeypatch.setattr(commands, "instructions_scaffold", stop)
    with pytest.raises(AppException, match="stop"):
        new_repo(tmp_path / "demo", archetype="python-tool", docs="none", yes=True)
    assert seen == [False]
