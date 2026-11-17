"""Tests are named for the behaviour they prove, with no spec ID in prose."""

from __future__ import annotations

import ast
import io
import re
import tokenize
from pathlib import Path

TESTS = Path(__file__).parents[1]
STORY_NAMED = re.compile(r"^test_s[0-9]+_")
SPEC_ID = re.compile(r"\b(F[0-9]+\.[0-9]+|S[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)*)\b")


def _python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def story_named_tests(root: Path) -> list[str]:
    offenders: list[str] = []
    for path in _python_files(root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(
                node, ast.FunctionDef | ast.AsyncFunctionDef
            ) and STORY_NAMED.match(node.name):
                offenders.append(f"{path.relative_to(root).as_posix()}::{node.name}")
    return offenders


def spec_ids_in_prose(root: Path) -> list[str]:
    offenders: list[str] = []
    for path in _python_files(root):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        lines: set[int] = set()
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(
                node,
                ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
            ):
                doc = ast.get_docstring(node, clean=False)
                if doc is not None and SPEC_ID.search(doc):
                    # The docstring is the first statement of the body.
                    first = node.body[0]
                    start = first.lineno
                    for offset, line in enumerate(doc.splitlines()):
                        if SPEC_ID.search(line):
                            lines.add(start + offset)
                            break
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT and SPEC_ID.search(token.string):
                lines.add(token.start[0])
        offenders.extend(f"{rel}:{line}" for line in sorted(lines))
    return offenders


def test_a_story_named_test_is_reported(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "test_x.py").write_text(
        # Split so a source search for story-named tests does not match.
        "def "
        "test_s1_2_3_thing(): ...\n"
        "def test_thing_works(): ...\n"
        "class TestY:\n"
        "    def "
        "test_s4_5_y(self): ...\n",
        encoding="utf-8",
    )
    assert story_named_tests(tmp_path) == [
        "a/test_x.py::test_s1_2_3_thing",
        "a/test_x.py::test_s4_5_y",
    ]


def test_a_spec_id_in_a_docstring_or_comment_is_reported(tmp_path: Path) -> None:
    (tmp_path / "test_x.py").write_text(
        '"""S1.2.3 — x."""\n'
        "x = 1  # since F4.5\n"
        "y = 2  # noqa: E731\n"
        'z = "specs/epics/E1-x/F1.1-a.md"\n',
        encoding="utf-8",
    )
    assert spec_ids_in_prose(tmp_path) == ["test_x.py:1", "test_x.py:2"]


def test_no_test_is_named_after_a_story() -> None:
    offenders = story_named_tests(TESTS)
    assert offenders == [], (
        "tests are named for the behaviour they prove, "
        f"test_<subject>_<behaviour>, with no spec ID: {offenders}"
    )


def test_no_test_prose_carries_a_spec_id() -> None:
    offenders = spec_ids_in_prose(TESTS)
    assert offenders == [], (
        f"test docstrings and comments carry no feature or story ID: {offenders}"
    )
