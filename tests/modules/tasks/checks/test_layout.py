"""The task-layout rules fail when they should.

One test per rule `check_task_layout.py` enforced: wrappers only in the root
file, a `desc:` on every task, and the validate gate not shrinking.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from rn_forge.kiln import checks, commands
from rn_forge.kiln.modules.tasks.config import ROOT_VERBS

# The smallest graph that satisfies the gate for an archetype with no docs
# profile: `validate` reaches every required task through one namespace.
QUALITY_HEAD = """
version: '3'
tasks:
  lint:python:
    desc: Lint
    cmds: [ruff check .]
    internal: true
  lint:generated:
    desc: Check generated state
    cmds: [kiln doctor .]
    internal: true
  lint:rn-forge-deps:
    desc: Check dependencies
    cmds: [kiln doctor .]
    internal: true
  lint:imports:
    desc: Check imports
    cmds: [lint-imports]
    internal: true
  lint:task-layout:
    desc: Check task layout
    cmds: [kiln doctor .]
    internal: true
  lint:ci-entrypoint:
    desc: Check CI entrypoint
    cmds: [kiln doctor .]
    internal: true
  lint:markdown:
    desc: Check markdown
    cmds: [mdformat --check .]
    internal: true
  lint:toml:
    desc: Check TOML
    cmds: [taplo fmt --check]
    internal: true
  typecheck:python:
    desc: Typecheck
    cmds: [pyright src]
    internal: true
  test:python:
    desc: Test
    cmds: [pytest -q]
    internal: true
"""

QUALITY = QUALITY_HEAD

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
        "lint:toml",
        "typecheck:python",
        "test:python",
    )
)

WRAPPER = "      - task: quality:lint:python"


def taskfile(
    overrides: dict[str, str] | None = None,
    extra: str = "",
    includes: str = "  quality: tasks/quality.yml\n",
) -> str:
    """A root Taskfile with exactly the ten verbs, each a wrapper.

    *overrides* replaces a verb's whole block; *extra*
    appends whole tasks.
    """
    overrides = overrides or {}
    out = f"version: '3'\nincludes:\n{includes}tasks:\n"
    for verb in ROOT_VERBS:
        if verb == "validate":
            body = f"    desc: The gate\n    cmds:\n{GATE_REFS}\n"
        else:
            body = f"    desc: {verb}\n    cmds:\n{WRAPPER}\n"
        out += overrides.get(verb, f"  {verb}:\n{body}")
    return out + extra


TASKFILE = taskfile()


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
            "Taskfile.yml": taskfile(
                {"build": "  build:\n    desc: Build\n    cmds: [uv build]\n"}
            )
        },
    )
    reported = run(root)
    assert any("is not a `task:` call" in line for line in reported)
    assert all("Taskfile.yml" in line for line in reported)


def test_root_shorthand_for_a_shell_command_is_reported(repo) -> None:
    root = compliant(
        repo, **{"Taskfile.yml": taskfile({"build": "  build: uv build\n"})}
    )
    assert any("shorthand for a raw shell command" in line for line in run(root))


def test_a_task_without_a_desc_is_reported(repo) -> None:
    root = compliant(
        repo,
        **{"Taskfile.yml": taskfile({"build": f"  build:\n    cmds:\n{WRAPPER}\n"})},
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
        **{
            "Taskfile.yml": TASKFILE.replace(
                "      - task: quality:test:python\n", "", 1
            )
        },
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


# --- S4.6.2: the task-graph validator ---------------------------------------

OWNED = "version: '3'\ntasks:\n  go:\n    cmds: [echo hi]\n"


def codes(root: Path) -> list[str]:
    return [f.code for f in checks.run(root, only="task-layout")]


def findings(root: Path, code: str):
    return [f for f in checks.run(root, only="task-layout") if f.code == code]


def declare(root: Path, namespace: str, taskfile_path: str) -> None:
    """Declare a repository-owned include in `config.toml`."""
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + f'\n[tasks]\nincludes = [{{ namespace = "{namespace}", '
        f'taskfile = "{taskfile_path}" }}]\n',
        encoding="utf-8",
    )


def test_s4_6_2_1_surface_is_exactly_the_root_verbs(repo) -> None:
    extra = f"  deploy:\n    desc: Deploy\n    cmds:\n{WRAPPER}\n"
    root = compliant(repo, **{"Taskfile.yml": taskfile(extra=extra)})
    [surface] = findings(root, "taskgraph.surface")
    assert "`deploy`" in surface.message


def test_s4_6_2_1_surface_reports_a_missing_verb(repo, tmp_path: Path) -> None:
    root = compliant(
        repo,
        **{
            "Taskfile.yml": TASKFILE.replace(
                "  clean:\n    desc: clean\n", "  cleen:\n    desc: x\n"
            )
        },
    )
    messages = [f.message for f in findings(root, "taskgraph.surface")]
    assert any("`clean`" in m and "missing" in m for m in messages)


def test_s4_6_2_1_reserved_namespace_tasks_are_internal(repo) -> None:
    for namespace in ("quality", "workspace"):
        root = compliant(
            repo,
            **{
                "Taskfile.yml": taskfile(
                    includes=f"  quality: tasks/quality.yml\n  {namespace}: tasks/{namespace}.yml\n"
                    if namespace != "quality"
                    else "  quality: tasks/quality.yml\n"
                ),
                f"tasks__{namespace}.yml": "version: '3'\ntasks:\n  x:\n    desc: X\n    cmds: [true]\n"
                if namespace != "quality"
                else QUALITY + "  x:\n    desc: X\n    cmds: [true]\n",
            },
        )
        assert [f.path for f in findings(root, "taskgraph.not-internal")] == [
            f"tasks/{namespace}.yml"
        ]


def test_s4_6_2_1_a_public_docs_api_or_web_task_is_not_reported(repo) -> None:
    includes = "".join(
        f"  {ns}: tasks/{ns}.yml\n" for ns in ("quality", "docs", "api", "web")
    )
    public = "version: '3'\ntasks:\n  dev:\n    desc: Dev\n    cmds: [true]\n"
    root = compliant(
        repo,
        **{
            "Taskfile.yml": taskfile(includes=includes),
            "tasks__docs.yml": public,
            "tasks__api.yml": public,
            "tasks__web.yml": public,
        },
    )
    assert codes(root) == []


def test_s4_6_2_1_an_include_must_exist(repo) -> None:
    root = compliant(
        repo,
        **{
            "Taskfile.yml": taskfile(
                includes="  quality: tasks/quality.yml\n  docs: tasks/docs.yml\n"
            )
        },
    )
    [missing] = findings(root, "taskgraph.missing-include")
    assert "tasks/docs.yml" in missing.message


def test_s4_6_2_1_task_refs_resolve(repo) -> None:
    managed = QUALITY + (
        "  broken:\n    desc: B\n    internal: true\n    cmds:\n"
        "      - task: quality:nope\n      - task: self:go\n"
    )
    root = compliant(
        repo,
        **{
            "Taskfile.yml": taskfile(
                includes="  quality: tasks/quality.yml\n  self: tasks/self.yml\n"
            ),
            "tasks__quality.yml": managed,
            "tasks__self.yml": OWNED,
        },
    )
    declare(root, "self", "tasks/self.yml")
    [unresolved] = findings(root, "taskgraph.unresolved")
    assert "quality:nope" in unresolved.message
    assert "self:go" not in unresolved.message


def test_s4_6_2_1_no_cycles(repo) -> None:
    quality = QUALITY + (
        "  a:\n    desc: A\n    internal: true\n    cmds:\n      - task: other:b\n"
    )
    other = (
        "version: '3'\ntasks:\n  b:\n    desc: B\n    internal: true\n"
        "    cmds:\n      - task: quality:a\n"
    )
    root = compliant(
        repo,
        **{
            "Taskfile.yml": taskfile(
                includes="  quality: tasks/quality.yml\n  other: tasks/other.yml\n"
            ),
            "tasks__quality.yml": quality,
            "tasks__other.yml": other,
        },
    )
    [cycle] = findings(root, "taskgraph.cycle")
    assert "other:b -> quality:a -> other:b" in cycle.message


def test_s4_6_2_1_reserved_namespace_collision(repo) -> None:
    root = compliant(repo, **{"tasks__mine.yml": OWNED})
    declare(root, "quality", "tasks/mine.yml")
    [collision] = findings(root, "taskgraph.reserved-namespace")
    assert "quality" in collision.message


def test_s4_6_2_1_repository_owned_files_are_not_held_to_layout(repo) -> None:
    root = compliant(
        repo,
        **{
            "Taskfile.yml": taskfile(
                includes="  quality: tasks/quality.yml\n  self: tasks/self.yml\n"
            ),
            "tasks__self.yml": OWNED,
        },
    )
    declare(root, "self", "tasks/self.yml")
    assert codes(root) == []


CI = "jobs:\n  a:\n    steps:\n      - run: task nope\n"


def test_s4_6_2_2_unresolved_ref_in_a_workflow(repo, write_state) -> None:
    ci = (
        "jobs:\n  a:\n    steps:\n"
        "      - run: task --list\n"
        "      - run: task validate\n"
        "      - run: |\n"
        "          echo hi\n"
        "          task validate && task nope\n"
    )
    root = compliant(
        repo, **{".github__workflows__ci.yml": ci, "NOTES.md": "task nope\n"}
    )
    write_state(
        {
            ".github/workflows/ci.yml": {
                "kind": "managed",
                "path": ".github/workflows/ci.yml",
                "content_hash": "0",
            }
        }
    )
    [unresolved] = findings(root, "taskgraph.unresolved-ref")
    assert (unresolved.path, unresolved.line) == (".github/workflows/ci.yml", 8)
    assert "nope" in unresolved.message


def test_s4_6_2_2_unresolved_ref_in_a_managed_block(repo, write_state) -> None:
    text = (
        "# Title\n\nrun task nope outside\n\n<!-- BEGIN x -->\n"
        "Run `task validate`.\nthen task nope\n<!-- END x -->\n"
    )
    root = compliant(repo, **{"CLAUDE.md": text})
    write_state(
        {
            "CLAUDE.md#x": {
                "kind": "block",
                "path": "CLAUDE.md",
                "begin_marker": "<!-- BEGIN x -->",
                "end_marker": "<!-- END x -->",
                "content_hash": "0",
            }
        }
    )
    [unresolved] = findings(root, "taskgraph.unresolved-ref")
    assert (unresolved.path, unresolved.line) == ("CLAUDE.md", 7)


def _render_cell(tmp_path_factory, name: str, archetype: str, **flags: str) -> Path:
    parent = tmp_path_factory.mktemp(name)
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(parent)
        commands.new(Path(name), archetype=archetype, docs="mkdocs", yes=True, **flags)
    return parent / name


CELLS = {
    "python-app": ("python-app", {}),
    "python-tool": ("python-tool", {}),
    "python-web-api": ("python-web-api", {"backend": "fastapi"}),
    "python-web-app": (
        "python-web-app",
        {"backend": "fastapi", "frontend": "angular"},
    ),
}


@pytest.mark.parametrize(
    "cell",
    [
        "python-app",
        "python-tool",
        "python-web-api",
        pytest.param(
            "python-web-app",
            marks=pytest.mark.skipif(
                shutil.which("pnpm") is None, reason="pnpm is not on PATH"
            ),
        ),
        "python-lib",
    ],
)
def test_s4_6_2_3_every_rendered_cell_passes(
    cell: str, rendered, tmp_path_factory: pytest.TempPathFactory
) -> None:
    if cell == "python-lib":
        root = rendered("python-lib")
    else:
        archetype, flags = CELLS[cell]
        root = _render_cell(tmp_path_factory, cell, archetype, **flags)
    assert checks.run(root, only="task-layout") == []
