"""The node task surface: both archetypes, affected CI, validate without Nx."""

from __future__ import annotations
import json
import os
import pytest
import re
import subprocess
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS
from rn_forge.kiln.modules.tasks.config import ROOT_VERBS
from tests.conftest import module_findings, git, requires
from tests.modules.tasks.support import (
    ALL_CELLS,
    ARCHETYPES,
    NODE_AUDITS,
    NODE_CHECKS,
    STEP,
    _ci_tasks,
    _codes,
    _commit,
    _load,
    _node_lib_root,
    _node_root,
    _root,
    _run_task,
    _ci_root,
)


def test_node_yml_is_byte_identical_in_both_cells(tmp_path: Path) -> None:
    lib = _node_lib_root(tmp_path / "lib")
    app = _node_root(tmp_path / "app")
    cycle.apply(lib, home=tmp_path / "home")
    cycle.apply(app, home=tmp_path / "home")
    # Only a library publishes, so the lib file adds exactly `version`.
    lib_doc = YamlUtils.load((lib / "tasks/node.yml").read_text(encoding="utf-8"))
    text = (app / "tasks/node.yml").read_text(encoding="utf-8")
    del lib_doc["tasks"]["version"]
    assert lib_doc == YamlUtils.load(text)
    assert set(YamlUtils.load(text)["tasks"]) == {*NODE_CHECKS, *NODE_AUDITS}


@pytest.mark.parametrize("cell", ["lib", "app"])
def test_typecheck_is_the_angular_build(tmp_path: Path, cell: str) -> None:
    root = (_node_lib_root if cell == "lib" else _node_root)(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    task = _load(root, "tasks/node.yml")["tasks"]["typecheck"]
    assert task["cmds"] == ["pnpm nx run-many -t build"]
    assert task["desc"] == "Type-check every project through its Angular build."


def test_root_typecheck_per_archetype(tmp_path: Path) -> None:
    lib = _node_lib_root(tmp_path / "lib")
    app = _node_root(tmp_path / "app")
    cycle.apply(lib, home=tmp_path / "home")
    cycle.apply(app, home=tmp_path / "home")
    assert _load(lib, "Taskfile.yml")["tasks"]["typecheck"]["cmds"] == [
        {"task": "node:typecheck"}
    ]
    assert _load(app, "Taskfile.yml")["tasks"]["typecheck"]["cmds"] == [
        {"task": "python:typecheck"},
        {"task": "node:typecheck"},
    ]


def test_python_archetypes_typecheck_calls_no_node(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    assert _load(root, "Taskfile.yml")["tasks"]["typecheck"]["cmds"] == [
        {"task": "python:typecheck"}
    ]


def test_clean_removes_the_nx_cache_and_the_web_dist(tmp_path: Path) -> None:
    lib = _node_lib_root(tmp_path / "lib")
    app = _node_root(tmp_path / "app")
    cycle.apply(lib, home=tmp_path / "home")
    cycle.apply(app, home=tmp_path / "home")
    lib_cmds = _load(lib, "tasks/workspace.yml")["tasks"]["clean"]["cmds"]
    app_cmds = _load(app, "tasks/workspace.yml")["tasks"]["clean"]["cmds"]
    assert "rm -rf .nx" in lib_cmds
    assert "rm -rf .nx apps/web/dist" in app_cmds
    assert not any("dist" in c and ".nx" in c for c in lib_cmds)


@pytest.mark.parametrize("name", ["typecheck", "e2e"])
def test_python_web_app_overrides_take_the_merged_keys(
    tmp_path: Path, name: str
) -> None:
    root = _node_root(
        tmp_path,
        extra=f'\n[tasks]\n[tasks.command_overrides]\n"node:{name}" = "echo hi"\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    assert _load(root, "tasks/node.yml")["tasks"][name]["cmds"] == ["echo hi"]


def test_a_python_tool_still_refuses_the_node_keys(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra='\n[tasks]\n[tasks.command_overrides]\n"node:typecheck" = "echo hi"\n',
    )
    with pytest.raises(AppException, match="node:typecheck"):
        TASKS.artifacts(KilnConfig.load(root), root)


PYTHON_TASKS = (
    "install",
    "lint",
    "lint:imports",
    "lint:audit",
    "lint:licenses",
    "format",
    "typecheck",
    "test",
    "test:coverage",
    "build",
    "version",
)


QUALITY_STAYS = {
    "lint:markdown",
    "lint:toml",
    "lint:yaml",
    "format:markdown",
    "format:toml",
    "format:yaml",
}


PYTHON_OLD_KEYS = {
    "quality:lint:python": "python:lint",
    "quality:lint:imports": "python:lint:imports",
    "quality:lint:audit": "python:lint:audit",
    "quality:format:python": "python:format",
    "quality:typecheck:python": "python:typecheck",
    "quality:test:python": "python:test",
    "quality:test:coverage": "python:test:coverage",
    "workspace:install": "python:install",
    "workspace:build": "python:build",
    "workspace:version": "python:version",
}


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_python_yml_holds_the_toolchain(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _ci_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "tasks/python.yml")["tasks"]
    assert set(tasks) == set(PYTHON_TASKS)
    for name, task in tasks.items():
        assert task["internal"] is True, name
        assert task["desc"].strip(), name


def test_the_bodies_moved_unchanged(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "tasks/python.yml")["tasks"]
    assert tasks["install"]["cmds"] == ["uv sync --group dev --group docs"]
    assert tasks["lint"]["cmds"] == [
        "uv run ruff check src $(test -d tests && echo tests)",
        "uv run ruff format --check src $(test -d tests && echo tests)",
    ]
    assert tasks["typecheck"]["cmds"] == ["uv run pyright src"]
    assert tasks["test"]["cmds"] == ["uv run pytest -q {{.CLI_ARGS}}"]
    assert tasks["build"]["env"] == {"UV_CACHE_DIR": "/tmp/demo-uv-cache"}


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_quality_is_repository_wide(tmp_path: Path, archetype: str, extra: str) -> None:
    root = _ci_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    quality = _load(root, "tasks/quality.yml")
    assert set(quality["tasks"]) == QUALITY_STAYS
    assert set(quality["vars"]) == {"FILES"}


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_workspace_is_clean_only(tmp_path: Path, archetype: str, extra: str) -> None:
    root = _ci_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    workspace = _load(root, "tasks/workspace.yml")
    assert set(workspace["tasks"]) == {"banner", "step", "clean"}
    assert "vars" not in workspace


def test_python_lib_vars_move_with_the_tasks(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    cycle.apply(root, home=tmp_path / "home")
    assert set(_load(root, "tasks/python.yml")["vars"]) == {
        "PACKAGE_DIRS",
        "PACKAGES",
    }


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_the_wrappers_call_python_in_place(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _ci_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "Taskfile.yml")["tasks"]

    def refs(verb: str) -> list[str]:
        calls = tasks[verb].get("cmds", tasks[verb].get("deps"))
        return [cmd["task"] for cmd in calls if cmd["task"] != STEP]

    assert refs("setup")[0] == "python:install"
    if archetype == "python-web-app":
        assert refs("setup") == ["python:install", "node:install"]
    lint = refs("lint")
    assert lint[0] == "python:lint"
    assert "python:lint:imports" in lint
    assert "python:lint:audit" in lint
    assert not [r for r in lint if r.startswith("quality:lint:") and "python" in r]
    assert refs("format")[0] == "python:format"
    assert "python:typecheck" in refs("typecheck")
    assert "python:test" in refs("test")
    assert "python:test:coverage" in refs("test:coverage")
    assert refs("build")[0] == "python:build"
    assert "python:version" in refs("version")
    assert "workspace:clean" in refs("clean")
    assert not [
        r
        for verb in tasks
        for r in refs(verb)
        if r in PYTHON_OLD_KEYS
        or r.startswith("workspace:")
        and r not in ("workspace:clean", "workspace:banner", STEP)
    ]


@pytest.mark.parametrize(
    "new", [n for n in PYTHON_OLD_KEYS.values() if n != "python:lint:audit"]
)
def test_overrides_take_the_new_keys(tmp_path: Path, new: str) -> None:
    root = _root(
        tmp_path,
        extra=f'\n[tasks]\n[tasks.command_overrides]\n"{new}" = "echo hi"\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    task = _load(root, "tasks/python.yml")["tasks"][new.removeprefix("python:")]
    assert task["cmds"] == ["echo hi"]


@pytest.mark.parametrize("old", PYTHON_OLD_KEYS)
def test_old_keys_are_refused(tmp_path: Path, old: str) -> None:
    root = _root(
        tmp_path,
        extra=f'\n[tasks]\n[tasks.command_overrides]\n"{old}" = "echo hi"\n',
    )
    with pytest.raises(AppException, match=re.escape(old)):
        TASKS.artifacts(KilnConfig.load(root), root)


@pytest.mark.parametrize("name", [n for n in archetypes.shipped() if n != "node-lib"])
def test_required_validate_names_the_python_tasks(name: str) -> None:
    required = archetypes.load(name).required_validate
    for task in ("lint", "lint:imports", "lint:audit", "typecheck", "test"):
        assert f"python:{task}" in required
    allowed = {f"quality:{task}" for task in QUALITY_STAYS if task.startswith("lint:")}
    assert not [r for r in required if r.startswith("quality:") and r not in allowed]


def test_python_tasks_must_be_internal(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    path = root / "tasks/python.yml"
    text = path.read_text(encoding="utf-8")
    head, _, tail = text.partition("  lint:\n")
    path.write_text(
        head + "  lint:\n" + tail.replace("    internal: true\n", "", 1),
        encoding="utf-8",
    )
    assert "taskgraph.not-internal" in _codes(root)


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_task_layout_accepts_the_rendered_files(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _ci_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    assert _codes(root) == []


NODE_LIB_CI_TASKS = ("test", "test:has-e2e", "test:playwright", "test:playwright-deps")


def _affected_rule(tmp_path: Path) -> str:
    """The `outside_projects` function the `ci:test` task defines."""
    cmd = _ci_tasks(_node_lib_root(tmp_path))["tasks"]["test"]["cmds"][0]  # type: ignore[index]
    match = re.search(r"^outside_projects\(\) \{\n.*?^\}\n", cmd, re.M | re.S)
    assert match
    return match.group(0)


def _outside(tmp_path: Path, *changed: str) -> list[str]:
    """What the rule reports for `changed`, in a repository of two projects."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    base = _commit(
        repo, "libs/a/src/a.ts", "libs/b/src/b.ts", "docs/guide.md", "README.md"
    )
    head = _commit(repo, *changed)
    script = f'{_affected_rule(tmp_path)}\noutside_projects "$1" "$2" libs/a libs/b'
    done = subprocess.run(
        ["bash", "-c", script, "bash", base, head],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.split()


@requires("git")
@pytest.mark.parametrize(
    ("changed", "outside"),
    [
        (("libs/a/src/a.ts",), []),
        (("libs/a/src/a.ts", "libs/b/src/b.ts"), []),
        (("docs/guide.md", "docs/new.png"), []),
        (("README.md", "libs/a/CHANGELOG.md"), []),
        (("tools/ci/x.mjs",), ["tools/ci/x.mjs"]),
        ((".github/actions/setup/action.yml",), [".github/actions/setup/action.yml"]),
        (("libs/a/src/a.ts", "package.json"), ["package.json"]),
        (("libs/ab/src/x.ts",), ["libs/ab/src/x.ts"]),
    ],
)
def test_changed_file_rule(
    tmp_path: Path, changed: tuple[str, ...], outside: list[str]
) -> None:
    assert _outside(tmp_path, *changed) == outside


@requires("task", "jq")
def test_affected_selects_run_many_or_affected(tmp_path: Path) -> None:
    root = _node_lib_root(tmp_path / "cell")
    cycle.apply(root, home=tmp_path / "home")
    stub = tmp_path / "bin"
    stub.mkdir()
    pnpm = stub / "pnpm"
    pnpm.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        '  "exec nx show projects --json") echo \'["a","b"]\' ;;\n'
        '  "exec nx show project a --json") echo \'{"root":"libs/a"}\' ;;\n'
        '  "exec nx show project b --json") echo \'{"root":"libs/b"}\' ;;\n'
        '  *) echo "pnpm $*" ;;\n'
        "esac\n"
    )
    pnpm.chmod(0o755)
    repo = tmp_path / "work"
    repo.mkdir()
    git(repo, "init", "-q")
    base = _commit(repo, "libs/a/a.ts", "libs/b/b.ts")
    inside = _commit(repo, "libs/a/a.ts")
    outside = _commit(repo, "package.json")

    def selected(event: str, nx_base: str, nx_head: str) -> str:
        env = {
            **os.environ,
            "PATH": f"{stub}:{os.environ['PATH']}",
            "GITHUB_EVENT_NAME": event,
            "NX_BASE": nx_base,
            "NX_HEAD": nx_head,
        }
        done = subprocess.run(
            [
                "task",
                "-t",
                str(root / "Taskfile.yml"),
                "--dir",
                str(repo),
                "ci:test",
                "--",
                "lint test",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        return done.stdout.strip()

    assert (
        selected("pull_request", base, inside) == "pnpm exec nx affected -t lint test"
    )
    assert (
        selected("pull_request", base, outside) == "pnpm exec nx run-many -t lint test"
    )
    assert (
        selected("workflow_dispatch", base, inside)
        == "pnpm exec nx run-many -t lint test"
    )


def test_node_lib_ci_tasks_are_described_and_public(tmp_path: Path) -> None:
    tasks = _ci_tasks(_node_lib_root(tmp_path))["tasks"]
    for name in NODE_LIB_CI_TASKS:
        assert tasks[name]["desc"], name  # type: ignore[index]
        assert "internal" not in tasks[name], name  # type: ignore[operator]
    assert tasks["test:has-e2e"]["cmds"] == [  # type: ignore[index]
        "echo \"has-e2e=$(pnpm exec nx show projects --with-target e2e --json | jq 'length > 0')\""
    ]
    assert tasks["test:playwright"]["cmds"] == [
        "pnpm exec playwright install --with-deps"
    ]  # type: ignore[index]
    assert tasks["test:playwright-deps"]["cmds"] == [
        "pnpm exec playwright install-deps"
    ]  # type: ignore[index]


def test_other_archetypes_render_no_affected_tasks(tmp_path: Path) -> None:
    for archetype in ARCHETYPES:
        tasks = _ci_tasks(_root(tmp_path / archetype, archetype))["tasks"]
        assert not set(NODE_LIB_CI_TASKS[1:]) & set(tasks), archetype  # type: ignore[arg-type]
        assert "nx" not in json.dumps(tasks["test"]), archetype


CI_VALIDATE_HEAD = [
    {"task": ":quality:lint:markdown"},
    {"task": ":quality:lint:toml"},
    {"task": ":quality:lint:yaml"},
    {"task": ":kiln:doctor"},
    {"task": "lint:workflows"},
    {"task": "internal-ranges"},
]


def test_node_lib_ci_validate_is_public_and_ordered(tmp_path: Path) -> None:
    task = _ci_tasks(_node_lib_root(tmp_path / "docs"))["tasks"]["validate"]  # type: ignore[index]
    assert task["desc"].startswith("CI only")
    assert "internal" not in task
    assert task["cmds"] == [*CI_VALIDATE_HEAD, {"task": ":docs:build"}]
    bare = _root(tmp_path / "none", "node-lib", profile="none")
    task = _ci_tasks(bare)["tasks"]["validate"]  # type: ignore[index]
    assert task["cmds"] == CI_VALIDATE_HEAD


def test_only_node_lib_and_single_packages_have_a_ci_validate_task(
    tmp_path: Path,
) -> None:
    for archetype in (*ARCHETYPES,):
        tasks = _ci_tasks(_root(tmp_path / archetype, archetype))["tasks"]
        assert ("validate" in tasks) == (archetype != "python-lib"), archetype  # type: ignore[operator]


@requires("task")
def test_dry_run_prints_doctor_with_full_only_when_asked(
    tmp_path: Path,
) -> None:
    root = _node_lib_root(tmp_path / "cell")
    cycle.apply(root, home=tmp_path / "home")
    env = {k: v for k, v in os.environ.items() if k != "KILN_DOCTOR_FULL"}

    def dry(extra: dict[str, str]) -> str:
        done = subprocess.run(
            ["task", "-t", str(root / "Taskfile.yml"), "--dry", "ci:validate"],
            capture_output=True,
            text=True,
            check=True,
            cwd=root,
            env={**env, **extra},
        )
        return done.stdout + done.stderr

    plain = [line for line in dry({}).splitlines() if " doctor " in line]
    full = [
        line
        for line in dry({"KILN_DOCTOR_FULL": "1"}).splitlines()
        if " doctor " in line
    ]
    assert plain
    assert all("--full" not in line for line in plain)
    assert full
    assert all("--full" in line for line in full)


def test_root_validate_still_runs_the_nx_verbs(tmp_path: Path) -> None:
    root = _node_lib_root(tmp_path)
    cmds = [
        c
        for c in _load_from_render(root)["tasks"]["validate"]["cmds"]
        if c["task"] != "workspace:banner"
    ]
    assert cmds == [
        {"task": "lint"},
        {"task": "typecheck"},
        {"task": "test"},
        {"task": "docs:build"},
    ]


def test_extra_refs_run_in_root_validate_order(tmp_path: Path) -> None:
    extra = (
        "\n[tasks]\n[tasks.extra_refs]\n"
        'lint = ["workspace:clean"]\n'
        'typecheck = ["python:version"]\n'
        'test = ["python:install"]\n'
        'validate = ["kiln:doctor"]\n'
        'format = ["workspace:clean"]\n'
    )
    root = _root(tmp_path, "node-lib", extra=extra)
    cmds = _ci_tasks(root)["tasks"]["validate"]["cmds"]  # type: ignore[index]
    assert cmds == [
        *CI_VALIDATE_HEAD,
        {"task": ":workspace:clean"},
        {"task": ":python:version"},
        {"task": ":python:install"},
        {"task": ":docs:build"},
        {"task": ":kiln:doctor"},
    ]


def _load_from_render(root: Path) -> dict[str, object]:
    rendered = {a.path: a.content for a in TASKS.artifacts(KilnConfig.load(root), root)}
    return YamlUtils.load(rendered["Taskfile.yml"])


def test_kiln_tasks_run_diff_and_apply(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    specs = YamlUtils.load((root / "tasks" / "kiln.yml").read_text(encoding="utf-8"))[
        "tasks"
    ]
    for verb in ("diff", "apply"):
        assert "internal" not in specs[verb]
        assert specs[verb]["cmds"] == ["{{.KILN}} " + verb + " {{.CLI_ARGS}}"]
    includes = YamlUtils.load((root / "Taskfile.yml").read_text(encoding="utf-8"))[
        "includes"
    ]
    assert includes["kiln"] == "tasks/kiln.yml"
    assert specs["doctor"]["internal"] is True


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_ten_root_verbs(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype, profile="none")
    cycle.apply(root, home=tmp_path / "home")
    result = _run_task(root, "--list", "--json")
    assert result.returncode == 0, result.stderr
    names = {entry["name"] for entry in json.loads(result.stdout)["tasks"]}
    assert {n for n in names if n.startswith("kiln:")} == {
        "kiln:diff",
        "kiln:apply",
        "kiln:pin",
        "kiln:upgrade",
    }
    assert {n for n in names if not n.startswith(("ci:", "kiln:", "sonar:"))} == set(
        ROOT_VERBS
    )
    assert not [
        f
        for f in module_findings("tasks", KilnConfig.load(root), root)
        if f.code.startswith("taskgraph")
    ]
