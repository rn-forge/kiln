"""The task-layout rules fail when they should.

One test per rule `check_task_layout.py` enforced: wrappers only in the root
file, a `desc:` on every task, and the validate gate not shrinking.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.kiln import checks

# The smallest graph that satisfies the gate for an archetype with no docs
# profile: `validate` reaches every required task through one namespace.
QUALITY = """
version: '3'
tasks:
  lint:python:
    desc: Lint
    cmds: [ruff check .]
  lint:generated:
    desc: Check generated state
    cmds: [kiln doctor .]
  lint:rn-forge-deps:
    desc: Check dependencies
    cmds: [kiln doctor .]
  lint:imports:
    desc: Check imports
    cmds: [lint-imports]
  lint:task-layout:
    desc: Check task layout
    cmds: [kiln doctor .]
  lint:ci-entrypoint:
    desc: Check CI entrypoint
    cmds: [kiln doctor .]
  lint:markdown:
    desc: Check markdown
    cmds: [mdformat --check .]
  typecheck:python:
    desc: Typecheck
    cmds: [pyright src]
  test:python:
    desc: Test
    cmds: [pytest -q]
"""

GATE_REFS = "\n".join(
    f"      - task: quality:{name}"
    for name in (
        "lint:python",
        "lint:generated",
        "lint:rn-forge-deps",
        "lint:imports",
        "lint:task-layout",
        "lint:ci-entrypoint",
        "lint:markdown",
        "typecheck:python",
        "test:python",
    )
)

TASKFILE = f"""
version: '3'
includes:
  quality: tasks/quality.yml
tasks:
  validate:
    desc: The gate
    cmds:
{GATE_REFS}
"""


def run(root: Path) -> list[str]:
    return [str(f) for f in checks.run(root, only="task-layout")]


def compliant(repo, **overrides: str) -> Path:
    files = {"Taskfile.yml": TASKFILE, "tasks__quality.yml": QUALITY}
    files.update(overrides)
    return repo(**files)


def test_a_compliant_graph_passes(repo) -> None:
    assert run(compliant(repo)) == []


def test_a_root_task_running_raw_shell_is_reported(repo) -> None:
    root = compliant(
        repo,
        **{
            "Taskfile.yml": TASKFILE
            + "  build:\n    desc: Build\n    cmds: [uv build]\n"
        },
    )
    reported = run(root)
    assert any("is not a `task:` call" in line for line in reported)
    assert all("Taskfile.yml" in line for line in reported)


def test_root_shorthand_for_a_shell_command_is_reported(repo) -> None:
    root = compliant(repo, **{"Taskfile.yml": TASKFILE + "  build: uv build\n"})
    assert any("shorthand for a raw shell command" in line for line in run(root))


def test_a_task_without_a_desc_is_reported(repo) -> None:
    root = compliant(
        repo, **{"Taskfile.yml": TASKFILE + "  build:\n    cmds:\n      - task: x\n"}
    )
    assert any("has no non-empty `desc:`" in line for line in run(root))


def test_a_namespace_task_without_a_desc_is_reported(repo) -> None:
    root = compliant(
        repo, **{"tasks__quality.yml": QUALITY + "  extra:\n    cmds: [true]\n"}
    )
    reported = run(root)
    assert any("has no non-empty `desc:`" in line for line in reported)
    assert any("tasks/quality.yml" in line for line in reported)


def test_a_shrunk_gate_is_reported(repo) -> None:
    """Dropping one `task:` ref from `validate` is exactly the failure."""
    root = compliant(
        repo,
        **{"Taskfile.yml": TASKFILE.replace("      - task: quality:test:python\n", "")},
    )
    assert any(
        "not reachable from `validate`" in line and "test:python" in line
        for line in run(root)
    )


def test_a_missing_validate_task_is_reported(repo) -> None:
    root = compliant(
        repo, **{"Taskfile.yml": "version: '3'\ntasks:\n  build:\n    desc: B\n"}
    )
    assert any("the aggregate gate is missing" in line for line in run(root))


def test_a_missing_taskfile_is_reported(repo) -> None:
    assert any("not found" in line for line in run(repo()))


def test_the_docs_profile_adds_its_gate_entries(repo) -> None:
    """A `mkdocs` repo must also reach the docs tasks (the reference, §2)."""
    root = compliant(repo)
    (root / ".rn-forge" / "kiln" / "config.toml").write_text(
        (root / ".rn-forge" / "kiln" / "config.toml")
        .read_text(encoding="utf-8")
        .replace('profile = "none"', 'profile = "mkdocs"'),
        encoding="utf-8",
    )
    assert any("docs:build" in line for line in run(root))
