"""Launching and applying a repository upgrade."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import ConfigFormat, DocumentUtils
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.commons.runtime.subprocess import Process

from rn_forge.kiln import commands
from rn_forge.kiln.commands import output
from rn_forge.kiln.config import CONFIG_PATH
from rn_forge.kiln.main import app
from rn_forge.kiln.modules.core import cycle, process, umbrella
from rn_forge.kiln.modules.python import ranges

from tests.conftest import git

STATE = umbrella.STATE_PATH
OLD_RANGE = "rn-forge-commons>=0.9.0,<0.10"
NEW_RANGE = "rn-forge-commons>=0.10.0,<0.11"
LOCK = Path("uv.lock")


def _dependencies(root: Path, requirement: str) -> None:
    path = root / "pyproject.toml"
    document = DocumentUtils.read_document(path)
    document["project"]["dependencies"] = [requirement]
    DocumentUtils.write_document(path, document)


def _commit(root: Path, message: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)


def _files(root: Path) -> dict[str, bytes]:
    return {
        name: (root / name).read_bytes()
        for name in git(
            root, "ls-files", "--cached", "--others", "--exclude-standard"
        ).splitlines()
    }


def _set_track(root: Path) -> None:
    path = root / CONFIG_PATH
    document = DocumentUtils.read_document(path)
    document.setdefault("kiln", {})["track"] = "feature/v1"
    DocumentUtils.write_document(path, document)
    _commit(root, "track kiln branch")


@dataclass
class Repo:
    root: Path
    calls: list[tuple[str | Path, ...]] = field(default_factory=list)
    exit_codes: dict[tuple[str | Path, ...], list[int]] = field(default_factory=dict)
    before_validate: Callable[[], None] | None = None
    update_lock: bool = False

    @property
    def task_calls(self) -> list[tuple[str | Path, ...]]:
        return [args for args in self.calls if args[0] == "task"]

    @property
    def ref(self) -> str:
        return DocumentUtils.read(self.root / CONFIG_PATH)["kiln"]["ref"]

    @property
    def dependencies(self) -> list[str]:
        return DocumentUtils.read(self.root / "pyproject.toml")["project"][
            "dependencies"
        ]


@pytest.fixture
def repo(
    monkeypatch: pytest.MonkeyPatch,
    rendered_copy: Callable[..., Path],
) -> Iterator[Repo]:
    root = rendered_copy("python-tool")
    monkeypatch.chdir(root)
    commands.pin("a" * 40)
    cycle.apply(root)
    _dependencies(root, OLD_RANGE)
    (root / LOCK).write_text("old lock", encoding="utf-8")
    git(root, "init", "-q")
    _commit(root, "base")

    repo = Repo(root)
    run = process.run

    def fake_run(
        label: str, *args: str | Path, **kwargs: Any
    ) -> Process | SimpleNamespace:
        if args[0] not in {"task", "uvx"}:
            return run(label, *args, **kwargs)
        repo.calls.append(args)
        assert kwargs == {
            "cwd": root.resolve(),
            "check": False,
            "capture_output": False,
        }
        codes = repo.exit_codes.get(args if args[0] == "task" else ("uvx",))
        if (
            args == ("task", "setup")
            and repo.update_lock
            and repo.task_calls.count(args) == 1
        ):
            (root / LOCK).write_text("new lock", encoding="utf-8")
        if args == ("task", "validate") and repo.before_validate is not None:
            repo.before_validate()
        return SimpleNamespace(
            return_code=codes.pop(0) if codes else 0, stdout="", stderr=""
        )

    monkeypatch.setattr(process, "run", fake_run)
    monkeypatch.setattr(ranges, "_fetch", lambda _: None)
    yield repo
    console.set_mode(OutputMode.PLAIN)


def _dispatch(ref: str, *options: str) -> tuple[str, ...]:
    return (
        "uvx",
        "--from",
        f"rn-forge-kiln @ git+https://github.com/rn-forge/kiln@{ref}",
        "kiln",
        "repo-upgrade",
        "--target-ref",
        ref,
        *options,
    )


def test_upgrade_dispatches_to_the_resolved_kiln(
    repo: Repo, kiln_remote_sha: str
) -> None:
    before = _files(repo.root)
    commands.upgrade("feature/v1")
    assert repo.calls == [_dispatch(kiln_remote_sha, "--target-track", "feature/v1")]
    assert _files(repo.root) == before


def test_upgrade_with_a_tag_passes_no_track(repo: Repo) -> None:
    _set_track(repo.root)
    commands.upgrade("v0.0.1")
    assert repo.calls == [_dispatch("v0.0.1")]


def test_upgrade_without_a_ref_follows_track(repo: Repo, kiln_remote_sha: str) -> None:
    _set_track(repo.root)
    commands.upgrade(force=True)
    assert repo.calls == [
        _dispatch(kiln_remote_sha, "--target-track", "feature/v1", "--force")
    ]


def test_upgrade_reports_a_failing_target(repo: Repo, kiln_remote_sha: str) -> None:
    repo.exit_codes[("uvx",)] = [2]
    before = _files(repo.root)
    with pytest.raises(
        AppException, match=rf"upgrade.target-failed: .*{kiln_remote_sha} exited 2"
    ):
        commands.upgrade(kiln_remote_sha)
    assert _files(repo.root) == before


def test_target_applies_pins_moves_and_validates(
    repo: Repo, kiln_remote_sha: str
) -> None:
    state = (repo.root / STATE).read_bytes()

    def observe_candidate() -> None:
        assert repo.ref == kiln_remote_sha
        assert (repo.root / STATE).read_bytes() != state
        assert repo.dependencies == [NEW_RANGE]

    repo.before_validate = observe_candidate
    commands.upgrade(target_ref=kiln_remote_sha, target_track="feature/v1")
    assert repo.ref == kiln_remote_sha
    assert DocumentUtils.read(repo.root / CONFIG_PATH)["kiln"]["track"] == "feature/v1"
    assert repo.dependencies == [NEW_RANGE]
    assert repo.task_calls == [("task", "setup"), ("task", "validate")]


def test_target_with_no_moves_still_validates(repo: Repo, kiln_remote_sha: str) -> None:
    _dependencies(repo.root, NEW_RANGE)
    _commit(repo.root, "current dependencies")
    commands.upgrade(target_ref=kiln_remote_sha)
    assert repo.task_calls == [("task", "setup"), ("task", "validate")]


def test_target_refuses_an_untracked_tree_unchanged(
    repo: Repo, kiln_remote_sha: str
) -> None:
    (repo.root / "untracked.txt").write_text("keep me", encoding="utf-8")
    before = _files(repo.root)
    with pytest.raises(AppException, match="upgrade.dirty"):
        commands.upgrade(target_ref=kiln_remote_sha)
    assert _files(repo.root) == before
    assert repo.task_calls == []


def test_target_leaves_a_blocked_plan_unchanged(
    repo: Repo, kiln_remote_sha: str
) -> None:
    (repo.root / ".editorconfig").write_text("root = false\n", encoding="utf-8")
    _commit(repo.root, "drift")
    before = _files(repo.root)
    with pytest.raises(AppException, match="unapproved"):
        commands.upgrade(target_ref=kiln_remote_sha)
    assert _files(repo.root) == before
    assert repo.task_calls == []


def test_target_restores_pin_files_and_lock_after_failed_validate(
    repo: Repo, kiln_remote_sha: str
) -> None:
    managed = repo.root / ".editorconfig"
    managed.unlink()
    state_path = repo.root / STATE
    state = DocumentUtils.read(state_path)
    del state["entries"][".editorconfig"]
    state_path.write_text(
        DocumentUtils.dumps(state, ConfigFormat.JSON), encoding="utf-8"
    )
    _commit(repo.root, "earlier baseline without editorconfig")
    ignored = repo.root / ".tmp/saved.txt"
    ignored.parent.mkdir(exist_ok=True)
    ignored.write_text("keep me", encoding="utf-8")
    assert git(repo.root, "status", "--porcelain", "--untracked-files=all") == ""
    before = _files(repo.root)

    def observe_writes() -> None:
        assert managed.is_file()
        assert (repo.root / LOCK).read_text(encoding="utf-8") == "new lock"

    repo.before_validate = observe_writes
    repo.update_lock = True
    repo.exit_codes[("task", "validate")] = [1]
    with pytest.raises(AppException, match="upgrade.failed: task validate failed"):
        commands.upgrade(target_ref=kiln_remote_sha)

    assert repo.task_calls == [
        ("task", "setup"),
        ("task", "validate"),
        ("task", "setup"),
    ]
    assert _files(repo.root) == before
    assert not managed.exists()
    assert ignored.read_text(encoding="utf-8") == "keep me"


def test_target_skips_validate_and_restores_after_failed_setup(
    repo: Repo, kiln_remote_sha: str
) -> None:
    before = _files(repo.root)
    repo.update_lock = True
    repo.exit_codes[("task", "setup")] = [1, 0]
    with pytest.raises(AppException, match="upgrade.failed: task setup failed"):
        commands.upgrade(target_ref=kiln_remote_sha)
    assert repo.task_calls == [("task", "setup"), ("task", "setup")]
    assert _files(repo.root) == before


def test_target_reports_a_failed_recovery_setup(
    repo: Repo, kiln_remote_sha: str
) -> None:
    repo.exit_codes[("task", "setup")] = [0, 1]
    repo.exit_codes[("task", "validate")] = [1]
    with pytest.raises(AppException, match="recovery task setup also failed"):
        commands.upgrade(target_ref=kiln_remote_sha)


def test_force_keeps_an_applied_upgrade_that_fails_validation(
    repo: Repo, kiln_remote_sha: str
) -> None:
    repo.exit_codes[("task", "validate")] = [1]
    with pytest.raises(AppException, match="upgrade.kept: task validate failed"):
        commands.upgrade(target_ref=kiln_remote_sha, force=True)
    assert repo.ref == kiln_remote_sha
    assert repo.dependencies == [NEW_RANGE]
    assert repo.task_calls == [("task", "setup"), ("task", "validate")]


def test_force_does_not_keep_a_failed_apply(
    repo: Repo, kiln_remote_sha: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = _files(repo.root)

    def fail(root: Path) -> None:
        assert (root / STATE).read_bytes() != before[str(STATE)]
        raise AppException("ownership checks failed")

    monkeypatch.setattr(output, "fail_on_errors", fail)
    with pytest.raises(AppException, match="ownership checks failed"):
        commands.upgrade(target_ref=kiln_remote_sha, force=True)
    assert _files(repo.root) == before
    assert repo.task_calls == []


def test_cli_runs_upgrade(repo: Repo, kiln_remote_sha: str) -> None:
    assert app(["repo-upgrade", "--ref", kiln_remote_sha]) == 0
    assert repo.calls == [_dispatch(kiln_remote_sha)]
