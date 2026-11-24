"""The rules `task-layout` once applied to kiln's rendered Taskfiles.

They hold over every rendered cell, so they are render tests, not doctor
findings.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle, umbrella
from rn_forge.kiln.modules.core.steps import step_commands
from rn_forge.kiln.modules.tasks.config import ROOT_VERBS, WEB_APP_VERBS
from rn_forge.kiln.modules.tasks.taskfile import include_map, task_refs, task_specs
from tests.modules.tasks import graph as taskgraph
from tests.modules.tasks.support import (
    RENDER_CELLS,
    _ci_root,
    _load,
    _node_lib_root,
)

REACH_CELLS = [
    *RENDER_CELLS,
    ("python-app", "\n[ci.checks]\nlicenses = true\n"),
    ("python-app", '\n[tasks]\n[tasks.extra_refs]\nvalidate = ["workspace:clean"]\n'),
]


def _applied(tmp_path: Path, archetype: str, extra: str) -> Path:
    if archetype == "node-lib":
        root = _node_lib_root(tmp_path)
    else:
        root = _ci_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    return root


def _managed_files(root: Path) -> list[str]:
    document = _load(root, "Taskfile.yml")
    return sorted(include_map(document).values())


@pytest.mark.parametrize(("archetype", "extra"), RENDER_CELLS)
def test_the_root_taskfile_holds_exactly_the_root_verbs(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _applied(tmp_path, archetype, extra)
    expected = ROOT_VERBS + (WEB_APP_VERBS if archetype == "python-web-app" else ())
    assert sorted(task_specs(_load(root, "Taskfile.yml"))) == sorted(expected)


@pytest.mark.parametrize(("archetype", "extra"), RENDER_CELLS)
def test_every_task_has_a_desc(tmp_path: Path, archetype: str, extra: str) -> None:
    root = _applied(tmp_path, archetype, extra)
    for path in ["Taskfile.yml", *_managed_files(root)]:
        for name, spec in task_specs(_load(root, path)).items():
            assert str(spec.get("desc", "")).strip(), f"{path}: {name}"  # type: ignore[union-attr]


@pytest.mark.parametrize(("archetype", "extra"), RENDER_CELLS)
def test_the_root_taskfile_holds_wrappers_only(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _applied(tmp_path, archetype, extra)
    for name, spec in task_specs(_load(root, "Taskfile.yml")).items():
        assert isinstance(spec, dict), name
        for entry in spec.get("cmds", []):
            assert isinstance(entry, dict) and "task" in entry, (name, entry)


@pytest.mark.parametrize(("archetype", "extra"), RENDER_CELLS)
def test_inner_tasks_are_internal(tmp_path: Path, archetype: str, extra: str) -> None:
    root = _applied(tmp_path, archetype, extra)
    includes = include_map(_load(root, "Taskfile.yml"))
    for namespace, path in includes.items():
        if namespace not in taskgraph.RESERVED_NAMESPACES:
            continue
        for name, spec in task_specs(_load(root, path)).items():
            if namespace == "kiln" and name in taskgraph.PUBLIC_KILN_TASKS:
                continue
            assert spec.get("internal") is True, f"{namespace}:{name}"  # type: ignore[union-attr]


@pytest.mark.parametrize(("archetype", "extra"), RENDER_CELLS)
def test_every_task_reference_resolves(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _applied(tmp_path, archetype, extra)
    graph, namespaces = taskgraph.load_graph(root)
    for name, spec in graph.items():
        prefix = name.split(":", 1)[0]
        namespace = prefix if prefix in namespaces else None
        for ref in task_refs(spec):
            if "{{" in ref or "$" in ref:
                continue
            assert taskgraph.resolve(ref, namespace, graph) in graph, (name, ref)


@pytest.mark.parametrize(("archetype", "extra"), RENDER_CELLS)
def test_the_task_graph_has_no_cycle(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _applied(tmp_path, archetype, extra)
    graph, namespaces = taskgraph.load_graph(root)
    edges: dict[str, list[str]] = {}
    for name, spec in graph.items():
        prefix = name.split(":", 1)[0]
        namespace = prefix if prefix in namespaces else None
        resolved = (taskgraph.resolve(ref, namespace, graph) for ref in task_refs(spec))
        edges[name] = [ref for ref in resolved if ref in graph]
    done: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        assert node not in stack, " -> ".join([*stack, node])
        if node in done:
            return
        for target in edges[node]:
            visit(target, [*stack, node])
        done.add(node)

    for node in sorted(edges):
        visit(node, [])


@pytest.mark.parametrize(("archetype", "extra"), REACH_CELLS)
def test_every_required_validate_task_is_reachable_from_validate(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _applied(tmp_path, archetype, extra)
    config = KilnConfig.load(root)
    graph, namespaces = taskgraph.load_graph(root)
    reachable = taskgraph.reachable_from("validate", graph, namespaces)
    required = set(archetypes.for_config(config).required_validate)
    assert required <= reachable, required - reachable


@pytest.mark.parametrize(("archetype", "extra"), RENDER_CELLS)
def test_managed_workflows_and_blocks_call_existing_tasks(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _applied(tmp_path, archetype, extra)
    graph, _ = taskgraph.load_graph(root)
    entries = DocumentUtils.read(root / umbrella.STATE_PATH)["entries"]
    missing: list[str] = []
    for entry in entries.values():
        relative = str(entry.get("path", ""))
        path = root / relative
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        kind = entry.get("kind")
        if kind == "managed" and relative.startswith(".github/"):
            texts = [text for _, text in step_commands(lines, ("run",))]
        elif kind == "block" and entry.get("begin_marker") and entry.get("end_marker"):
            begin = str(entry["begin_marker"]).strip()
            end = str(entry["end_marker"]).strip()
            texts, inside = [], False
            for text in lines:
                if text.strip() == end:
                    inside = False
                elif inside:
                    texts.append(text)
                elif text.strip() == begin:
                    inside = True
        else:
            continue
        missing += [f"{relative}: {n}" for n in taskgraph.unresolved_in(texts, graph)]
    assert missing == []
