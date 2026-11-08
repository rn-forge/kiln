"""S17.1.5 — the public task surface, read from the rendered task files."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import surface

CELLS = (
    ("python-app", ""),
    ("python-tool", ""),
    ("python-lib", ""),
    ("python-web-api", ""),
    ("python-web-app", 'frontend = "angular"'),
    ("node-lib", ""),
)

CONFIG = """
schema_version = 1

[repository]
name = "demo"
owner = "rn-forge"
archetype = "{archetype}"

[docs]
profile = "mkdocs"
{section}
"""


def _root(tmp_path: Path, archetype: str, frontend: str) -> Path:
    section = ""
    if archetype == "python-lib":
        section = '\n[archetype."python-lib"]\npackages = ["packages/alpha", "packages/beta"]\n'
    elif archetype.startswith("python-web"):
        section = f'\n[archetype."{archetype}"]\nbackend = "fastapi"\n{frontend}\n'
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        CONFIG.format(archetype=archetype, section=section), encoding="utf-8"
    )
    return tmp_path


def _run_task(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "KILN_DOCTOR_FULL"}
    return subprocess.run(
        ["task", *args], cwd=root, capture_output=True, text=True, check=False, env=env
    )


@pytest.mark.parametrize(("archetype", "frontend"), CELLS, ids=[c[0] for c in CELLS])
def test_s17_1_5_1_surface_is_what_task_lists(
    tmp_path: Path, archetype: str, frontend: str
) -> None:
    root = _root(tmp_path, archetype, frontend)
    cycle.apply(root, home=tmp_path / "home")
    result = _run_task(root, "--list", "--json")
    assert result.returncode == 0, result.stderr
    listed = {
        (entry["name"], entry["desc"]) for entry in json.loads(result.stdout)["tasks"]
    }
    public = surface.public_tasks(KilnConfig.load(root))
    assert {(t.name, t.desc) for t in public} == listed
    assert [t.name for t in public] == sorted(t.name for t in public)
    assert any(t.name.startswith("ci:") for t in public)
