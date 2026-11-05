"""Tests for the `requirements` check."""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.kiln.devops import cli, requirements


def _workspace(
    root: Path, a_deps: str, b_version: str = "0.3.0", a_extra: str = ""
) -> Path:
    (root / "pyproject.toml").write_text(
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n'
    )
    for name, version, body in (
        ("a", "1.0.0", f"dependencies = [{a_deps}]\n{a_extra}"),
        ("b", b_version, ""),
    ):
        (root / "packages" / name).mkdir(parents=True)
        (root / "packages" / name / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\nversion = "{version}"\n{body}\n'
        )
    return root


def test_s15_4_1_1_range_passes(tmp_path: Path) -> None:
    _workspace(tmp_path, '"b>=0.2,<1"')
    assert requirements.check(tmp_path) == []


def test_s15_4_1_2_no_lower_bound(tmp_path: Path) -> None:
    _workspace(tmp_path, '"b"')
    assert requirements.check(tmp_path) == ["a -> b: no lower bound"]


def test_s15_4_1_3_exact_pin(tmp_path: Path) -> None:
    _workspace(tmp_path, '"b==0.3.0"')
    assert requirements.check(tmp_path) == ["a -> b: exact pin"]


def test_s15_4_1_4_floor_above_current(tmp_path: Path) -> None:
    _workspace(tmp_path, '"b>=0.4"')
    assert requirements.check(tmp_path) == ["a -> b: lower bound 0.4 is above 0.3.0"]


def test_s15_4_1_5_extras_and_optional(tmp_path: Path) -> None:
    _workspace(
        tmp_path,
        '"b[x]>=0.2"',
        a_extra=(
            '[project.optional-dependencies]\nfull = ["b"]\n'
            '[dependency-groups]\ndev = ["b==0.3.0"]\n'
        ),
    )
    assert requirements.check(tmp_path) == ["a -> b: no lower bound"]


def test_s15_4_1_6_non_members_ignored(tmp_path: Path) -> None:
    _workspace(tmp_path, '"requests", "b>=0.2"')
    assert requirements.check(tmp_path) == []


def test_s15_4_1_7_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _workspace(tmp_path, '"b>=0.2,<1"')
    assert cli.main(["requirements", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""
    (tmp_path / "bad").mkdir()
    _workspace(tmp_path / "bad", '"b"')
    assert cli.main(["requirements", "--root", str(tmp_path / "bad")]) == 1
    assert capsys.readouterr().out == "a -> b: no lower bound\n"
