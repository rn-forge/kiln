"""The `python` module's seeded starter source."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest
from rn_forge.commons.generation import Artifact, ArtifactKind

from tests.conftest import new_repo, write_config

from rn_forge.kiln import commands
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.base import StarterModule
from rn_forge.kiln.modules.python import PYTHON, starter
from rn_forge.kiln.modules.core.names import module_name

TOOL_PATHS = {
    "src/python_tool/main.py",
    "src/python_tool/commands.py",
    "src/python_tool/product.py",
    "tests/test_cli.py",
    "tests/test_product.py",
}


def _config(root: Path, archetype: str, **kwargs: Any) -> KilnConfig:
    kwargs.setdefault("name", "demo")
    return KilnConfig.load(write_config(root, archetype, **kwargs))


def _fresh(root: Path, package: str, *names: str) -> None:
    directory = root / "src" / package
    directory.mkdir(parents=True)
    for name in ("__init__.py", *names):
        (directory / name).write_text("", encoding="utf-8")


def _tool(root: Path, archetype: str = "python-tool") -> KilnConfig:
    return _config(root, archetype, name="python-tool")


def test_tool_starter_artifacts(tmp_path: Path) -> None:
    config = _tool(tmp_path)
    _fresh(tmp_path, "python_tool")
    artifacts = starter.render(config, tmp_path)
    assert {a.path for a in artifacts} == TOOL_PATHS
    assert all(a.kind is ArtifactKind.SEEDED for a in artifacts)
    assert all("{{" not in a.content for a in artifacts)
    by_path = {a.path: a.content for a in artifacts}
    assert 'name="python-tool"' in by_path["src/python_tool/product.py"]
    assert "from python_tool.product import PRODUCT" in by_path["tests/test_product.py"]
    assert "from python_tool.main import app" in by_path["tests/test_cli.py"]
    assert "build_tool_app" in by_path["src/python_tool/main.py"]


def test_app_starter_has_no_product(tmp_path: Path) -> None:
    config = _tool(tmp_path, "python-app")
    _fresh(tmp_path, "python_tool")
    artifacts = starter.render(config, tmp_path)
    assert {a.path for a in artifacts} == {
        "src/python_tool/main.py",
        "src/python_tool/commands.py",
        "tests/test_cli.py",
    }
    main = next(a for a in artifacts if a.path.endswith("main.py")).content
    assert "CliApp.from_config" in main
    assert "rn_forge.tooling" not in main


def test_lib_starter_is_per_package(tmp_path: Path) -> None:
    config = _lib(tmp_path, ["packages/alpha-lib"])
    member = tmp_path / "packages" / "alpha-lib" / "src" / "alpha_lib"
    member.mkdir(parents=True)
    (member / "__init__.py").write_text("", encoding="utf-8")
    artifacts = starter.render(config, tmp_path)
    assert {a.path for a in artifacts} == {
        "packages/alpha-lib/src/alpha_lib/settings.py",
        "packages/alpha-lib/tests/test_settings.py",
    }
    assert all(a.kind is ArtifactKind.SEEDED for a in artifacts)
    tests = next(a for a in artifacts if a.path.endswith("test_settings.py"))
    assert "from alpha_lib.settings import" in tests.content

    empty = tmp_path / "empty"
    empty.mkdir()
    assert starter.render(_lib(empty, []), empty) == []


def test_tool_starter_renders_only_into_a_fresh_package(tmp_path: Path) -> None:
    config = _tool(tmp_path)
    assert starter.render(config, tmp_path) == []

    _fresh(tmp_path, "python_tool", "service.py")
    assert starter.render(config, tmp_path) == []

    package = tmp_path / "src" / "python_tool"
    (package / "service.py").unlink()
    assert len(starter.render(config, tmp_path)) == 5

    for name in ("main.py", "commands.py", "product.py"):
        (package / name).write_text("", encoding="utf-8")
    assert len(starter.render(config, tmp_path)) == 5

    assert starter.seedable(package, ["main.py", "commands.py", "product.py"])
    assert not starter.seedable(package, ["main.py"])
    assert not starter.seedable(tmp_path / "missing", [])


def _lib(root: Path, packages: list[str], **kwargs: Any) -> KilnConfig:
    kwargs.setdefault("name", "demo-lib")
    return _config(root, "python-lib", packages=packages, **kwargs)


def _web(
    root: Path, archetype: str, backend: str = "fastapi", extra: str = ""
) -> KilnConfig:
    return _config(root, archetype, backend=backend, tail=extra)


def _fresh_api(root: Path, api_dir: str, *names: str, module: str = "demo_api") -> None:
    directory = root / api_dir / "src" / module
    directory.mkdir(parents=True)
    for name in ("__init__.py", *names):
        (directory / name).write_text("", encoding="utf-8")


def _api_paths(api_dir: str) -> set[str]:
    return {
        f"{api_dir}/src/demo_api/app.py",
        f"{api_dir}/src/demo_api/errors.py",
        f"{api_dir}/src/demo_api/routes.py",
        f"{api_dir}/tests/test_app.py",
    }


def test_fastapi_starter_artifacts(tmp_path: Path) -> None:
    api = tmp_path / "api"
    api.mkdir()
    config = _web(api, "python-web-api")
    _fresh_api(api, "apps/api")
    artifacts = starter.render(config, api)
    assert {a.path for a in artifacts} == _api_paths("apps/api")
    assert all(a.kind is ArtifactKind.SEEDED for a in artifacts)
    assert all("{{" not in a.content for a in artifacts)
    by_path = {a.path: a.content for a in artifacts}
    assert (
        "from demo_api.routes import router" in by_path["apps/api/src/demo_api/app.py"]
    )
    assert 'title="demo"' in by_path["apps/api/src/demo_api/app.py"]
    assert "from demo_api.app import app" in by_path["apps/api/tests/test_app.py"]

    moved = tmp_path / "moved"
    moved.mkdir()
    config = _web(moved, "python-web-app", extra='api_dir = "services/api"')
    _fresh_api(moved, "services/api")
    artifacts = starter.render(config, moved)
    assert {a.path for a in artifacts} == _api_paths("services/api")

    django = tmp_path / "django"
    django.mkdir()
    config = _web(django, "python-web-api", backend="django")
    _fresh_api(django, "apps/api")
    assert starter.render(config, django) == []


def test_web_api_starter_renders_only_into_a_fresh_package(tmp_path: Path) -> None:
    config = _web(tmp_path, "python-web-api")
    assert starter.render(config, tmp_path) == []
    _fresh_api(tmp_path, "apps/api", "other.py")
    package = tmp_path / "apps/api/src/demo_api"
    assert not starter.seedable(package, ["app.py", "errors.py", "routes.py"])
    assert starter.render(config, tmp_path) == []
    (package / "other.py").unlink()
    assert len(starter.render(config, tmp_path)) == 4


def test_httpx_is_a_dev_dependency(tmp_path: Path) -> None:
    from rn_forge.kiln.modules.python import scaffold

    config = _web(tmp_path, "python-web-api")
    raw = tmp_path.parent / f"{tmp_path.name}-raw"
    raw.mkdir()
    scaffold.scaffold_backend(raw, config)
    scaffold.reconcile_backend(raw, tmp_path, config)
    document = tomllib.loads(
        (tmp_path / "apps/api/pyproject.toml").read_text(encoding="utf-8")
    )
    dev = document["dependency-groups"]["dev"]
    assert "uvicorn>=0.30" in dev
    assert "httpx>=0.28.1" in dev
    assert dev.index("httpx>=0.28.1") < dev.index("uvicorn>=0.30")


def test_new_records_seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / "demo"
    new_repo(
        directory, archetype="python-web-api", docs="none", backend="fastapi", yes=True
    )
    entries = json.loads(
        (directory / ".rn-forge" / "kiln" / "state.json").read_text(encoding="utf-8")
    )["entries"]
    for path in _api_paths("apps/api"):
        assert entries[path]["kind"] == "seeded"


LONG_NAME = "-".join(["abcdefg"] * 4) + "-abcdefgh"
assert len(LONG_NAME) == 40


def _assert_formatter_stable(root: Path, artifacts: list[Artifact]) -> None:
    paths: list[str] = []
    for artifact in artifacts:
        if not artifact.path.endswith(".py"):
            continue
        target = root / "out" / artifact.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(artifact.content, encoding="utf-8")
        paths.append(str(target))
    assert paths
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--isolated",
            "--check",
            "--diff",
            *paths,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("name", ["t", "tool", "python-tool", LONG_NAME])
@pytest.mark.parametrize("archetype", ["python-tool", "python-app", "python-lib"])
def test_starter_is_formatter_stable_at_any_name(
    tmp_path: Path, name: str, archetype: str
) -> None:
    if archetype == "python-lib":
        config = _lib(tmp_path, [f"packages/{name}"], name=name)
        _fresh(tmp_path / "packages" / name, module_name(name))
    else:
        config = _config(tmp_path, archetype, name=name)
        _fresh(tmp_path, module_name(name))
    artifacts = starter.render(config, tmp_path)
    assert artifacts
    _assert_formatter_stable(tmp_path, artifacts)


@pytest.mark.parametrize("name", ["demo", LONG_NAME])
def test_web_api_starter_is_formatter_stable(tmp_path: Path, name: str) -> None:
    config = _config(tmp_path, "python-web-api", name=name, backend="fastapi")
    _fresh_api(tmp_path, "apps/api", module=module_name(f"{name}-api"))
    artifacts = starter.render(config, tmp_path)
    assert artifacts
    _assert_formatter_stable(tmp_path, artifacts)


def test_python_starters_are_its_starter_paths(tmp_path: Path) -> None:
    assert isinstance(PYTHON, StarterModule)
    config = _tool(tmp_path)
    _fresh(tmp_path, "python_tool")
    expected = {a.path for a in starter.render(config, tmp_path)}
    assert expected
    assert set(PYTHON.starters(config, tmp_path)) == expected

    (tmp_path / "src" / "python_tool" / "service.py").write_text("", encoding="utf-8")
    assert not PYTHON.starters(config, tmp_path)


def test_starter_flags_seed_cli_and_lifecycle() -> None:
    cli = {
        "name": "demo",
        "help": "The demo command line.",
        "commands": [{"name": "hello", "target": "demo.commands:hello"}],
    }
    assert starter.starter_flags("python-tool", "demo", "demo") == {
        "cli": cli,
        "lifecycle": {"product": "demo.product:PRODUCT"},
    }
    assert starter.starter_flags("python-app", "demo", "demo") == {"cli": cli}
    assert starter.starter_flags("python-lib", "demo", "demo") == {}
