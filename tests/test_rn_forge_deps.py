"""The dependency contract fails when it should.

A lint that has never rejected anything is a lint nobody has tested. This runs
the golden repo's own `check_rn_forge_deps.py` — the exact bytes every generated
repo commits — against synthetic `pyproject.toml` files, one per rule in
kiln ADR-0005.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHECKER = (
    ROOT
    / "tests"
    / "fixtures"
    / "golden"
    / "python-tool"
    / "scripts"
    / "standards"
    / "check_rn_forge_deps.py"
)

BASE_URL = "git+https://github.com/rn-forge/pykit@feature/upgrade"


def pinned(distribution: str) -> str:
    return f"{distribution} @ {BASE_URL}#subdirectory=packages/{distribution}"


# The python-tool archetype's whole REQUIRED set — the checker under test is
# that archetype's copy, so a fixture missing any one of the three is testing
# the `required` rule rather than the one it means to.
REQUIRED_URLS = [
    pinned("rn-forge-commons"),
    pinned("rn-forge-cli"),
    pinned("rn-forge-tooling"),
]
PINNED_URL = REQUIRED_URLS[0]
UNPINNED_URL = (
    "rn-forge-commons @ git+https://github.com/rn-forge/pykit"
    "#subdirectory=packages/rn-forge-commons"
)
REQUIRED_BLOCK = ", ".join(f'"{url}"' for url in REQUIRED_URLS)

COMPLIANT = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = [{REQUIRED_BLOCK}]
"""

MISSING_REQUIRED = """
[project]
name = "example"
version = "0.1.0"
dependencies = []
"""

FORBIDDEN_KIT = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = [{REQUIRED_BLOCK}]

[dependency-groups]
dev = ["rn-forge-agentkit>=0.6.0"]
"""

UNPINNED = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = ["{UNPINNED_URL}", "{REQUIRED_URLS[1]}", "{REQUIRED_URLS[2]}"]
"""

# The exact shape ADR-0005 rejects: resolvable in the workspace, unresolvable
# for anyone who installs the built wheel.
SOURCE_OVERRIDE_ONLY = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = ["rn-forge-commons>=0.2.2", "{REQUIRED_URLS[1]}", "{REQUIRED_URLS[2]}"]

[tool.uv.sources]
rn-forge-commons = {{ git = "https://github.com/rn-forge/pykit", subdirectory = "packages/rn-forge-commons", tag = "rn-forge-commons-v0.2.2" }}
"""

EXTRA_ON_ALLOWED = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = [
  "rn-forge-commons[excel] @ {PINNED_URL.partition(" @ ")[2]}",
  "{REQUIRED_URLS[1]}",
  "{REQUIRED_URLS[2]}",
]
"""


def run(tmp_path: Path, pyproject: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(CHECKER), str(tmp_path)],
        capture_output=True,
        text=True,
    )


def test_a_compliant_repo_passes(tmp_path: Path):
    result = run(tmp_path, COMPLIANT)
    assert result.returncode == 0, result.stdout


def test_an_extra_on_an_allowed_distribution_is_still_allowed(tmp_path: Path):
    """`rn-forge-commons[excel]` is the same distribution, not a different one."""
    result = run(tmp_path, EXTRA_ON_ALLOWED)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    ("pyproject", "expected"),
    [
        (MISSING_REQUIRED, "requires a dependency on `rn-forge-commons`"),
        (FORBIDDEN_KIT, "not in this archetype's allowed set"),
        (UNPINNED, "names no tag or rev"),
        (SOURCE_OVERRIDE_ONLY, "does not survive into a built wheel"),
    ],
    ids=["required", "allowed", "pinned", "source-override"],
)
def test_each_rule_rejects_its_violation(tmp_path: Path, pyproject: str, expected: str):
    result = run(tmp_path, pyproject)
    assert result.returncode == 1, result.stdout
    assert expected in result.stdout


def test_a_missing_pyproject_is_a_finding(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, str(CHECKER), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "not found" in result.stdout
