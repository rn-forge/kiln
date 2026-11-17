"""S18.5.1 — tests reach `commands` only through its public names."""

from __future__ import annotations

import ast
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]
THIS = Path(__file__).resolve()

# The patterns are built from pieces so that this file does not match itself.
PRIVATE = re.compile("commands" + r"\._[A-Za-z]")
PATCH = re.compile(r"monkeypatch\.setattr\(\s*" + "commands")

# Tests patch a scaffold step at its definition module, so this list stays empty.
ALLOWED = frozenset[str]()


def _enclosing(tree: ast.Module, line: int) -> str:
    """The outermost function holding *line*, or `<module>`."""
    holders = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.lineno <= line <= (node.end_lineno or node.lineno)
    ]
    return min(holders, key=lambda node: node.lineno).name if holders else "<module>"


def _offences() -> set[str]:
    found: set[str] = set()
    for path in sorted(TESTS.rglob("*.py")):
        if path == THIS or "fixtures" in path.relative_to(TESTS).parts:
            continue
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        relative = path.relative_to(TESTS.parent).as_posix()
        for pattern in (PRIVATE, PATCH):
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                found.add(f"{relative}::{_enclosing(tree, line)}")
    return found


def test_s18_5_1_1_tests_use_only_public_commands_names() -> None:
    assert _offences() - ALLOWED == set()
