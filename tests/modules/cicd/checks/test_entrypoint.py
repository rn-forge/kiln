"""The CI entrypoint rule fails when it should.

One test per shape `check_ci_entrypoint.py` handled: a single-line step, a
block scalar, a tool after a shell separator, and a tool invoked by path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.checks import entrypoint

CLEAN = """
jobs:
  validate:
    steps:
      - run: task setup
      - run: |
          task validate
          task build
"""


def run(root: Path) -> list[str]:
    return [str(f) for f in entrypoint.check(KilnConfig.load(root), root)]


def workflow(repo, body: str) -> Path:
    return repo(**{".github__workflows__ci.yml": body})


def test_a_compliant_workflow_passes(repo) -> None:
    assert run(workflow(repo, CLEAN)) == []


@pytest.mark.parametrize(
    ("body", "tool"),
    [
        ("jobs:\n  a:\n    steps:\n      - run: uv sync\n", "uv"),
        ("jobs:\n  a:\n    steps:\n      - run: |\n          uv sync\n", "uv"),
        ("jobs:\n  a:\n    steps:\n      - run: task setup && pytest -q\n", "pytest"),
        ("jobs:\n  a:\n    steps:\n      - run: ./mkdocs build\n", "mkdocs"),
        ("jobs:\n  a:\n    steps:\n      - bash: ruff check .\n", "ruff"),
        ("jobs:\n  a:\n    steps:\n      - run: kiln apply\n", "kiln"),
    ],
    ids=[
        "single-line",
        "block-scalar",
        "after-separator",
        "by-path",
        "ado-bash",
        "kiln",
    ],
)
def test_a_directly_invoked_tool_is_reported(repo, body: str, tool: str) -> None:
    reported = run(workflow(repo, body))
    assert any(f"invokes `{tool}` directly" in line for line in reported)
    assert all(".github/workflows/ci.yml" in line for line in reported)


def test_a_finding_carries_its_line(repo) -> None:
    root = workflow(repo, "jobs:\n  a:\n    steps:\n      - run: uv sync\n")
    findings = entrypoint.check(KilnConfig.load(root), root)
    assert [f.line for f in findings] == [4]


def test_a_repo_with_no_workflows_passes(repo) -> None:
    assert run(repo()) == []


def test_task_itself_is_never_the_offender(repo) -> None:
    """`task` appears in every compliant step; it must not match."""
    assert (
        run(workflow(repo, "jobs:\n  a:\n    steps:\n      - run: task test\n")) == []
    )


FIX_CI = (
    "jobs:\n  a:\n    steps:\n      - run: pnpm exec nx fix-ci\n        if: always()\n"
)


def test_s9_1_2_8_node_lib_exempts_fix_ci(repo) -> None:
    root = repo(archetype="node-lib", **{".github__workflows__ci.yml": FIX_CI})
    assert run(root) == []


def test_s9_1_2_8_the_exemption_is_an_exact_match(repo) -> None:
    other = FIX_CI.replace("fix-ci", "fix-ci --verbose")
    root = repo(archetype="node-lib", **{".github__workflows__ci.yml": other})
    assert any("invokes `pnpm` directly" in line for line in run(root))


def test_s9_1_2_8_python_web_app_gets_no_exemption(repo) -> None:
    root = repo(archetype="python-web-app", **{".github__workflows__ci.yml": FIX_CI})
    assert any("invokes `pnpm` directly" in line for line in run(root))
