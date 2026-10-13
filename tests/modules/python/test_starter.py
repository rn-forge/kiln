"""S4.9.1 — the `python` module's seeded starter source."""

from __future__ import annotations

from pathlib import Path

from rn_forge.tooling.generation import ArtifactKind

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.python import starter

CONFIG = """
schema_version = 1

[repository]
name = "{name}"
archetype = "{archetype}"
"""

LIB_CONFIG = """
schema_version = 1

[repository]
name = "demo-lib"
archetype = "python-lib"

[archetype."python-lib"]
packages = {packages}
"""

TOOL_PATHS = {
    "src/python_tool/main.py",
    "src/python_tool/commands.py",
    "src/python_tool/product.py",
    "tests/test_cli.py",
    "tests/test_product.py",
}


def _config(root: Path, text: str) -> KilnConfig:
    path = root / ".rn-forge" / "kiln" / "config.toml"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    return KilnConfig.load(root)


def _fresh(root: Path, package: str, *names: str) -> None:
    directory = root / "src" / package
    directory.mkdir(parents=True)
    for name in ("__init__.py", *names):
        (directory / name).write_text("", encoding="utf-8")


def _tool(root: Path, archetype: str = "python-tool") -> KilnConfig:
    return _config(root, CONFIG.format(name="python-tool", archetype=archetype))


def test_s4_9_1_1_tool_starter_artifacts(tmp_path: Path) -> None:
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


def test_s4_9_1_2_app_starter_has_no_product(tmp_path: Path) -> None:
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


def test_s4_9_1_3_lib_starter_is_per_package(tmp_path: Path) -> None:
    config = _config(tmp_path, LIB_CONFIG.format(packages='["packages/alpha-lib"]'))
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
    assert starter.render(_config(empty, LIB_CONFIG.format(packages="[]")), empty) == []


def test_s4_9_1_4_gate(tmp_path: Path) -> None:
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
