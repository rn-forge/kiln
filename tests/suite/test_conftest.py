"""The test session must not inherit CI's UV_LOCKED."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from tests.conftest import requires


def test_s16_1_5_1_uv_locked_is_not_inherited() -> None:
    assert "UV_LOCKED" not in os.environ
    out = subprocess.run(
        [sys.executable, "-c", "import os; print('UV_LOCKED' in os.environ)"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == "False"


def _cleanup(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
    for suffix in (".done", ".lock"):
        path.with_name(path.name + suffix).unlink(missing_ok=True)


def test_s17_3_2_1_shared_build_builds_once(shared_build) -> None:
    name = f"probe-{uuid.uuid4().hex}"
    calls: list[Path] = []

    def build(path: Path) -> None:
        calls.append(path)
        (path / "x").write_text("x", encoding="utf-8")

    path = shared_build(name, build)
    try:
        assert shared_build(name, build) == path
        assert (path / "x").is_file()
        assert len(calls) == 1
    finally:
        _cleanup(path)


def test_s17_3_2_2_xdist_workers_share_the_parent_basetemp(
    shared_build, tmp_path_factory: pytest.TempPathFactory, monkeypatch
) -> None:
    def build(path: Path) -> None:
        (path / "x").write_text("x", encoding="utf-8")

    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw0")
    first = shared_build(f"probe-{uuid.uuid4().hex}", build)
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    second = shared_build(f"probe-{uuid.uuid4().hex}", build)
    try:
        assert first.parent.parent == tmp_path_factory.getbasetemp().parent
        assert second.parent.parent == tmp_path_factory.getbasetemp()
    finally:
        _cleanup(first)
        _cleanup(second)


def test_s17_3_2_3_only_the_nx_archetypes_are_shared(rendered) -> None:
    assert "shared" not in rendered("python-lib").parts


@requires("pnpm")
def test_s17_3_2_4_nx_archetypes_use_the_shared_build(rendered) -> None:
    assert "shared" in rendered("node-lib").parts
    assert "shared" in rendered("python-web-app").parts


def test_s18_5_3_1_no_unmarked_which_skip() -> None:
    needle = "shutil." + "which("
    tests = Path(__file__).parents[1]
    offenders = [
        str(path.relative_to(tests))
        for path in sorted(tests.rglob("*.py"))
        if "fixtures" not in path.relative_to(tests).parts
        and path.name != "conftest.py"
        and needle in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_s18_5_3_2_requires_marks_and_skips(monkeypatch) -> None:
    missing = requires("kiln-no-such-tool")
    names = [mark.name for mark in missing]
    assert "requires_tool" in names
    skip = next(mark for mark in missing if mark.name == "skipif")
    assert skip.args[0] is True

    monkeypatch.setenv("CI", "1")
    monkeypatch.setattr(shutil, "which", lambda _tool: None)
    pnpm = requires("pnpm")
    assert "requires_pnpm" in [mark.name for mark in pnpm]
    skip = next(mark for mark in pnpm if mark.name == "skipif")
    assert skip.args[0] is False


def _tests_py_files() -> list[Path]:
    tests = Path(__file__).parents[1]
    return [
        path
        for path in sorted(tests.rglob("*.py"))
        if "fixtures" not in path.relative_to(tests).parts
    ]


def test_s18_5_2_1_no_test_loads_another_by_path() -> None:
    needle = "spec_from_file_" + "location"
    tests = Path(__file__).parents[1]
    offenders = [
        str(path.relative_to(tests))
        for path in _tests_py_files()
        if path.name not in ("test_conftest.py", "test_golden_matrix.py")
        and needle in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_s18_5_2_2_check_tests_use_the_registry() -> None:
    call = re.compile(r"\b\w+\.check\(")
    tests = Path(__file__).parents[1]
    offenders = [
        str(path.relative_to(tests))
        for path in sorted((tests / "modules").glob("*/checks/*.py"))
        if path.name != "test_pin.py" and call.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_s18_5_4_1_no_test_file_over_1200_lines() -> None:
    tests = Path(__file__).parents[1]
    offenders = [
        str(path.relative_to(tests))
        for path in _tests_py_files()
        if len(path.read_text(encoding="utf-8").splitlines()) > 1200
    ]
    assert offenders == []


def test_s18_5_4_2_no_story_banners() -> None:
    banner = re.compile(r"^# S\d", re.MULTILINE)
    tests = Path(__file__).parents[1]
    offenders = [
        str(path.relative_to(tests))
        for path in _tests_py_files()
        if banner.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
