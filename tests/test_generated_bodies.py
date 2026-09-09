"""Every generated script has one body across every golden repo.

This is F2 made executable: `check_ci_entrypoint.py` existed in four repos as
four forks that differed only in a list literal. In the golden repos the list
lives in a `# BEGIN kiln config` header and the body below it is the same bytes
everywhere — and that is only true for as long as something checks it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "fixtures" / "golden"
ASSERT = ROOT / "tests" / "support" / "assert_generated_bodies.py"

GENERATED_SCRIPTS = [
    "scripts/ci/check_ci_entrypoint.py",
    "scripts/task/check_task_layout.py",
    "scripts/standards/check_generated.py",
    "scripts/standards/check_rn_forge_deps.py",
    "scripts/docs/_common.py",
    "scripts/docs/check_docs.py",
    "scripts/docs/check_structure.py",
    "scripts/docs/gen_nav.py",
]


def golden_repos() -> list[Path]:
    return sorted(path for path in GOLDEN.iterdir() if (path / "Taskfile.yml").exists())


@pytest.mark.parametrize("relative_path", GENERATED_SCRIPTS)
def test_one_body_per_generated_script(relative_path: str):
    repos = golden_repos()
    assert len(repos) >= 2, "need at least two golden repos to compare"
    result = subprocess.run(
        [sys.executable, str(ASSERT), "--relative-path", relative_path, *map(str, repos)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_golden_repo_has_every_generated_script():
    for repo in golden_repos():
        for relative_path in GENERATED_SCRIPTS:
            assert (repo / relative_path).is_file(), f"{repo.name} is missing {relative_path}"
