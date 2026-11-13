"""Tests for the uv workspace adapter's manifest reading."""

from __future__ import annotations

import re
import subprocess
import zipfile
from pathlib import Path

import pytest

from rn_forge.kiln.devops import Package, Service, Smoke, Workspace, uv
from rn_forge.kiln.devops.ci import plan, select


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _workspace(root: Path) -> None:
    _write(
        root / "pyproject.toml",
        '[tool.uv.workspace]\nmembers = ["pkgs/*"]\n\n'
        '[tool.workspace-ci]\npytest-args = ["-m", "not slow"]\n',
    )
    _write(
        root / "pkgs/base/pyproject.toml", '[project]\nname = "base"\nversion = "1"\n'
    )
    _write(
        root / "pkgs/app/pyproject.toml",
        '[project]\nname = "App_X"\nversion = "1"\ndependencies = ["base>=1"]\n\n'
        '[tool.workspace-ci.integration.postgres]\nimage = "postgres:17"\n'
        'ports = ["5432:5432"]\nhealth-cmd = "pg_isready -U ci"\n\n'
        '[tool.workspace-ci.integration.postgres.env]\nPOSTGRES_USER = "ci"\n\n'
        "[tool.workspace-ci.integration.postgres.expose]\n"
        'DATABASE_URL = "postgresql://ci@localhost:5432/ci"\n\n'
        '[tool.workspace-ci.integration.redis]\nimage = "redis:7"\n',
    )


def test_s15_8_2_1_load(tmp_path: Path) -> None:
    _workspace(tmp_path)
    packages = uv.load_workspace(tmp_path).packages
    assert packages["base"].services == ()
    assert packages["app-x"].services == (
        Service(
            "postgres",
            "postgres:17",
            ports=("5432:5432",),
            health_cmd="pg_isready -U ci",
            env={"POSTGRES_USER": "ci"},
            expose={"DATABASE_URL": "postgresql://ci@localhost:5432/ci"},
        ),
        Service("redis", "redis:7"),
    )
    assert packages["app-x"].release_requires == {"base"}


def test_s15_8_2_1_image_is_required(tmp_path: Path) -> None:
    _workspace(tmp_path)
    _write(
        tmp_path / "pkgs/base/pyproject.toml",
        '[project]\nname = "base"\nversion = "1"\n\n'
        '[tool.workspace-ci.integration.redis]\nports = ["6379:6379"]\n',
    )
    with pytest.raises(ValueError, match="integration.redis.*image"):
        uv.load_workspace(tmp_path)


@pytest.mark.parametrize("old", ["postgres", "redis"])
def test_s15_8_2_4_old_table_is_refused(tmp_path: Path, old: str) -> None:
    _workspace(tmp_path)
    _write(
        tmp_path / "pkgs/base/pyproject.toml",
        f'[project]\nname = "base"\nversion = "1"\n\n'
        f'[tool.workspace-ci.{old}]\nenv = "X"\n',
    )
    with pytest.raises(
        ValueError,
        match=re.escape(
            f"[tool.workspace-ci.{old}] was replaced by "
            f"[tool.workspace-ci.integration.{old}]"
        ),
    ):
        uv.load_workspace(tmp_path)


def test_s6_8_1_9_load_workspace_keeps_dependency_groups_out_of_release_requires(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path)
    _write(
        tmp_path / "pkgs/base/pyproject.toml",
        '[project]\nname = "base"\nversion = "1"\n\n'
        '[dependency-groups]\ndev = ["App_X>=1"]\n',
    )
    packages = uv.load_workspace(tmp_path).packages
    assert (packages["base"].requires, packages["base"].release_requires) == (
        {"app-x"},
        set(),
    )


def test_s6_7_2_find_root_walks_up_from_a_subdirectory(tmp_path: Path) -> None:
    _workspace(tmp_path)
    assert uv.find_root(tmp_path / "pkgs" / "app") == tmp_path


def test_s6_7_2_find_root_fails_outside_a_workspace(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        uv.find_root(tmp_path)


def test_s6_7_2_load_workspace_reads_members_and_settings(tmp_path: Path) -> None:
    _workspace(tmp_path)
    workspace = uv.load_workspace(tmp_path)
    assert sorted(workspace.packages) == ["app-x", "base"]
    app = workspace.packages["app-x"]
    assert (app.dir, app.module, app.requires) == ("pkgs/app", "app_x", {"base"})
    assert [s.name for s in app.services] == ["postgres", "redis"]
    assert workspace.pytest_args == ["-m", "not slow"]


def _adapter_member(root: Path, adapters: str, extras: str, files: list[str]) -> None:
    _write(
        root / "pyproject.toml",
        '[tool.uv.workspace]\nmembers = ["pkgs/*"]\n',
    )
    _write(
        root / "pkgs/data/pyproject.toml",
        '[project]\nname = "data"\nversion = "1"\n\n'
        f"[project.optional-dependencies]\n{extras}\n\n"
        f"[tool.workspace-ci]\n{adapters}\n",
    )
    for file in files:
        _write(root / "pkgs/data/src/data" / file, "")


def test_s6_7_2_check_adapters_passes_for_modules_and_subpackages(
    tmp_path: Path,
) -> None:
    _adapter_member(
        tmp_path,
        'adapters = ["pandas", "oidc"]',
        "pandas = []\noidc = []",
        ["pandas.py", "oidc/__init__.py", "core.py"],
    )
    assert uv.check_adapters(uv.load_workspace(tmp_path)) == []


def test_s6_7_2_check_adapters_reports_a_missing_module(tmp_path: Path) -> None:
    _adapter_member(tmp_path, 'adapters = ["pandas"]', "pandas = []", ["core.py"])
    assert uv.check_adapters(uv.load_workspace(tmp_path)) == [
        "data: adapter pandas has no module pandas"
    ]


def test_s6_7_2_check_adapters_reports_a_missing_extra(tmp_path: Path) -> None:
    _adapter_member(tmp_path, 'adapters = ["pandas"]', "excel = []", ["pandas.py"])
    assert uv.check_adapters(uv.load_workspace(tmp_path)) == [
        "data: adapter pandas has no extra pandas"
    ]


def test_s6_7_2_check_adapters_reports_a_duplicate(tmp_path: Path) -> None:
    _adapter_member(
        tmp_path, 'adapters = ["pandas", "pandas"]', "pandas = []", ["pandas.py"]
    )
    assert uv.check_adapters(uv.load_workspace(tmp_path)) == [
        "data: adapter pandas is declared twice"
    ]


def test_s6_7_2_check_adapters_skips_a_member_without_the_key(tmp_path: Path) -> None:
    _workspace(tmp_path)
    assert uv.check_adapters(uv.load_workspace(tmp_path)) == []


def _stub_uv(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Replace `subprocess.run` so `uv build` writes a wheel and nothing else runs."""
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[:2] == ["uv", "build"]:
            name = command[command.index("--package") + 1]
            out = Path(command[command.index("--out-dir") + 1])
            out.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(out / f"{name}-1-py3-none-any.whl", "w") as wheel:
                wheel.writestr(f"{name}-1.dist-info/METADATA", f"Name: {name}\n")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(uv.subprocess, "run", run)
    return calls


def test_s6_7_2_smoke_without_a_declaration_imports_the_package_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _stub_uv(monkeypatch)
    package = Package("app", "pkgs/app", "app_core")
    workspace = Workspace(root=tmp_path, packages={"app": package})
    assert uv.smoke(workspace, "app", "") == 0
    builds = [c for c in calls if c[:2] == ["uv", "build"]]
    assert [c[c.index("--package") + 1] for c in builds] == ["app"]
    assert any("--no-deps" in c for c in calls)
    assert calls[-1][-1] == "app_core"
    assert calls[-1][-2] == ""


def test_s6_7_2_smoke_with_a_declaration_imports_its_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _stub_uv(monkeypatch)
    package = Package("app", "pkgs/app", "app", smoke=Smoke(modules=["app.core"]))
    workspace = Workspace(root=tmp_path, packages={"app": package})
    assert uv.smoke(workspace, "app", "") == 0
    assert calls[-1][-1] == "app.core"


def _single(root: Path) -> None:
    _write(
        root / "pyproject.toml",
        '[project]\nname = "My_Tool"\nversion = "1"\n\n'
        '[tool.workspace-ci.integration.redis]\nimage = "redis:7"\n',
    )
    _write(root / "src/my_tool/__init__.py", "")


def test_s15_8_3_1_root_is_the_member(tmp_path: Path) -> None:
    _single(tmp_path)
    assert uv.find_root(tmp_path / "src") == tmp_path
    packages = uv.load_workspace(tmp_path).packages
    assert list(packages) == ["my-tool"]
    assert (packages["my-tool"].dir, packages["my-tool"].module) == (".", "my_tool")
    assert [s.name for s in packages["my-tool"].services] == ["redis"]


def test_s15_8_3_1_declared_module_name_wins(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "ns-pkg"\nversion = "1"\n\n'
        '[tool.uv.build-backend]\nmodule-name = "ns.pkg"\n',
    )
    assert uv.load_workspace(tmp_path).packages["ns-pkg"].module == "ns.pkg"


def test_s15_8_3_2_plan_of_one(tmp_path: Path) -> None:
    _single(tmp_path)
    run = lambda *args: subprocess.run(  # noqa: E731
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=tmp_path, check=True, capture_output=True,
    )  # fmt: skip
    run("init", "-q", "-b", "main")
    run("add", ".")
    run("commit", "-q", "-m", "one")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path, check=True, capture_output=True, text=True,
    ).stdout.strip()  # fmt: skip
    workspace = uv.load_workspace(tmp_path)

    _write(tmp_path / "docs/index.md", "x")
    run("add", ".")
    run("commit", "-q", "-m", "docs")
    assert select(workspace, base) == set()

    _write(tmp_path / "src/my_tool/more.py", "x = 1")
    run("add", ".")
    run("commit", "-q", "-m", "src")
    assert select(workspace, base) == {"my-tool"}
    assert select(workspace, "") == {"my-tool"}
    outputs = plan(workspace, base)
    assert outputs["integration"] == [
        {
            "name": "my-tool",
            "dir": ".",
            "services": ["redis"],
            "marker": "my-tool.integration",
        }
    ]


def test_s16_6_5_1_load(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        '[tool.uv.workspace]\nmembers = ["pkgs/*"]\n',
    )
    _write(
        tmp_path / "pkgs/app/pyproject.toml",
        '[project]\nname = "app"\nversion = "1"\n\n'
        '[tool.workspace-ci.integration.kc]\nimage = "kc:1"\n'
        'command = ["start-dev", "--import-realm"]\n'
        'volumes = ["realms:/data:ro"]\npytest-args = ["-m", "broker"]\n\n'
        '[tool.workspace-ci.integration.plain]\nimage = "redis:7"\n',
    )
    kc, plain = uv.load_workspace(tmp_path).packages["app"].services
    assert kc.command == ("start-dev", "--import-realm")
    assert kc.volumes == ("realms:/data:ro",)
    assert kc.pytest_args == ("-m", "broker")
    assert (plain.command, plain.volumes, plain.pytest_args) == ((), (), ())
