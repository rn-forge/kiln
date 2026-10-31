"""The planner stands alone: it loads and ships nothing else of kiln's."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FORBIDDEN = (
    "rn_forge.commons",
    "rn_forge.cli",
    "rn_forge.tooling",
    "typer",
    "jinja2",
    "pydantic",
    "rich",
)


def test_s6_7_2_1_cli_loads_no_other_rn_forge_code() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, rn_forge.kiln.devops.cli; print('\\n'.join(sys.modules))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    loaded = result.stdout.split()
    assert [n for n in loaded if n.startswith(FORBIDDEN)] == []
    kiln = [n for n in loaded if n.startswith("rn_forge.kiln.")]
    assert kiln
    assert [n for n in kiln if not n.startswith("rn_forge.kiln.devops")] == []


def test_s6_7_2_2_console_script_is_declared() -> None:
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["scripts"]["kiln-devops"] == "rn_forge.kiln.devops.cli:main"
    assert any(d.startswith("packaging") for d in project["dependencies"])
