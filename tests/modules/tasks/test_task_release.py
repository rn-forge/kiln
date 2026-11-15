"""Dispatch release tasks."""

from __future__ import annotations
import os
import pytest
import subprocess
from pathlib import Path
from rn_forge.kiln.modules.core import cycle
from tests.conftest import git, requires
from tests.modules.tasks.support import (
    ARCHETYPES,
    _ci_tasks,
    _commit,
    _node_lib_root,
    _root,
)


RELEASE_TASKS = (
    "release:state",
    "release:author",
    "release:tag",
    "release:verify",
    "release:push",
    "release:github",
    "release:publish",
    "release:finalize",
    "release:latest",
    "verify-release",
)


def _release_run(
    tmp_path: Path,
    task: str,
    env: dict[str, str] | None = None,
    stubs: dict[str, str] | None = None,
    tag: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `ci:<task>` in a git repository with `stubs` (name -> sh body) first on PATH."""
    root = _node_lib_root(tmp_path / "cell")
    cycle.apply(root, home=tmp_path / "home")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (stubs or {}).items():
        stub = bin_dir / name
        stub.write_text(f"#!/bin/sh\n{body}\n")
        stub.chmod(0o755)
    repo = tmp_path / "work"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    _commit(repo, "a.txt")
    if tag:
        _commit(repo, "b.txt")
        git(repo, "tag", tag)
    output = tmp_path / "output"
    return subprocess.run(
        ["task", "-t", str(root / "Taskfile.yml"), "--dir", str(repo), f"ci:{task}"],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "GITHUB_OUTPUT": str(output),
            "RUNNER_TEMP": str(tmp_path),
            **(env or {}),
        },
    )


def test_s9_1_5_4_release_tasks_are_described_and_public(tmp_path: Path) -> None:
    tasks = _ci_tasks(_node_lib_root(tmp_path))["tasks"]
    for name in RELEASE_TASKS:
        assert tasks[name]["desc"].startswith("CI only"), name  # type: ignore[index]
        assert "internal" not in tasks[name], name  # type: ignore[operator]
        assert "pipefail" not in "\n".join(tasks[name]["cmds"]), name  # type: ignore[index]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s9_1_5_4_other_archetypes_render_no_release_tasks(
    tmp_path: Path, archetype: str
) -> None:
    tasks = _ci_tasks(_root(tmp_path, archetype))["tasks"]
    assert "release:author" not in tasks  # type: ignore[arg-type]


@pytest.mark.parametrize("env", [{}])
@requires("task")
def test_s9_3_5_5_verify_fails_when_no_tarball_was_written(
    tmp_path: Path, env: dict[str, str]
) -> None:
    done = _release_run(tmp_path, "release:verify", env, {"pnpm": "exit 0"})

    assert done.returncode != 0
    output = done.stdout + done.stderr
    assert "exit status 1" in output
    assert "::error::No tarball in dist/tarballs" in output


@pytest.mark.parametrize("env", [{}])
@requires("task")
def test_s9_3_5_6_verify_passes_when_a_tarball_was_written(
    tmp_path: Path, env: dict[str, str]
) -> None:
    stub = "mkdir -p dist/tarballs; : > dist/tarballs/x.tgz"
    done = _release_run(tmp_path, "release:verify", env, {"pnpm": stub})

    assert done.returncode == 0, done.stderr


@requires("task")
def test_s9_3_5_7_package_is_unguarded(tmp_path: Path) -> None:
    tasks = _ci_tasks(_node_lib_root(tmp_path))["tasks"]
    assert tasks["smoke"]["cmds"] == [  # type: ignore[index]
        "pnpm exec nx run-many -t pack verify-dist verify-consumer"
    ]
    done = _release_run(
        tmp_path / "run", "smoke", stubs={"pnpm": "echo No tasks were run"}
    )
    assert done.returncode == 0, done.stderr
    assert "No tasks were run" in done.stdout


@pytest.mark.parametrize("local", [True, False])
@requires("task")
def test_s9_1_5_4_latest_downloads_tarballs_only_when_none_are_local(
    tmp_path: Path, local: bool
) -> None:
    log = tmp_path / "calls"
    stubs = {
        "gh": f'echo "gh $*" >> {log}\ncase "$*" in *"view latest"*) echo old ;; *"view v1"*) echo new ;; esac',
        "git": f'echo "git $*" >> {log}\ncase "$1" in rev-parse) echo abc ;; esac',
    }
    root = _node_lib_root(tmp_path / "cell")
    cycle.apply(root, home=tmp_path / "home")
    repo = tmp_path / "work"
    (repo / "dist" / "tarballs").mkdir(parents=True)
    if local:
        (repo / "dist" / "tarballs" / "a.tgz").write_text("")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in stubs.items():
        (bin_dir / name).write_text(f"#!/bin/sh\n{body}\n")
        (bin_dir / name).chmod(0o755)
    done = subprocess.run(
        [
            "task",
            "-t",
            str(root / "Taskfile.yml"),
            "--dir",
            str(repo),
            "ci:release:latest",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "TAG": "v1"},
    )
    assert done.returncode == 0, done.stderr
    calls = log.read_text()
    assert ("release download v1" in calls) is (not local)
    assert "gh release create latest dist/tarballs/" in calls
    assert "git push origin latest --force" in calls
