"""The python and node scaffolds do one job per unit."""

from __future__ import annotations

from tests.conftest import SRC, oversized

PYTHON = SRC / "modules" / "python"


def test_no_scaffold_function_is_large() -> None:
    assert oversized("modules/python", "modules/node") == []


def test_the_python_scaffold_is_split() -> None:
    assert (PYTHON / "uv_init.py").is_file()
    assert (PYTHON / "pyproject.py").is_file()
    assert len((PYTHON / "scaffold.py").read_text("utf-8").splitlines()) <= 300
