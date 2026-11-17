"""The Sonar tasks: node Sonar and the one coverage task."""

from __future__ import annotations
import os
import pytest
import subprocess
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS
from tests.conftest import requires
from tests.modules.tasks.support import (
    _ci_cells,
    _ci_rendered,
    _ci_tasks,
    _node_lib_root,
    _rendered_yaml,
    _root,
    _secrets_root,
)


def _reports_run(
    tmp_path: Path, lcov: tuple[str, ...]
) -> subprocess.CompletedProcess[str]:
    root = _node_lib_root(tmp_path / "cell")
    cycle.apply(root, home=tmp_path / "home")
    stub = tmp_path / "bin"
    stub.mkdir()
    pnpm = stub / "pnpm"
    pnpm.write_text('#!/bin/sh\necho "pnpm $*"\n')
    pnpm.chmod(0o755)
    repo = tmp_path / "work"
    for name in lcov:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text("")
    repo.mkdir(exist_ok=True)
    return subprocess.run(
        [
            "task",
            "-t",
            str(root / "Taskfile.yml"),
            "--dir",
            str(repo),
            "ci:sonar:reports",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{stub}:{os.environ['PATH']}"},
    )


@requires("task")
def test_reports_runs_tests_and_prints_the_reports(tmp_path: Path) -> None:
    done = _reports_run(
        tmp_path, ("coverage/b/lcov.info", "coverage/a/lcov.info", "coverage/a/x.txt")
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout == "reports=coverage/a/lcov.info,coverage/b/lcov.info\n"


@requires("task")
def test_reports_fails_without_an_lcov_report(tmp_path: Path) -> None:
    done = _reports_run(tmp_path, ())
    assert done.returncode != 0
    assert "::error::No lcov.info found under coverage/" in done.stdout + done.stderr


def _reports_run_with_projects(
    tmp_path: Path, projects: str, lcov: tuple[str, ...]
) -> subprocess.CompletedProcess[str]:
    root = _node_lib_root(tmp_path / "cell")
    cycle.apply(root, home=tmp_path / "home")
    stub = tmp_path / "bin"
    stub.mkdir()
    pnpm = stub / "pnpm"
    pnpm.write_text(
        '#!/bin/sh\ncase "$*" in\n  *"show projects"*) echo \'' + projects + "'"
        ' ;;\n  *) echo "pnpm $*" ;;\nesac\n'
    )
    pnpm.chmod(0o755)
    repo = tmp_path / "work"
    repo.mkdir()
    for name in lcov:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text("")
    return subprocess.run(
        [
            "task",
            "-t",
            str(root / "Taskfile.yml"),
            "--dir",
            str(repo),
            "ci:sonar:reports",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{stub}:{os.environ['PATH']}"},
    )


@requires("task")
def test_reports_passes_a_workspace_with_no_projects(
    tmp_path: Path,
) -> None:
    done = _reports_run_with_projects(tmp_path, "[]", ())
    assert done.returncode == 0, done.stderr
    assert done.stdout == "reports=\n"


@requires("task")
def test_reports_fails_a_project_with_no_report(tmp_path: Path) -> None:
    done = _reports_run_with_projects(tmp_path, '["foo"]', ())
    # task reports a failed command as 201 and names the command's own status.
    assert done.returncode != 0
    assert "exit status 1" in done.stderr
    assert "::error::No lcov.info found under coverage/" in done.stdout + done.stderr


@requires("task")
def test_reports_prints_the_report_path(tmp_path: Path) -> None:
    done = _reports_run_with_projects(tmp_path, '["foo"]', ("coverage/foo/lcov.info",))
    assert done.returncode == 0, done.stderr
    assert done.stdout == "reports=coverage/foo/lcov.info\n"


def test_reports_is_described_and_public(tmp_path: Path) -> None:
    task = _ci_tasks(_node_lib_root(tmp_path))["tasks"]["sonar:reports"]  # type: ignore[index]
    assert task["desc"]
    assert "internal" not in task


def test_package_packs_and_verifies(tmp_path: Path) -> None:
    task = _ci_tasks(_node_lib_root(tmp_path))["tasks"]["smoke"]  # type: ignore[index]
    assert task["desc"]
    assert "internal" not in task
    assert task["cmds"] == ["pnpm exec nx run-many -t pack verify-dist verify-consumer"]


def test_sonar_runs_the_root_verb(tmp_path: Path) -> None:
    for archetype, root in _ci_cells(tmp_path):
        text = (root / ".github/workflows/_sonar.yml").read_text(encoding="utf-8")
        steps = YamlUtils.load(text)["jobs"]["sonar"]["steps"]
        runs = [step.get("run") for step in steps]
        assert "task test:coverage" in runs, archetype
        assert "ci:coverage" not in text, archetype


def test_node_lib_reports(tmp_path: Path) -> None:
    root = _secrets_root(tmp_path, "node-lib")
    tasks = _ci_rendered(root)
    assert "coverage" not in tasks
    assert tasks["sonar:reports"].get("internal") is not True
    steps = YamlUtils.load(
        (root / ".github/workflows/_sonar.yml").read_text(encoding="utf-8")
    )["jobs"]["sonar"]["steps"]
    reports = next(
        s for s in steps if s.get("run", "").startswith("task ci:sonar:reports")
    )
    assert reports["run"] == 'task ci:sonar:reports >> "$GITHUB_OUTPUT"'
    scan = steps[-1]
    assert f"steps.{reports['id']}.outputs.reports" in scan["with"]["args"]


def test_old_key_refused(tmp_path: Path) -> None:
    root = _root(tmp_path, extra="\n[tasks.audit]\nignore = []\n")
    with pytest.raises(
        AppException, match=r"tasks.audit moved to \[ci.checks\] pip-audit"
    ):
        KilnConfig.load(root)


def test_ignored_ids_render(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra=(
            '\n[ci.checks]\npip-audit = { ignore = [{ id = "PYSEC-2026-1", '
            'reason = "a" }] }\n'
        ),
    )
    cycle.apply(root, home=tmp_path / "home")
    _, python = _rendered_yaml(root)
    assert "--ignore-vuln PYSEC-2026-1" in YamlUtils.serialize(python["lint:audit"])


def test_workspace_test_tolerates_no_tests(tmp_path: Path) -> None:
    guard = "|| [ $? -eq 5 ]"
    for archetype, guarded in (("python-lib", True), ("python-app", False)):
        root = _root(tmp_path / archetype, archetype)
        rendered = {
            a.path: a.content for a in TASKS.artifacts(KilnConfig.load(root), root)
        }
        tasks = YamlUtils.load(rendered["tasks/python.yml"])["tasks"]
        for task in ("test", "test:coverage"):
            text = "\n".join(
                c["cmd"] if isinstance(c, dict) else c for c in tasks[task]["cmds"]
            )
            assert (guard in text) is guarded
