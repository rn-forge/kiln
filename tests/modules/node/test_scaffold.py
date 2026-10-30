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
from rn_forge.commons.runtime.subprocess import Process

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.node.angular import NX_VERSION, scaffold_angular
from rn_forge.kiln.modules.registry import builtin
from rn_forge.kiln.modules.python.artifacts import render
from rn_forge.kiln.modules.node.scaffold import (
    reconcile_node,
    scaffold_node,
)
from rn_forge.kiln.modules.python.scaffold import add_task_tools, scaffold

FIXTURE = Path(__file__).parents[2] / "fixtures" / "scaffold" / "nx-angular"
UV_FIXTURE = Path(__file__).parents[2] / "fixtures" / "scaffold" / "uv" / ".gitignore"

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


def test_angular_scaffold_has_its_own_git_boundary(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("*\n", encoding="utf-8")
    raw = tmp_path / "frontend"
    raw.mkdir()
    execute = Process.execute

    def run(name: str, *args: str, **kwargs: object) -> None:
        if args[0] == "git":
            execute(name, *args, cwd=str(raw))
        elif name == "nx-workspace":
            assert (raw / ".git").is_dir()
            shutil.copytree(FIXTURE, raw / "workspace")

    with mock.patch(
        "rn_forge.kiln.modules.node.angular.Process.execute", side_effect=run
    ):
        workspace = scaffold_angular(raw)

    boundary = execute(
        "git-root", "git", "rev-parse", "--show-toplevel", cwd=str(workspace)
    )
    assert boundary.stdout is not None
    assert Path(boundary.stdout.strip()).resolve() == raw.resolve()
    assert not (workspace / ".git").exists()


def test_s5_2_1_reconcile_moves_fixture_into_root(tmp_path: Path) -> None:
    root = _root(tmp_path)
    workspace = _workspace(tmp_path)
    config = KilnConfig.load(root)

    reconcile_node(root, workspace, config)

    assert (root / "nx.json").is_file()
    assert (root / "package.json").is_file()
    assert (root / "apps" / "web" / "project.json").is_file()
    assert not (root / "workspace").exists()


def test_s4_4_1_reconcile_drops_scaffolder_readme(tmp_path: Path) -> None:
    root = _root(tmp_path)
    workspace = _workspace(tmp_path)
    assert (workspace / "README.md").is_file()

    reconcile_node(root, workspace, KilnConfig.load(root))

    assert not (root / "README.md").exists()


def test_s5_2_1_reconcile_appends_scaffolder_gitignore(tmp_path: Path) -> None:
    root = _root(tmp_path)
    workspace = _workspace(tmp_path)
    fixture_gitignore = (workspace / ".gitignore").read_text(encoding="utf-8")
    config = KilnConfig.load(root)

    reconcile_node(root, workspace, config)

    body = (root / ".gitignore").read_text(encoding="utf-8")
    for line in fixture_gitignore.splitlines():
        if line.strip():
            assert line in body


def test_s5_3_6_1_reconcile_composes_uv_then_nx_once(tmp_path: Path) -> None:
    root = _root(tmp_path)
    uv_body = (root / ".gitignore").read_text(encoding="utf-8")
    workspace = _workspace(tmp_path)
    nx_body = (workspace / ".gitignore").read_text(encoding="utf-8")

    reconcile_node(root, workspace, KilnConfig.load(root))

    assert uv_body == "## uv ##\n" + UV_FIXTURE.read_text(encoding="utf-8")
    assert (root / ".gitignore").read_text(encoding="utf-8") == (
        uv_body + "\n## nx ##\n" + nx_body.rstrip("\n") + "\n"
    )


def test_s5_2_1_reconcile_renames_web_dir_and_rewrites_project_json(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, extra='web_dir = "apps/frontend"')
    workspace = _workspace(tmp_path)
    config = KilnConfig.load(root)

    reconcile_node(root, workspace, config)

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
        reconcile_node(root, workspace, config)


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
            scaffold_node(root, config)

    run.assert_not_called()


def test_s5_2_4_frontend_module_owns_the_frontend_option() -> None:
    registry = builtin()
    owners = [
        m.name
        for m in registry.modules
        if any(o.flag == "frontend" for o in m.options())
    ]
    assert owners == ["node"]


def test_s4_5_9_reconcile_node_leaves_the_raw_tree_untouched(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, extra='web_dir = "apps/frontend"')
    workspace = _workspace(tmp_path)
    before = {p: p.read_bytes() for p in sorted(workspace.rglob("*")) if p.is_file()}
    config = KilnConfig.load(root)

    reconcile_node(root, workspace, config)

    after = {p: p.read_bytes() for p in sorted(workspace.rglob("*")) if p.is_file()}
    assert before == after
    assert (root / "apps" / "frontend" / "project.json").is_file()


LIB_CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "node-lib"

[docs]
profile = "mkdocs"
"""


def _lib_root(tmp_path: Path) -> Path:
    """A root with the `python`/uv side of a `node-lib` scaffold done."""
    root = tmp_path / "root"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(LIB_CONFIG, encoding="utf-8")
    scaffold(root, KilnConfig.load(root))
    return root


def test_s9_1_8_1_node_lib_is_shipped_and_loads() -> None:
    assert "node-lib" in archetypes.shipped()
    manifest = archetypes.load("node-lib")
    assert manifest.name == "node-lib"
    assert manifest.dependencies.required == []
    assert manifest.dependencies.allowed == []
    assert manifest.modules == [
        "core",
        "python",
        "node",
        "docs",
        "tasks",
        "cicd",
        "instructions",
    ]


def _scaffold_calls(root: Path, raw: Path) -> tuple[Path | None, list[mock.call]]:
    (raw / "workspace").mkdir()
    (raw / "workspace" / "package.json").write_text("{}\n", encoding="utf-8")
    with mock.patch("rn_forge.kiln.modules.node.angular.Process.execute") as run:
        workspace = scaffold_node(raw, KilnConfig.load(root))
    return workspace, run.call_args_list


_SHARED_STEPS = [
    "nx-git-boundary",
    "nx-workspace",
    "nx-angular-plugin",
    "nx-angular-app",
    "nx-install",
]


def test_s9_2_2_1_node_lib_scaffolds_the_app_then_removes_it(tmp_path: Path) -> None:
    root = _lib_root(tmp_path)
    raw = tmp_path / "frontend"
    raw.mkdir()

    workspace, calls = _scaffold_calls(root, raw)

    assert workspace == raw / "workspace"
    assert [c.args[0] for c in calls] == [*_SHARED_STEPS, "nx-remove-app"]


def test_s9_2_2_2_web_app_adds_ngkit_after_install_and_keeps_the_app(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    raw = tmp_path / "frontend"
    raw.mkdir()

    _, calls = _scaffold_calls(root, raw)

    assert [c.args[0] for c in calls] == [*_SHARED_STEPS, "ngkit-core"]


def test_s9_2_2_3_nx_remove_app_removes_web_in_the_workspace(tmp_path: Path) -> None:
    root = _lib_root(tmp_path)
    raw = tmp_path / "frontend"
    raw.mkdir()

    workspace, calls = _scaffold_calls(root, raw)

    remove = calls[-1]
    assert remove.args == (
        "nx-remove-app",
        "pnpm",
        "nx",
        "g",
        "@nx/workspace:remove",
        "web",
        "--forceRemove",
        "--interactive=false",
    )
    assert remove.kwargs["cwd"] == str(workspace)


def test_s9_2_2_4_python_web_api_has_no_node_scaffold(tmp_path: Path) -> None:
    root = tmp_path / "root"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        'schema_version = 1\n\n[repository]\nname = "demo"\n'
        'archetype = "python-web-api"\n\n[archetype."python-web-api"]\n'
        'backend = "fastapi"\n',
        encoding="utf-8",
    )
    raw = tmp_path / "frontend"
    raw.mkdir()

    workspace, calls = _scaffold_calls(root, raw)

    assert workspace is None
    assert calls == []


def _reconciled(tmp_path: Path, *, lib: bool) -> tuple[Path, KilnConfig]:
    root = _lib_root(tmp_path) if lib else _root(tmp_path)
    workspace = _workspace(tmp_path)
    if lib:
        shutil.rmtree(workspace / "apps")
    config = KilnConfig.load(root)
    reconcile_node(root, workspace, config)
    return root, config


@pytest.mark.parametrize("lib", [True, False])
def test_s9_2_3_1_reconcile_node_writes_nvmrc_for_both(
    tmp_path: Path, lib: bool
) -> None:
    root, _ = _reconciled(tmp_path, lib=lib)

    assert (root / ".nvmrc").read_text(encoding="utf-8") == "24\n"


@pytest.mark.parametrize("lib", [True, False])
def test_s9_2_3_2_reconcile_node_pins_pnpm_in_package_json(
    tmp_path: Path, lib: bool
) -> None:
    root, _ = _reconciled(tmp_path, lib=lib)

    package = DocumentUtils.read(root / "package.json")
    assert package["packageManager"] == "pnpm@12.15.0"
    assert package["name"] == "@workspace/source"


@pytest.mark.parametrize("lib", [True, False])
def test_s9_2_3_3_neither_pin_is_a_managed_artifact(tmp_path: Path, lib: bool) -> None:
    _, config = _reconciled(tmp_path, lib=lib)

    keys = [a.key for a in render(config)]
    assert not any(k.endswith((".nvmrc", "package.json")) for k in keys)


@pytest.mark.parametrize("lib", [True, False])
def test_s9_2_3_4_scaffold_node_pins_pnpm_before_the_last_lockfile_write(
    tmp_path: Path, lib: bool
) -> None:
    root = _lib_root(tmp_path) if lib else _root(tmp_path)
    raw = tmp_path / "frontend"
    raw.mkdir()
    workspace = raw / "workspace"
    seen: dict[str, object] = {}

    def run(name: str, *args: str, **kwargs: object) -> None:
        if name in ("nx-remove-app", "ngkit-core"):
            seen["package"] = DocumentUtils.read(workspace / "package.json")

    workspace.mkdir()
    (workspace / "package.json").write_text("{}\n", encoding="utf-8")
    with mock.patch(
        "rn_forge.kiln.modules.node.angular.Process.execute", side_effect=run
    ):
        scaffold_node(raw, KilnConfig.load(root))

    assert seen["package"] == {"packageManager": "pnpm@12.15.0"}


def test_s9_1_8_3_reconcile_node_folds_the_workspace_and_writes_nvmrc(
    tmp_path: Path,
) -> None:
    root = _lib_root(tmp_path)
    workspace = _workspace(tmp_path)
    shutil.rmtree(workspace / "apps")
    config = KilnConfig.load(root)

    reconcile_node(root, workspace, config)

    assert (root / "nx.json").is_file()
    assert not (root / "workspace").exists()
    assert not (root / "apps").exists()
    assert (root / ".nvmrc").read_text(encoding="utf-8") == "24\n"
    assert not any(a.key.endswith(".nvmrc") for a in render(config))


def test_s9_1_8_3_reconcile_node_writes_no_angular_starter(tmp_path: Path) -> None:
    root = _lib_root(tmp_path)
    workspace = _workspace(tmp_path)
    config = KilnConfig.load(root)
    project = workspace / "apps" / "web" / "project.json"
    before = project.read_bytes()

    reconcile_node(root, workspace, config)

    assert not (root / "apps" / "web" / "proxy.conf.json").exists()
    assert (root / "apps" / "web" / "project.json").read_bytes() == before


def test_s9_1_8_4_root_pyproject_is_bare_with_docs_tooling(tmp_path: Path) -> None:
    root = _lib_root(tmp_path)
    config = KilnConfig.load(root)

    document = DocumentUtils.read(root / "pyproject.toml")
    assert "build-system" not in document
    assert not (root / "src").exists()
    assert not (root / "tests").exists()
    assert not (root / ".importlinter").exists()
    assert "mkdocs-material>=9.6" in document["dependency-groups"]["docs"]
    assert add_task_tools(root, config) == []
    assert "mdformat" in " ".join(document["dependency-groups"]["docs"])
