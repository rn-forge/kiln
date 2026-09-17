"""S5.2.1 — the reconcile, tested offline against the captured frontend scaffold.

No test here runs `pnpm`: `tests/fixtures/scaffold/nx-angular/` (S5.2.2) stands
in for a live `create-nx-workspace` + `@nx/angular:application` run, copied
into a temporary workspace directory and folded into a temporary root that
already holds a `python-web-app` scaffold.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.python.artifacts import render
from rn_forge.kiln.modules.python.frontend import reconcile_frontend
from rn_forge.kiln.modules.python.scaffold import scaffold

FIXTURE = Path(__file__).parents[2] / "fixtures" / "scaffold" / "nx-angular"

WEB_CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "python-web-app"

[archetype."python-web-app"]
backend = "fastapi"
frontend = "angular"
{extra}
"""


def _root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, extra: str = "") -> Path:
    """A root with the `python`/uv side of a `python-web-app` scaffold already
    done, `scaffold_frontend` stubbed out so the setup itself never runs
    `pnpm`."""
    monkeypatch.setattr(
        "rn_forge.kiln.modules.python.scaffold.scaffold_frontend", lambda *a: None
    )
    root = tmp_path / "root"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(WEB_CONFIG.format(extra=extra), encoding="utf-8")
    scaffold(root, KilnConfig.load(root))
    return root


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "ws"
    shutil.copytree(FIXTURE, workspace)
    return workspace


def test_s5_2_1_reconcile_moves_fixture_into_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path, monkeypatch)
    workspace = _workspace(tmp_path)
    config = KilnConfig.load(root)

    reconcile_frontend(root, workspace, config)

    assert (root / "nx.json").is_file()
    assert (root / "package.json").is_file()
    assert (root / "apps" / "web" / "project.json").is_file()
    assert not (root / "ws").exists()


def test_s5_2_1_reconcile_appends_scaffolder_gitignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path, monkeypatch)
    workspace = _workspace(tmp_path)
    fixture_gitignore = (workspace / ".gitignore").read_text(encoding="utf-8")
    config = KilnConfig.load(root)

    reconcile_frontend(root, workspace, config)

    body = (root / ".gitignore").read_text(encoding="utf-8")
    for line in fixture_gitignore.splitlines():
        if line.strip():
            assert line in body


def test_s5_2_1_reconcile_renames_web_dir_and_rewrites_project_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path, monkeypatch, extra='web_dir = "apps/frontend"')
    workspace = _workspace(tmp_path)
    config = KilnConfig.load(root)

    reconcile_frontend(root, workspace, config)

    assert not (root / "apps" / "web").exists()
    project = DocumentUtils.read(root / "apps" / "frontend" / "project.json")
    assert project["root"] == "apps/frontend"
    assert project["sourceRoot"] == "apps/frontend/src"


def test_s5_2_1_reconcile_refuses_a_root_that_already_holds_readme(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path, monkeypatch)
    (root / "README.md").write_text("existing\n", encoding="utf-8")
    workspace = _workspace(tmp_path)
    config = KilnConfig.load(root)

    with pytest.raises(AppException, match="README.md"):
        reconcile_frontend(root, workspace, config)


def test_s5_2_1_no_kiln_artifact_lies_under_web_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path, monkeypatch)
    config = KilnConfig.load(root)

    for artifact in render(config):
        assert not artifact.key.startswith("apps/web")
