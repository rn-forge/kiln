"""`task-layout` — the wrapper/inner split, and the validate gate.

Three rules:

1. The root `Taskfile.yml` holds wrappers only. Every `cmds:` entry in it must
   be a `task:` call into a namespace file, never raw shell. Anything that
   shells out to a real tool belongs in the namespace file that owns it.
2. Every task, in the root file and in every `tasks/*.yml`, carries a non-empty
   `desc:`, so `task --list` stays self-documenting.
3. Every task in the archetype's `required_validate` list is reachable from
   `validate`.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln import archetypes, documents
from rn_forge.kiln.config import KilnConfig

__all__ = ["CODE", "NAME", "check"]

NAME = "task-layout"
CODE = "taskgraph"

ROOT_TASKFILE = Path("Taskfile.yml")
NAMESPACE_DIR = Path("tasks")


def task_specs(document: object) -> dict[str, object]:
    """The `tasks:` mapping of a Taskfile, or empty if there isn't one."""
    return documents.table(document, "tasks")


def _check_desc(label: str, name: str, spec: object) -> list[Finding]:
    if str(documents.mapping(spec).get("desc", "")).strip():
        return []
    return [
        Finding(
            f"{CODE}.no-desc",
            Severity.ERROR,
            f"task `{name}` has no non-empty `desc:`",
            path=label,
        )
    ]


def _check_wrapper_only(label: str, name: str, spec: object) -> list[Finding]:
    """Every cmds entry in the root file must be a `task:` call."""
    # `name: echo hi` and `name: [a, b]` are go-task shorthand for raw shell.
    if isinstance(spec, str | list):
        return [
            Finding(
                f"{CODE}.not-a-wrapper",
                Severity.ERROR,
                f"task `{name}` is shorthand for a raw shell command — the root "
                f"file holds wrappers only",
                path=label,
            )
        ]
    findings: list[Finding] = []
    for index, entry in enumerate(
        documents.sequence(documents.mapping(spec).get("cmds"))
    ):
        if "task" in documents.mapping(entry):
            continue
        shown = entry if isinstance(entry, str) else type(entry).__name__
        findings.append(
            Finding(
                f"{CODE}.not-a-wrapper",
                Severity.ERROR,
                f"task `{name}` cmds[{index}] is not a `task:` call ({shown!r}) "
                f"— move the command into the namespace file that owns it and "
                f"call it from here",
                path=label,
            )
        )
    return findings


def task_refs(spec: object) -> list[str]:
    """The `task:` targets a task calls, in order."""
    refs: list[str] = []
    for entry in documents.sequence(documents.mapping(spec).get("cmds")):
        target = documents.mapping(entry).get("task")
        if isinstance(target, str):
            refs.append(target)
    return refs


def load_graph(root: Path) -> tuple[dict[str, object], set[str]]:
    """Every task keyed by fully qualified name, and the namespaces in use."""
    graph: dict[str, object] = {}
    for name, spec in task_specs(
        yaml.safe_load((root / ROOT_TASKFILE).read_text(encoding="utf-8"))
    ).items():
        graph[name] = spec

    namespaces: set[str] = set()
    for namespace_file in sorted((root / NAMESPACE_DIR).glob("*.yml")):
        namespace = namespace_file.stem
        namespaces.add(namespace)
        for name, spec in task_specs(
            yaml.safe_load(namespace_file.read_text(encoding="utf-8"))
        ).items():
            graph[f"{namespace}:{name}"] = spec

    return graph, namespaces


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


def _check_gate(
    graph: dict[str, object], namespaces: set[str], required: tuple[str, ...]
) -> list[Finding]:
    label = ROOT_TASKFILE.as_posix()
    if "validate" not in graph:
        return [
            Finding(
                f"{CODE}.no-gate",
                Severity.ERROR,
                "no `validate` task — the aggregate gate is missing",
                path=label,
            )
        ]
    reachable = reachable_from("validate", graph, namespaces)
    return [
        Finding(
            "gate.shrunk",
            Severity.ERROR,
            f"`{name}` is not reachable from `validate` — the gate has shrunk",
            path=label,
        )
        for name in required
        if name not in reachable
    ]


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Hold the task graph to the vocabulary's shape and the archetype's gate."""
    root_taskfile = root / ROOT_TASKFILE
    if not root_taskfile.exists():
        return [
            Finding(
                f"{CODE}.missing",
                Severity.ERROR,
                "not found",
                path=ROOT_TASKFILE.as_posix(),
            )
        ]

    findings: list[Finding] = []
    label = ROOT_TASKFILE.as_posix()
    for name, spec in task_specs(
        yaml.safe_load(root_taskfile.read_text(encoding="utf-8"))
    ).items():
        findings.extend(_check_desc(label, name, spec))
        findings.extend(_check_wrapper_only(label, name, spec))

    for namespace_file in sorted((root / NAMESPACE_DIR).glob("*.yml")):
        namespace_label = namespace_file.relative_to(root).as_posix()
        for name, spec in task_specs(
            yaml.safe_load(namespace_file.read_text(encoding="utf-8"))
        ).items():
            findings.extend(_check_desc(namespace_label, name, spec))

    graph, namespaces = load_graph(root)
    findings.extend(
        _check_gate(
            graph, namespaces, tuple(archetypes.for_config(config).required_validate)
        )
    )
    return findings
