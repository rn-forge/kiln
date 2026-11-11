"""The test session must not inherit CI's UV_LOCKED."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest


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


@pytest.mark.skipif(
    shutil.which("pnpm") is None and not os.environ.get("CI"),
    reason="pnpm is not on PATH",
)
def test_s17_3_2_4_nx_archetypes_use_the_shared_build(rendered) -> None:
    assert "shared" in rendered("node-lib").parts
    assert "shared" in rendered("python-web-app").parts
