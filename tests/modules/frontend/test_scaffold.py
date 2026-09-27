"""S5.2.1 — the reconcile, tested offline against the captured frontend scaffold.

No test here runs `pnpm`: `tests/fixtures/scaffold/nx-angular/` (S5.2.2) stands
in for a live `create-nx-workspace` + `@nx/angular:application` run, copied
into a temporary workspace directory and folded into a temporary root that
already holds a `python-web-app` scaffold.
"""

from __future__ import annotations

import shutil
from unittest import mock
from pathlib import Path

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.registry import builtin
from rn_forge.kiln.modules.python.artifacts import render
from rn_forge.kiln.modules.frontend.scaffold import (
    reconcile_frontend,
    scaffold_frontend,
)
from rn_forge.kiln.modules.python.scaffold import scaffold

FIXTURE = Path(__file__).parents[2] / "fixtures" / "scaffold" / "nx-angular"

WEB_CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "python-web-app"

[archetype."python-web-app"]
backend = "fastapi"
frontend = "{frontend}"
{extra}
"""


def _root(tmp_path: Path, *, extra: str = "", frontend: str = "angular") -> Path:
    """A root with the `python`/uv side of a `python-web-app` scaffold done."""
    root = tmp_path / "root"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        WEB_CONFIG.format(extra=extra, frontend=frontend), encoding="utf-8"
    )
    scaffold(root, KilnConfig.load(root))
    return root


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE, workspace)
    return workspace


def test_s5_2_1_reconcile_moves_fixture_into_root(tmp_path: Path) -> None:
    root = _root(tmp_path)
    workspace = _workspace(tmp_path)
    config = KilnConfig.load(root)

    reconcile_frontend(root, workspace, config)

    assert (root / "nx.json").is_file()
    assert (root / "package.json").is_file()
    assert (root / "apps" / "web" / "project.json").is_file()
    assert not (root / "workspace").exists()


def test_s5_2_1_reconcile_appends_scaffolder_gitignore(tmp_path: Path) -> None:
    root = _root(tmp_path)
    workspace = _workspace(tmp_path)
    fixture_gitignore = (workspace / ".gitignore").read_text(encoding="utf-8")
    config = KilnConfig.load(root)

    reconcile_frontend(root, workspace, config)

    body = (root / ".gitignore").read_text(encoding="utf-8")
    for line in fixture_gitignore.splitlines():
        if line.strip():
            assert line in body


def test_s5_2_1_reconcile_renames_web_dir_and_rewrites_project_json(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, extra='web_dir = "apps/frontend"')
    workspace = _workspace(tmp_path)
    config = KilnConfig.load(root)

    reconcile_frontend(root, workspace, config)

    assert not (root / "apps" / "web").exists()
    project = DocumentUtils.read(root / "apps" / "frontend" / "project.json")
    assert project["root"] == "apps/frontend"
    assert project["sourceRoot"] == "apps/frontend/src"


def test_s5_2_1_reconcile_refuses_a_root_that_already_holds_readme(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    (root / "README.md").write_text("existing\n", encoding="utf-8")
    workspace = _workspace(tmp_path)
    config = KilnConfig.load(root)

    with pytest.raises(AppException, match="README.md"):
        reconcile_frontend(root, workspace, config)


def test_s5_2_1_no_kiln_artifact_lies_under_web_dir(tmp_path: Path) -> None:
    root = _root(tmp_path)
    config = KilnConfig.load(root)

    for artifact in render(config):
        assert not artifact.key.startswith("apps/web")


def test_s5_2_4_dispatch_rejects_a_frontend_with_no_scaffolder(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, frontend="react")
    config = KilnConfig.load(root)

    with mock.patch("rn_forge.commons.runtime.subprocess.Process.execute") as run:
        with pytest.raises(AppException, match="react"):
            scaffold_frontend(root, config)

    run.assert_not_called()


def test_s5_2_4_frontend_module_owns_the_frontend_option() -> None:
    registry = builtin()
    owners = [
        m.name
        for m in registry.modules
        if any(o.flag == "frontend" for o in m.options())
    ]
    assert owners == ["frontend"]


def test_s4_5_9_reconcile_frontend_leaves_the_raw_tree_untouched(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, extra='web_dir = "apps/frontend"')
    workspace = _workspace(tmp_path)
    before = {p: p.read_bytes() for p in sorted(workspace.rglob("*")) if p.is_file()}
    config = KilnConfig.load(root)

    reconcile_frontend(root, workspace, config)

    after = {p: p.read_bytes() for p in sorted(workspace.rglob("*")) if p.is_file()}
    assert before == after
    assert (root / "apps" / "frontend" / "project.json").is_file()
