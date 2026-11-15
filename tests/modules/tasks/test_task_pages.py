"""One Pages site."""

from __future__ import annotations
import os
import subprocess
from pathlib import Path
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS
from tests.conftest import requires
from tests.modules.tasks.support import _ci_tasks, _node_lib_root


@requires("task")
def test_s9_3_1_1_docs_site_runs_both_commands_with_no_environment(
    tmp_path: Path,
) -> None:
    tasks = _ci_tasks(_node_lib_root(tmp_path / "root"))["tasks"]
    site = tasks["docs:site"]  # type: ignore[index]
    assert site["desc"]
    assert "internal" not in site
    assert site["cmds"] == [
        "pnpm exec nx run-many -t compodoc build-storybook",
        "{{.DEVOPS}} site-assemble .docs-site",
    ]
    root = _node_lib_root(tmp_path / "cell")
    cycle.apply(root, home=tmp_path / "home")
    stub = tmp_path / "bin"
    stub.mkdir()
    for tool in ("pnpm", "uvx"):
        script = stub / tool
        script.write_text(f'#!/bin/sh\necho "{tool} $*"\n')
        script.chmod(0o755)
    repo = tmp_path / "work"
    repo.mkdir()
    done = subprocess.run(
        ["task", "-t", str(root / "Taskfile.yml"), "--dir", str(repo), "ci:docs:site"],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PATH": f"{stub}:{os.environ['PATH']}"},
    )
    assert "pnpm exec nx run-many -t compodoc build-storybook" in done.stdout
    assert "kiln-devops site-assemble .docs-site" in done.stdout


def test_s9_3_1_2_node_lib_has_no_docs_affected_task(tmp_path: Path) -> None:
    root = _node_lib_root(tmp_path)
    assert "docs:affected" not in _ci_tasks(root)["tasks"]  # type: ignore[operator]
    rendered = {a.path: a.content for a in TASKS.artifacts(KilnConfig.load(root), root)}
    text = rendered["tasks/ci.yml"]
    assert "BUILD" not in text
    assert "docs:affected" not in text
