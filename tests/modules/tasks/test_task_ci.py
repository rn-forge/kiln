"""The `ci:` tasks: where they live and the grammar they follow."""

from __future__ import annotations

from tests.conftest import module_findings
import pytest
import re
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS
from tests.modules.tasks.support import (
    ALL_CELLS,
    ARCHETYPES,
    NODE_AUDITS,
    NODE_CHECKS,
    _ci_cells,
    _ci_rendered,
    _codes,
    _load,
    _node_lib_root,
    _node_root,
    _root,
    _s4_12_1_root,
    _secrets_root,
    _unmarked,
)


CI_LINT_CHECKS = {
    "lint:workflows": ["uv run zizmor --offline .github", "uv run actionlint"],
}


CI_PIPELINE_TASKS = {
    "plan",
    "internal-ranges",
    "adapters",
    "test",
    "integration",
    "smoke",
    "suites",
    "release:build",
    "release:publish",
    "verify-release",
    "docs:publish",
}


SINGLE_PIPELINE_TASKS = {
    "validate",
    "test",
    "plan",
    "integration",
    "smoke",
    "suites",
    "verify-release",
}


OLD_CI_KEYS = [
    "quality:lint:ci-entrypoint",
    "quality:lint:ci-pins",
    "quality:lint:ci-hooks",
    "quality:lint:workflows",
]


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_s4_12_2_1_every_archetype_renders_ci_yml(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _s4_12_1_root(tmp_path, archetype, extra)
    rendered = {a.path: a.content for a in TASKS.artifacts(KilnConfig.load(root), root)}
    assert "tasks/ci.yml" in rendered
    assert YamlUtils.load(rendered["Taskfile.yml"])["includes"]["ci"] == "tasks/ci.yml"


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_s4_12_2_2_ci_yml_holds_the_workflows_check(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _s4_12_1_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "tasks/ci.yml")["tasks"]
    for name, cmds in CI_LINT_CHECKS.items():
        assert tasks[name]["internal"] is True
        assert tasks[name]["desc"].strip()
        assert tasks[name]["cmds"] == cmds


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_s4_12_2_3_only_python_lib_has_the_pipeline_tasks(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _s4_12_1_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    document = _load(root, "tasks/ci.yml")
    assert "sonar:target" in document["tasks"]
    single = {"release:state", "release:source", "release:publish"}
    if archetype != "python-lib":
        assert single <= set(document["tasks"])
    others = {
        k
        for k in document["tasks"]
        if not k.startswith("lint:")
        and k not in {"sonar:target", "secret-scan", "secrets:install"}
        and not (archetype != "python-lib" and k in single)
    }
    if archetype == "python-lib":
        assert others == CI_PIPELINE_TASKS
        assert not any("internal" in document["tasks"][k] for k in others)
    else:
        dist = (
            {"dist:resolve", "dist:verify", "consumer"}
            if archetype == "python-web-app"
            else set()
        )
        assert others == SINGLE_PIPELINE_TASKS | dist
    assert "DEVOPS" in document["vars"]


@pytest.mark.parametrize("key", [f"ci:{name}" for name in CI_LINT_CHECKS])
def test_s4_12_2_5_overrides_take_the_new_keys(tmp_path: Path, key: str) -> None:
    root = _root(
        tmp_path,
        extra=f'\n[tasks]\n[tasks.command_overrides]\n"{key}" = "echo hi"\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "tasks/ci.yml")["tasks"]
    assert tasks[key.removeprefix("ci:")]["cmds"] == ["echo hi"]


@pytest.mark.parametrize("key", OLD_CI_KEYS)
def test_s4_12_2_5_old_keys_are_refused(tmp_path: Path, key: str) -> None:
    root = _root(
        tmp_path,
        extra=f'\n[tasks]\n[tasks.command_overrides]\n"{key}" = "echo hi"\n',
    )
    with pytest.raises(AppException, match=re.escape(key)):
        TASKS.artifacts(KilnConfig.load(root), root)


@pytest.mark.parametrize("name", archetypes.shipped())
def test_s4_12_2_6_required_validate_names_the_ci_tasks(name: str) -> None:
    required = archetypes.load(name).required_validate
    for task in ("workflows",):
        assert f"ci:lint:{task}" in required
    assert not [
        r
        for r in required
        if r.startswith("quality:lint:ci-")
        or r.endswith(":workflows")
        and r.startswith("quality:")
    ]


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_s4_12_2_7_task_layout_accepts_the_rendered_files(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _s4_12_1_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    assert _codes(root) == []


@pytest.mark.parametrize("name", ["workflows"])
def test_s4_12_2_7_gate_shrunk_fires(tmp_path: Path, name: str) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    taskfile = root / "Taskfile.yml"
    line = f"      - task: ci:lint:{name}\n"
    text = taskfile.read_text(encoding="utf-8")
    assert line in text
    taskfile.write_text(text.replace(line, ""), encoding="utf-8")
    findings = list(module_findings("tasks", KilnConfig.load(root), root))
    assert any(
        f.code == "gate.shrunk" and f"ci:lint:{name}" in str(f) for f in findings
    )


def test_s4_12_2_8_an_include_cannot_take_ci(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + '\n[tasks]\nincludes = [{ namespace = "ci", taskfile = "tasks/mine.yml" }]\n',
        encoding="utf-8",
    )
    assert "taskgraph.reserved-namespace" in _codes(root)


def test_s4_12_3_1_node_yml_holds_the_toolchain(tmp_path: Path) -> None:
    root = _node_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "tasks/node.yml")["tasks"]
    assert set(tasks) == {*NODE_CHECKS, *NODE_AUDITS}
    for name, cmds in NODE_CHECKS.items():
        assert tasks[name]["internal"] is True
        assert tasks[name]["desc"].strip()
        assert tasks[name]["cmds"] == cmds
    paths = [a.path for a in TASKS.artifacts(KilnConfig.load(root), root)]
    assert paths.index("tasks/node.yml") == paths.index("tasks/web.yml") + 1
    assert _load(root, "Taskfile.yml")["includes"]["node"] == "tasks/node.yml"


def test_s4_12_3_2_web_yml_keeps_only_dev(tmp_path: Path) -> None:
    root = _node_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "tasks/web.yml")["tasks"]
    assert set(tasks) == {"dev"}
    assert tasks["dev"]["desc"] == "Run the frontend dev server."
    assert tasks["dev"]["cmds"] == ["pnpm nx serve web"]
    assert "internal" not in tasks["dev"]


def test_s4_12_3_3_the_wrappers_call_node(tmp_path: Path) -> None:
    root = _node_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "Taskfile.yml")["tasks"]
    setup = tasks["setup"]["cmds"]
    assert setup == [{"task": "python:install"}, {"task": "node:install"}]
    lint = _unmarked(tasks["lint"]["cmds"])
    assert lint[lint.index({"task": "python:lint:imports"}) + 1] == {
        "task": "node:lint"
    }
    for verb in ("test", "build"):
        assert tasks[verb]["cmds"][-1] == {"task": f"node:{verb}"}
    for task in tasks.values():
        for cmd in task["cmds"]:
            assert not cmd["task"].startswith("web:")


def test_s4_12_3_4_workspace_install_has_no_pnpm(tmp_path: Path) -> None:
    root = _node_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "tasks/workspace.yml")["tasks"]
    assert "pnpm" not in YamlUtils.serialize(tasks)
    assert any(".nx" in c for c in tasks["clean"]["cmds"])


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [(a, "") for a in ARCHETYPES] + [("python-web-api", "")],
)
def test_s4_12_3_5_only_python_web_app_renders_node_yml(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _s4_12_1_root(tmp_path, archetype, extra)
    rendered = {a.path: a.content for a in TASKS.artifacts(KilnConfig.load(root), root)}
    assert "tasks/node.yml" not in rendered
    assert "node" not in YamlUtils.load(rendered["Taskfile.yml"])["includes"]


@pytest.mark.parametrize("name", NODE_CHECKS)
def test_s4_12_3_6_overrides_take_the_node_keys(tmp_path: Path, name: str) -> None:
    root = _node_root(
        tmp_path,
        extra=f'\n[tasks]\n[tasks.command_overrides]\n"node:{name}" = "echo hi"\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    assert _load(root, "tasks/node.yml")["tasks"][name]["cmds"] == ["echo hi"]


def test_s4_12_3_6_node_lint_is_unknown_on_python_tool(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra='\n[tasks]\n[tasks.command_overrides]\n"node:lint" = "echo hi"\n',
    )
    with pytest.raises(AppException, match="node:lint"):
        TASKS.artifacts(KilnConfig.load(root), root)


def test_s4_12_3_7_node_tasks_must_be_internal(tmp_path: Path) -> None:
    root = _node_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    node = root / "tasks/node.yml"
    text = node.read_text(encoding="utf-8")
    start = text.index("  lint:\n")
    head, tail = text[:start], text[start:]
    node.write_text(
        head + tail.replace("    internal: true\n", "", 1), encoding="utf-8"
    )
    assert "taskgraph.not-internal" in _codes(root)


def test_s9_1_9_1_node_yml_adds_typecheck_and_e2e_for_node_lib(
    tmp_path: Path,
) -> None:
    root = _node_lib_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "tasks/node.yml")["tasks"]
    assert set(tasks) == {*NODE_CHECKS, *NODE_AUDITS, "version"}
    for name, cmds in NODE_CHECKS.items():
        assert tasks[name]["internal"] is True
        assert tasks[name]["desc"].strip()
        assert tasks[name]["cmds"] == cmds
    assert _load(root, "Taskfile.yml")["includes"]["node"] == "tasks/node.yml"


@pytest.mark.parametrize("name", ["typecheck", "e2e"])
def test_s9_1_9_1_node_lib_overrides_take_the_new_keys(
    tmp_path: Path, name: str
) -> None:
    config = '\n[tasks]\n[tasks.command_overrides]\n"node:{}" = "echo hi"\n'
    root = _root(tmp_path, "node-lib", extra=config.format(name))
    cycle.apply(root, home=tmp_path / "home")
    assert _load(root, "tasks/node.yml")["tasks"][name]["cmds"] == ["echo hi"]


def test_s9_1_9_2_node_lib_root_verbs_wrap_node(tmp_path: Path) -> None:
    root = _node_lib_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "Taskfile.yml")["tasks"]
    assert {"task": "node:install"} in tasks["setup"]["cmds"]
    assert {"task": "node:lint"} in tasks["lint"]["cmds"]
    assert tasks["typecheck"]["cmds"] == [{"task": "node:typecheck"}]
    assert tasks["test"]["cmds"] == [{"task": "node:test"}]
    assert tasks["test:coverage"]["cmds"] == [{"task": "node:test"}]
    assert tasks["build"]["cmds"] == [{"task": "node:build"}]
    assert {"task": "typecheck"} in tasks["validate"]["cmds"]


def test_s9_1_9_2_node_lib_calls_no_python_task_that_needs_a_package(
    tmp_path: Path,
) -> None:
    root = _node_lib_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "Taskfile.yml")["tasks"]
    called = {
        cmd["task"]
        for task in tasks.values()
        for cmd in task["cmds"]
        if isinstance(cmd, dict)
    }
    assert {t for t in called if t.startswith("python:")} <= {"python:install"}
    assert {"task": "python:format"} not in tasks["format"]["cmds"]


def test_s9_2_6_3_web_app_coverage_runs_python_then_node(tmp_path: Path) -> None:
    root = _node_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "Taskfile.yml")["tasks"]
    assert tasks["test:coverage"]["cmds"] == [
        {"task": "python:test:coverage"},
        {"task": "node:test"},
    ]


def test_s9_2_6_3_node_lib_coverage_stays_node_only(tmp_path: Path) -> None:
    root = _node_lib_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "Taskfile.yml")["tasks"]
    assert tasks["test:coverage"]["cmds"] == [{"task": "node:test"}]


def test_s9_2_6_3_python_web_api_coverage_calls_no_node(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-web-api")
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "Taskfile.yml")["tasks"]
    assert tasks["test:coverage"]["cmds"] == [{"task": "python:test:coverage"}]


def test_s9_1_9_3_node_lib_taskfile_includes_no_python_or_api(
    tmp_path: Path,
) -> None:
    root = _node_lib_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    includes = _load(root, "Taskfile.yml")["includes"]
    assert "api" not in includes
    assert "node" in includes


CI_FIRST_LEVELS = (
    "validate",
    "plan",
    "test",
    "integration",
    "smoke",
    "suites",
    "sonar",
    "release",
    "verify-release",
    "docs",
    "dist",
    "consumer",
    "secret-scan",
    "internal-ranges",
    "adapters",
)


CI_WORD = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"


CI_NAME = re.compile(rf"^ci:{CI_WORD}(?::{CI_WORD})?$")


CI_OLD_NAMES = (
    "ci:coverage",
    "ci:sonar-target",
    "ci:release-state",
    "ci:release-source",
    "ci:release-publish",
    "ci:release-build",
    "ci:release-sign",
    "ci:docs-publish",
    "ci:suite",
    "ci:lint:secrets",
    "ci:requirements",
    "ci:affected",
    "ci:has-e2e",
    "ci:playwright",
    "ci:playwright:deps",
    "ci:package",
    "ci:version",
)


def test_s17_2_1_1_grammar(tmp_path: Path) -> None:
    for archetype, root in _ci_cells(tmp_path):
        tasks = _ci_rendered(root)
        public = [n for n, t in tasks.items() if not t.get("internal")]
        assert public, archetype
        for name in public:
            full = f"ci:{name}"
            assert CI_NAME.match(full), (archetype, full)
            first = name.split(":")[0]
            assert first in CI_FIRST_LEVELS, (archetype, full)
            assert tasks[name]["desc"].startswith("CI only: "), (archetype, full)
            sentence = tasks[name]["desc"].removeprefix("CI only: ")
            assert sentence[0].isupper() and sentence.endswith("."), (archetype, full)


def test_s17_2_1_2_one_name_per_idea(tmp_path: Path) -> None:
    for archetype, root in _ci_cells(tmp_path):
        names = {f"ci:{name}" for name in _ci_rendered(root)}
        assert not names & set(CI_OLD_NAMES), (archetype, names & set(CI_OLD_NAMES))
        files = {
            p: p.read_text(encoding="utf-8")
            for p in (root / "tasks").glob("*.yml")
            if p.name != "ci.yml"
        }
        for path, text in files.items():
            used = set(re.findall(r"ci:[\w:-]+", text))
            assert not used & set(CI_OLD_NAMES), (archetype, path.name)
    node = _ci_rendered(_secrets_root(tmp_path / "node", "node-lib"))
    assert "version" not in node
    node_yml = YamlUtils.load(
        (tmp_path / "node" / "tasks/node.yml").read_text(encoding="utf-8")
    )
    assert node_yml["tasks"]["version"]["internal"] is True
    root_yml = YamlUtils.load(
        (tmp_path / "node" / "Taskfile.yml").read_text(encoding="utf-8")
    )
    assert {"task": "node:version"} in root_yml["tasks"]["version"]["cmds"]


def test_s17_2_1_3_workflows_call_the_new_names(tmp_path: Path) -> None:
    for archetype, root in _ci_cells(tmp_path):
        files = [p for p in (root / ".github").rglob("*") if p.is_file()]
        assert files, archetype
        for path in files:
            used = set(re.findall(r"ci:[\w:-]+", path.read_text(encoding="utf-8")))
            assert not used & set(CI_OLD_NAMES), (archetype, path.name)
