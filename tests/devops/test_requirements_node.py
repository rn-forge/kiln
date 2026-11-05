"""Tests for the `requirements --stack node` check."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from rn_forge.kiln.devops import cli, requirements


def _workspace(root: Path, **fields: dict[str, str]) -> list[dict[str, str]]:
    """Write members @s/a (with `fields`), @s/b and @s/c; return the `pnpm ls` JSON."""
    members = []
    for name, extra in (("a", fields), ("b", {}), ("c", {})):
        path = root / name
        path.mkdir()
        manifest = {"name": f"@s/{name}", "version": "1.0.0", **extra}
        (path / "package.json").write_text(json.dumps(manifest))
        members.append({"name": f"@s/{name}", "version": "1.0.0", "path": str(path)})
    return members


def _stdin(monkeypatch: pytest.MonkeyPatch, members: list[dict[str, str]]) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(members)))


def test_s15_4_3_1_caret_and_tilde_pass(tmp_path: Path) -> None:
    deps = {"@s/b": "workspace:^", "@s/c": "workspace:~"}
    assert requirements.check_node(_workspace(tmp_path, dependencies=deps)) == []


def test_s15_4_3_2_star_fails(tmp_path: Path) -> None:
    members = _workspace(tmp_path, dependencies={"@s/b": "workspace:*"})
    assert requirements.check_node(members) == [
        "@s/a -> @s/b: workspace:* publishes as an exact pin"
    ]


@pytest.mark.parametrize("spec", ["^1.0.0", "workspace:1.0.0"])
def test_s15_4_3_3_literal_version_fails(tmp_path: Path, spec: str) -> None:
    members = _workspace(tmp_path, dependencies={"@s/b": spec})
    assert requirements.check_node(members) == [
        f"@s/a -> @s/b: use workspace:^ or workspace:~, found {spec}"
    ]


def test_s15_4_3_4_fields(tmp_path: Path) -> None:
    members = _workspace(
        tmp_path,
        dependencies={"@s/b": "^1"},
        peerDependencies={"@s/b": "^1"},
        optionalDependencies={"@s/c": "^1"},
        devDependencies={"@s/c": "workspace:*"},
    )
    assert len(requirements.check_node(members)) == 3


def test_s15_4_3_5_non_members_ignored(tmp_path: Path) -> None:
    members = _workspace(tmp_path, dependencies={"rxjs": "^7"})
    assert requirements.check_node(members) == []


def test_s15_4_3_6_one_member(tmp_path: Path) -> None:
    members = _workspace(tmp_path, dependencies={"rxjs": "^7"})[:1]
    assert requirements.check_node(members) == []


def test_s15_4_3_7_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "g").mkdir()
    good = _workspace(tmp_path / "g", dependencies={"@s/b": "workspace:^"})
    _stdin(monkeypatch, good)
    assert cli.main(["requirements", "--stack", "node"]) == 0
    assert capsys.readouterr().out == ""
    (tmp_path / "x").mkdir()
    bad = _workspace(tmp_path / "x", dependencies={"@s/b": "workspace:*"})
    _stdin(monkeypatch, bad)
    assert cli.main(["requirements", "--stack", "node"]) == 1
    assert "workspace:* publishes as an exact pin" in capsys.readouterr().out
