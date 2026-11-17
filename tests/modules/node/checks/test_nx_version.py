"""Doctor reports a node-lib behind kiln's Nx."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.conftest import run_check, write_config

from rn_forge.commons.findings import Finding

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.node.angular import NX_VERSION
from rn_forge.kiln.modules.node.checks import nx_version


def _repo(
    tmp_path: Path,
    nx: str | None,
    archetype: str = "node-lib",
    section: str = "devDependencies",
) -> Path:
    write_config(tmp_path, archetype, name="demo")
    package = {"name": "demo", section: {} if nx is None else {"nx": nx}}
    (tmp_path / "package.json").write_text(json.dumps(package), encoding="utf-8")
    return tmp_path


def _findings(root: Path) -> list[Finding]:
    return run_check(nx_version.NAME, root)


def test_behind_is_an_error(tmp_path: Path) -> None:
    (finding,) = _findings(_repo(tmp_path, "23.1.0"))
    assert finding.code == "node.nx-behind"
    assert finding.path == "package.json"
    assert f"pnpm exec nx migrate {NX_VERSION}" in finding.message
    assert "nx 23.1.0 is below" in finding.message


@pytest.mark.parametrize(
    ("nx", "behind"),
    [
        ("^23.1.0", True),
        ("~23.1.0", True),
        (">=23.1.0", True),
        (NX_VERSION, False),
        ("^24.1.0", False),
        ("latest", False),
    ],
)
def test_ranges_are_read(tmp_path: Path, nx: str, behind: bool) -> None:
    assert bool(_findings(_repo(tmp_path, nx))) is behind


def test_dependencies_are_read_too(tmp_path: Path) -> None:
    root = _repo(tmp_path, "23.1.0", section="dependencies")
    assert [f.code for f in _findings(root)] == ["node.nx-behind"]


def test_other_archetypes_and_missing_nx_pass(tmp_path: Path) -> None:
    assert _findings(_repo(tmp_path / "a", "23.1.0", archetype="python-app")) == []
    assert _findings(_repo(tmp_path / "b", None)) == []


def test_nx_version_check_is_registered() -> None:
    from rn_forge.kiln import checks

    assert "nx-version" in checks.names()
