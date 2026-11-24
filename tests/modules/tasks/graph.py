"""The rendered task graph, read from disk, for the render tests."""

from __future__ import annotations

import re
from pathlib import Path

from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.modules.tasks.taskfile import include_map, task_refs, task_specs

ROOT_TASKFILE = Path("Taskfile.yml")

RESERVED_NAMESPACES = frozenset({"quality", "workspace", "node", "python", "kiln"})
"""Namespaces whose tasks are inner implementation and must be `internal`."""

PUBLIC_KILN_TASKS = frozenset({"diff", "apply", "pin", "upgrade"})
"""The `kiln:` tasks that are public: the rest of the namespace stays internal."""

TASK_CALL = re.compile(r"(?:^|[;&|(]\s*|\s)task\s+([A-Za-z][\w:-]*)")


def _load_yaml(path: Path) -> object:
    return YamlUtils.read_file(path, encoding="utf-8")


def load_graph(root: Path) -> tuple[dict[str, object], set[str]]:
    """Every task keyed by fully qualified name, and the namespaces in use.

    Read from the root file's `includes:`; an include whose file is absent
    contributes no tasks.
    """
    document = _load_yaml(root / ROOT_TASKFILE)
    graph: dict[str, object] = dict(task_specs(document))
    includes = include_map(document)
    for namespace, path in includes.items():
        if (root / path).is_file():
            for name, spec in task_specs(_load_yaml(root / path)).items():
                graph[f"{namespace}:{name}"] = spec
    return graph, set(includes)


def resolve(ref: str, namespace: str | None, graph: dict[str, object]) -> str:
    """Normalise a `task:` reference to a fully qualified name.

    A leading `:` is go-task's "from the root Taskfile" prefix. Inside a
    namespace file an unprefixed reference means a sibling task first, and only
    then a root-level one.
    """
    if ref.startswith(":"):
        return ref[1:]
    if namespace is not None and f"{namespace}:{ref}" in graph:
        return f"{namespace}:{ref}"
    return ref


def reachable_from(
    entrypoint: str, graph: dict[str, object], namespaces: set[str]
) -> set[str]:
    """Every task reachable from *entrypoint* by following `task:` calls."""
    seen: set[str] = set()
    frontier = [entrypoint]
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        prefix = current.split(":", 1)[0]
        namespace = prefix if prefix in namespaces else None
        frontier.extend(
            resolve(ref, namespace, graph) for ref in task_refs(graph.get(current))
        )
    return seen


def unresolved_in(lines: list[str], graph: dict[str, object]) -> list[str]:
    """The `task <name>` calls in *lines* that name no task in *graph*."""
    return [
        match.group(1)
        for text in lines
        for match in TASK_CALL.finditer(text)
        if match.group(1) not in graph
    ]
