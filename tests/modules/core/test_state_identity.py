"""State file identity is declared once, in `umbrella` (S18.7.2)."""

from __future__ import annotations

import ast
from pathlib import Path

from rn_forge.kiln.modules.core import umbrella

SRC = Path(__file__).resolve().parents[3] / "src" / "rn_forge" / "kiln"
CORE = SRC / "modules" / "core"


def _docstring_nodes(tree: ast.AST) -> set[int]:
    # A bare string statement is a docstring, attribute docstrings included.
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }


def test_s18_7_2_1_state_json_is_named_once() -> None:
    found: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docs = _docstring_nodes(tree)
        found.extend(
            f"{path.relative_to(SRC).as_posix()}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "state.json" in node.value
            and id(node) not in docs
        )
    assert len(found) == 1, found
    assert found[0].startswith("modules/core/umbrella.py:"), found


def test_s18_7_2_2_one_state_schema_version() -> None:
    assert umbrella.STATE_SCHEMA_VERSION == "1"
    for path in (CORE / "cycle.py", CORE / "checks" / "generated.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            assert not line.startswith(
                ("STATE_SCHEMA_VERSION =", "SCHEMA_VERSION =")
            ), path
