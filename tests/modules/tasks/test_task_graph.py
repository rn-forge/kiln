"""The `tasks` module's artifacts: `Taskfile.yml`, `tasks/*.yml`, includes.

Also proves the properties every concern module owes: its template inventory,
create-only apply into an empty directory, idempotence, and passing checks.
"""

from __future__ import annotations
import json
import pytest
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.commons.generation import Action, ArtifactKind
from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS
from rn_forge.kiln.modules.tasks.checks import layout
from tests.conftest import actions as _actions
from tests.modules.tasks.support import (
    ARCHETYPES,
    STEP,
    _ci_tasks,
    _codes,
    _load,
    _node_lib_root,
    _root,
    _run_task,
    _unmarked,
)


TASK_KEYS = (
    "Taskfile.yml",
    "tasks/workspace.yml",
    "tasks/quality.yml",
    "tasks/python.yml",
    "tasks/kiln.yml",
    "tasks/docs.yml",
)


CI_KEY = "tasks/ci.yml"


SONAR_KEY = "tasks/sonar.yml"


INCLUDE_EXTRA = (
    '\n[tasks]\nincludes = [{ namespace = "extra", taskfile = "tasks/extra.yml" }]\n'
)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_renders_exactly_the_module_s_template_inventory_rows(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    artifacts = TASKS.artifacts(KilnConfig.load(root), root)
    assert [(a.path, a.kind) for a in artifacts] == [
        (path, ArtifactKind.MANAGED) for path in (*TASK_KEYS, CI_KEY, SONAR_KEY)
    ]


def test_without_mkdocs_omits_docs_yml(tmp_path: Path) -> None:
    root = _root(tmp_path, profile="none")
    artifacts = TASKS.artifacts(KilnConfig.load(root), root)
    assert [a.path for a in artifacts] == [*TASK_KEYS[:-1], CI_KEY, SONAR_KEY]


def test_one_seeded_artifact_per_include(tmp_path: Path) -> None:
    root = _root(tmp_path, extra=INCLUDE_EXTRA)
    artifacts = TASKS.artifacts(KilnConfig.load(root), root)
    assert [a.path for a in artifacts] == [
        *TASK_KEYS,
        CI_KEY,
        SONAR_KEY,
        "tasks/extra.yml",
    ]
    assert artifacts[-1].kind is ArtifactKind.SEEDED


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_into_an_empty_directory_only_creates(tmp_path: Path, archetype: str) -> None:
    actions = _actions(_root(tmp_path, archetype), tmp_path)
    tasks_actions = {key: actions[key] for key in (*TASK_KEYS, CI_KEY, SONAR_KEY)}
    assert set(tasks_actions.values()) == {Action.CREATE}


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_a_second_apply_is_unchanged(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    actions = _actions(root, tmp_path)
    assert all(
        actions[key] is Action.UNCHANGED for key in (*TASK_KEYS, CI_KEY, SONAR_KEY)
    )


def test_an_include_reports_skip_once_present(tmp_path: Path) -> None:
    root = _root(tmp_path, extra=INCLUDE_EXTRA)
    cycle.apply(root, home=tmp_path / "home")
    assert _actions(root, tmp_path)["tasks/extra.yml"] is Action.SKIP


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_task_layout_passes_on_the_rendered_output(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    assert _codes(root) == []


def test_task_layout_fails_on_a_broken_gate(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    taskfile = root / "Taskfile.yml"
    taskfile.write_text(
        taskfile.read_text(encoding="utf-8").replace("      - task: python:test\n", ""),
        encoding="utf-8",
    )
    assert "gate.shrunk" in _codes(root)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_lint_and_format_run_taplo(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    quality = YamlUtils.load((root / "tasks/quality.yml").read_text(encoding="utf-8"))
    assert quality["tasks"]["lint:toml"]["cmds"] == [
        "{{.FILES}} '*.toml' | xargs -0 -r uv run taplo fmt --check"
    ]
    assert quality["tasks"]["format:toml"]["cmds"] == [
        "{{.FILES}} '*.toml' | xargs -0 -r uv run taplo fmt"
    ]
    tasks = YamlUtils.load((root / "Taskfile.yml").read_text(encoding="utf-8"))["tasks"]
    assert {"task": "quality:lint:toml"} in tasks["lint"]["cmds"]
    assert {"task": "quality:format:toml"} in tasks["format"]["cmds"]


def _graph_roots(tmp_path: Path) -> list[Path]:
    roots = [_root(tmp_path / a, a) for a in ARCHETYPES]
    return [*roots, _node_lib_root(tmp_path / "node-lib")]


def test_markdown_tasks_run_in_batches(tmp_path: Path) -> None:
    batch = "{{.FILES}} '*.md' | xargs -0 -r -n 20 -P 4 uv run --group docs mdformat"
    for root in _graph_roots(tmp_path):
        cycle.apply(root, home=tmp_path / "home")
        tasks = _load(root, "tasks/quality.yml")["tasks"]
        assert tasks["lint:markdown"]["cmds"] == [f"{batch} --check"]
        assert tasks["format:markdown"]["cmds"] == [batch]


def test_toml_tasks_stay_serial(tmp_path: Path) -> None:
    for root in _graph_roots(tmp_path):
        cycle.apply(root, home=tmp_path / "home")
        tasks = _load(root, "tasks/quality.yml")["tasks"]
        assert tasks["lint:toml"]["cmds"] == [
            "{{.FILES}} '*.toml' | xargs -0 -r uv run taplo fmt --check"
        ]
        assert tasks["format:toml"]["cmds"] == [
            "{{.FILES}} '*.toml' | xargs -0 -r uv run taplo fmt"
        ]


def test_an_override_still_replaces_the_batch(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra='\n[tasks]\n[tasks.command_overrides]\n"quality:lint:markdown" = "echo hi"\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "tasks/quality.yml")["tasks"]
    assert tasks["lint:markdown"]["cmds"] == ["echo hi"]
    assert "-n 20 -P 4" in tasks["format:markdown"]["cmds"][0]


YAML_LINT = "{{.FILES}} '*.yml' '*.yaml' | xargs -0 -r uv run yamlfmt -lint"


YAML_FORMAT = "{{.FILES}} '*.yml' '*.yaml' | xargs -0 -r uv run yamlfmt"


def test_lint_and_format_run_the_yaml_formatter(tmp_path: Path) -> None:
    for root in _graph_roots(tmp_path):
        cycle.apply(root, home=tmp_path / "home")
        tasks = _load(root, "tasks/quality.yml")["tasks"]
        assert tasks["lint:yaml"]["cmds"] == [YAML_LINT]
        assert tasks["format:yaml"]["cmds"] == [YAML_FORMAT]
        for name in ("lint:yaml", "format:yaml"):
            assert tasks[name]["internal"] is True
            assert tasks[name]["desc"]


def test_the_root_verbs_call_the_pair(tmp_path: Path) -> None:
    for root in _graph_roots(tmp_path):
        cycle.apply(root, home=tmp_path / "home")
        tasks = _load(root, "Taskfile.yml")["tasks"]
        for verb, kind in (("lint", "lint"), ("format", "format")):
            cmds = _unmarked(tasks[verb]["cmds"])
            toml = cmds.index({"task": f"quality:{kind}:toml"})
            assert cmds[toml + 1] == {"task": f"quality:{kind}:yaml"}
        assert "YAML" in tasks["lint"]["desc"]


def test_an_override_replaces_one_task(tmp_path: Path) -> None:
    for kept, replaced in (("format", "lint"), ("lint", "format")):
        root = _root(
            tmp_path / replaced,
            extra=f'\n[tasks]\n[tasks.command_overrides]\n"quality:{replaced}:yaml" = "echo hi"\n',
        )
        cycle.apply(root, home=tmp_path / "home")
        tasks = _load(root, "tasks/quality.yml")["tasks"]
        assert tasks[f"{replaced}:yaml"]["cmds"] == ["echo hi"]
        assert tasks[f"{kept}:yaml"]["cmds"] == [
            YAML_LINT if kept == "lint" else YAML_FORMAT
        ]


def test_the_node_lib_ci_validate_runs_it(tmp_path: Path) -> None:
    cmds = _ci_tasks(_node_lib_root(tmp_path))["tasks"]["validate"]["cmds"]  # type: ignore[index]
    toml = cmds.index({"task": ":quality:lint:toml"})
    assert cmds[toml + 1] == {"task": ":quality:lint:yaml"}


BANNER = "workspace:banner"


RULE = "=" * 72


def test_validate_prints_a_banner_before_each_step(tmp_path: Path) -> None:
    for root in _graph_roots(tmp_path):
        cycle.apply(root, home=tmp_path / "home")
        cmds = _load(root, "Taskfile.yml")["tasks"]["validate"]["cmds"]
        steps = [c["task"] for c in cmds if c["task"] != BANNER]
        assert cmds == [
            entry
            for n, step in enumerate(steps, 1)
            for entry in (
                {"task": BANNER, "vars": {"STEP": step, "N": n, "OF": len(steps)}},
                {"task": step},
            )
        ]
        assert steps[:3] == ["lint", "typecheck", "test"]


def test_the_banner_task(tmp_path: Path) -> None:
    for root in _graph_roots(tmp_path):
        cycle.apply(root, home=tmp_path / "home")
        assert _load(root, "tasks/workspace.yml")["tasks"]["banner"] == {
            "desc": "Print a banner naming the step that follows (STEP), numbered N of OF.",
            "internal": True,
            "silent": True,
            "requires": {"vars": ["STEP", "N", "OF"]},
            "cmds": [
                f"printf '\\n{RULE}\\n### [%s/%s] %s\\n{RULE}\\n'"
                " '{{.N}}' '{{.OF}}' '{{.STEP}}'"
            ],
        }


def test_the_step_task(tmp_path: Path) -> None:
    for root in _graph_roots(tmp_path):
        cycle.apply(root, home=tmp_path / "home")
        assert _load(root, "tasks/workspace.yml")["tasks"]["step"] == {
            "desc": "Print a one-line marker naming the sub-step that follows (STEP), numbered N of OF.",
            "internal": True,
            "silent": True,
            "requires": {"vars": ["STEP", "N", "OF"]},
            "cmds": ["printf '\\n--- [%s/%s] %s\\n' '{{.N}}' '{{.OF}}' '{{.STEP}}'"],
        }


def test_lint_prints_a_marker_before_each_step(tmp_path: Path) -> None:
    for root in _graph_roots(tmp_path):
        cycle.apply(root, home=tmp_path / "home")
        cmds = _load(root, "Taskfile.yml")["tasks"]["lint"]["cmds"]
        steps = [c["task"] for c in cmds if c["task"] != STEP]
        assert cmds == [
            entry
            for n, step in enumerate(steps, 1)
            for entry in (
                {"task": STEP, "vars": {"STEP": step, "N": n, "OF": len(steps)}},
                {"task": step},
            )
        ]


def test_extra_steps_get_a_banner(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra='\n[tasks]\n[tasks.extra_refs]\nvalidate = ["workspace:clean"]\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    cmds = _load(root, "Taskfile.yml")["tasks"]["validate"]["cmds"]
    assert cmds[-2:] == [
        {"task": BANNER, "vars": {"STEP": "workspace:clean", "N": 5, "OF": 5}},
        {"task": "workspace:clean"},
    ]


def test_the_gate_still_passes_the_layout_check(tmp_path: Path) -> None:
    for root in _graph_roots(tmp_path):
        cycle.apply(root, home=tmp_path / "home")
        assert _codes(root) == []
        graph, namespaces = layout.load_graph(root)
        assert BANNER in layout.reachable_from("validate", graph, namespaces)


def test_ci_validate_is_unchanged(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    validate = _ci_tasks(root)["tasks"]["validate"]
    assert all(entry.get("task") != BANNER for entry in validate["cmds"])


@pytest.mark.parametrize("name", archetypes.shipped())
def test_lint_toml_is_a_required_gate(name: str) -> None:
    assert "quality:lint:toml" in archetypes.load(name).required_validate


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_task_list_json_lists_exactly_the_ten_root_verbs(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype, profile="none")
    cycle.apply(root, home=tmp_path / "home")
    result = _run_task(root, "--list", "--json")
    assert result.returncode == 0, result.stderr
    names = {
        entry["name"]
        for entry in json.loads(result.stdout)["tasks"]
        if not entry["name"].startswith(("ci:", "kiln:", "sonar:"))
    }
    assert names == {
        "setup",
        "validate",
        "lint",
        "format",
        "typecheck",
        "test",
        "test:coverage",
        "build",
        "version",
        "clean",
    }


def test_an_mkdocs_repo_also_lists_the_three_docs_verbs(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    result = _run_task(root, "--list", "--json")
    assert result.returncode == 0, result.stderr
    names = {entry["name"] for entry in json.loads(result.stdout)["tasks"]}
    assert {n for n in names if n.startswith("docs:")} == {
        "docs:build",
        "docs:serve",
        "docs:generate",
    }
    assert "docs:structure" not in names


def test_a_repo_owned_include_is_seeded_once_and_list_all_succeeds(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, extra=INCLUDE_EXTRA)
    cycle.apply(root, home=tmp_path / "home")
    include = root / "tasks" / "extra.yml"
    assert include.is_file()
    result = _run_task(root, "--list-all")
    assert result.returncode == 0, result.stderr


def test_an_edit_to_an_include_survives_apply(tmp_path: Path) -> None:
    root = _root(tmp_path, extra=INCLUDE_EXTRA)
    cycle.apply(root, home=tmp_path / "home")
    include = root / "tasks" / "extra.yml"
    edited = include.read_text(encoding="utf-8") + "  hand-written: true\n"
    include.write_text(edited, encoding="utf-8")
    assert _actions(root, tmp_path)["tasks/extra.yml"] is Action.SKIP
    cycle.apply(root, home=tmp_path / "home")
    assert include.read_text(encoding="utf-8") == edited


def test_an_extra_ref_is_reachable_from_validate(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra='\n[tasks]\n[tasks.extra_refs]\nvalidate = ["workspace:clean"]\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    graph, namespaces = layout.load_graph(root)
    assert "workspace:clean" in layout.reachable_from("validate", graph, namespaces)
    assert _codes(root) == []


def test_an_unknown_extra_ref_key_fails_config_load(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra='\n[tasks]\n[tasks.extra_refs]\nbogus = ["workspace:clean"]\n',
    )
    with pytest.raises(AppException) as excinfo:
        KilnConfig.load(root)
    assert "tasks.extra_refs.bogus" in str(excinfo.value)


def test_a_command_override_replaces_only_that_task_s_cmds(
    tmp_path: Path,
) -> None:
    plain = _root(tmp_path / "plain")
    overridden = _root(
        tmp_path / "overridden",
        extra=('\n[tasks]\n[tasks.command_overrides]\n"python:test" = "echo hi"\n'),
    )
    before = {a.path: a.content for a in TASKS.artifacts(KilnConfig.load(plain), plain)}
    after = {
        a.path: a.content
        for a in TASKS.artifacts(KilnConfig.load(overridden), overridden)
    }
    assert "cmds:\n      - echo hi\n" in after["tasks/python.yml"]
    for path in (
        "Taskfile.yml",
        "tasks/workspace.yml",
        "tasks/quality.yml",
        "tasks/docs.yml",
    ):
        assert after[path] == before[path]


def test_an_unknown_override_key_raises_naming_it(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra='\n[tasks]\n[tasks.command_overrides]\nbogus = "echo hi"\n',
    )
    config = KilnConfig.load(root)
    with pytest.raises(AppException, match="bogus"):
        TASKS.artifacts(config, root)
