"""S18.5.1 — tests reach `commands` only through its public names."""

from __future__ import annotations

import ast
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
THIS = Path(__file__).resolve()

# The patterns are built from pieces so that this file does not match itself.
PRIVATE = re.compile("commands" + r"\._[A-Za-z]")
PATCH = re.compile(r"monkeypatch\.setattr\(\s*" + "commands")

# `commands.py` binds the scaffold steps with `from ... import`, so a patch at
# the definition does not reach `new`. S18.6.2 moves these and empties this
# list. The same goes for the private names no test can reach through
# `commands.new` or `commands.apply`.
ALLOWED = frozenset[str](
    {
        "tests/modules/core/test_catalog.py::_written",
        "tests/test_doctor.py::test_s4_12_5_3_apply_does_not_fail_on_them",
        "tests/test_new.py::_commented_form",
        "tests/test_new.py::test_s16_7_3_8_new_formats_after_apply",
        "tests/test_new.py::test_s16_7_10_5_a_failing_member_step_leaves_no_directory",
        "tests/test_new.py::test_s4_5_11_3_failure_or_refusal_creates_no_git",
        "tests/test_new.py::test_s4_5_1_flags_match_module_union",
        "tests/test_new.py::test_s4_5_1_untested_flag_value_is_refused_without_allow_untested",
        "tests/test_new.py::test_s4_5_9_4_failure_retains_staging_and_writes_no_target",
        "tests/test_new.py::test_s4_5_9_6_no_retention_or_cleanup_flag_and_no_rnf_home",
        "tests/test_new.py::test_s5_3_1_explicit_selectors_override_web_defaults",
        "tests/test_new.py::test_s5_3_1_web_defaults_select_fastapi",
    }
)


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
