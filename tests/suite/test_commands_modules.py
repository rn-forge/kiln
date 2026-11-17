"""S18.6.2 — one module per command."""

from __future__ import annotations

import ast
import importlib
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KILN = ROOT / "src" / "rn_forge" / "kiln"
PACKAGE = "rn_forge.kiln.commands"


def test_s18_6_2_1_every_cli_target_resolves_to_a_command_module() -> None:
    document = tomllib.loads((KILN / "cli.toml").read_text(encoding="utf-8"))
    targets = [command["target"] for command in document["cli"]["commands"]]
    assert targets
    for target in targets:
        module_name, _, name = target.partition(":")
        assert module_name.startswith(f"{PACKAGE}.")
        assert module_name != PACKAGE
        assert hasattr(importlib.import_module(module_name), name)


def _command_imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names if a.name.startswith(f"{PACKAGE}."))
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == PACKAGE:
                found.update(f"{PACKAGE}.{a.name}" for a in node.names)
            elif node.module.startswith(f"{PACKAGE}."):
                found.add(node.module)
    return found


def test_s18_6_2_2_command_modules_import_no_other_command_module() -> None:
    for path in sorted((KILN / "commands").glob("*.py")):
        if path.name == "__init__.py":
            continue
        allowed = {f"{PACKAGE}.output"}
        if path.name == "new.py":
            allowed.add(f"{PACKAGE}.generate")
        assert _command_imports(path) - allowed == set(), path.name


def test_s18_6_2_3_the_old_modules_are_gone_and_none_is_large() -> None:
    assert not (KILN / "commands.py").exists()
    assert not (KILN / "doctor.py").exists()
    for path in sorted((KILN / "commands").glob("*.py")):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 350, path.name


def test_s18_6_3_1_commands_import_neither_subprocess_nor_state_store() -> None:
    for path in sorted((KILN / "commands").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                assert "subprocess" not in {a.name for a in node.names}, path.name
            elif isinstance(node, ast.ImportFrom):
                assert "StateStore" not in {a.name for a in node.names}, path.name
