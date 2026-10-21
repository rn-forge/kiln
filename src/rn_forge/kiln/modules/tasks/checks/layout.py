"""`task-layout` — the wrapper/inner split, and the validate gate.

Three rules:

1. The root `Taskfile.yml` holds wrappers only. Every `cmds:` entry in it must
   be a `task:` call into a namespace file, never raw shell. Anything that
   shells out to a real tool belongs in the namespace file that owns it.
2. Every task, in the root file and in every `tasks/*.yml`, carries a non-empty
   `desc:`, so `task --list` stays self-documenting.
3. Every task in the archetype's `required_validate` list is reachable from
   `validate`.

The graph rules (S4.6.2) read the root file's `includes:`. Layout rules apply
to the root file and to *managed* includes; an include that
`config.tasks.includes` declares is repository-owned, sits in the graph so that
references into it resolve, and is otherwise left alone.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln import archetypes, documents
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.tasks.config import ROOT_VERBS, TasksConfig

__all__ = ["CODE", "NAME", "check"]

NAME = "task-layout"
CODE = "taskgraph"

ROOT_TASKFILE = Path("Taskfile.yml")
STATE_PATH = Path(".rn-forge/kiln/state.json")

RESERVED_NAMESPACES = frozenset({"quality", "workspace", "node"})
"""Namespaces whose tasks are inner implementation and must be `internal`."""

_TASK_CALL = re.compile(r"(?:^|[;&|(]\s*|\s)task\s+([A-Za-z][\w:-]*)")
_RUN_LINE = re.compile(r"^(\s*)(?:- )?run:\s*(.*)$")
_BLOCK_SCALAR = re.compile(r"^[|>][+-]?\d*$")


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


def include_map(document: object) -> dict[str, str]:
    """The root file's `includes:`, namespace to path (posix, no `./`)."""
    includes: dict[str, str] = {}
    for namespace, value in documents.table(document, "includes").items():
        path = (
            value
            if isinstance(value, str)
            else documents.mapping(value).get("taskfile")
        )
        if isinstance(path, str):
            includes[namespace] = Path(path).as_posix()
    return includes


def _load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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


def _namespace_of(name: str, namespaces: set[str]) -> str | None:
    prefix = name.split(":", 1)[0]
    return prefix if prefix in namespaces else None


def _owner_file(name: str, includes: dict[str, str]) -> str:
    namespace = _namespace_of(name, set(includes))
    return includes[namespace] if namespace else ROOT_TASKFILE.as_posix()


def _check_surface(root_tasks: dict[str, object]) -> list[Finding]:
    label = ROOT_TASKFILE.as_posix()
    findings = [
        Finding(
            f"{CODE}.surface",
            Severity.ERROR,
            f"root task `{name}` is not one of the ten root verbs "
            f"({', '.join(ROOT_VERBS)})",
            path=label,
        )
        for name in root_tasks
        if name not in ROOT_VERBS
    ]
    findings.extend(
        Finding(
            f"{CODE}.surface",
            Severity.ERROR,
            f"root verb `{verb}` is missing",
            path=label,
        )
        for verb in ROOT_VERBS
        if verb not in root_tasks
    )
    return findings


def _check_internal(path: str, name: str, spec: object) -> list[Finding]:
    if documents.mapping(spec).get("internal") is True:
        return []
    return [
        Finding(
            f"{CODE}.not-internal",
            Severity.ERROR,
            f"task `{name}` is inner implementation and must be `internal: true`",
            path=path,
        )
    ]


def _check_includes(
    root: Path, includes: dict[str, str], tasks_config: TasksConfig, managed: set[str]
) -> list[Finding]:
    findings = [
        Finding(
            f"{CODE}.missing-include",
            Severity.ERROR,
            f"include `{namespace}` points at `{path}`, which does not exist",
            path=ROOT_TASKFILE.as_posix(),
        )
        for namespace, path in includes.items()
        if not (root / path).is_file()
    ]
    findings.extend(
        Finding(
            f"{CODE}.reserved-namespace",
            Severity.ERROR,
            f"tasks.includes namespace `{include.namespace}` collides with a "
            f"namespace kiln owns",
            path=".rn-forge/kiln/config.toml",
        )
        for include in tasks_config.includes
        if include.namespace in managed | RESERVED_NAMESPACES
    )
    return findings


def _check_refs(
    graph: dict[str, object], includes: dict[str, str], owned: set[str]
) -> list[Finding]:
    namespaces = set(includes)
    findings: list[Finding] = []
    for name, spec in graph.items():
        namespace = _namespace_of(name, namespaces)
        if namespace in owned:
            continue
        for ref in task_refs(spec):
            if "{{" in ref or "$" in ref:
                continue  # dynamic; cannot be verified
            if resolve(ref, namespace, graph) not in graph:
                findings.append(
                    Finding(
                        f"{CODE}.unresolved",
                        Severity.ERROR,
                        f"task `{name}` calls `{ref}`, which does not exist",
                        path=_owner_file(name, includes),
                    )
                )
    return findings


def _check_cycles(
    graph: dict[str, object], includes: dict[str, str], owned: set[str]
) -> list[Finding]:
    namespaces = set(includes)
    edges: dict[str, list[str]] = {}
    for name, spec in graph.items():
        namespace = _namespace_of(name, namespaces)
        resolved = (resolve(ref, namespace, graph) for ref in task_refs(spec))
        edges[name] = [ref for ref in resolved if ref in graph]

    findings: list[Finding] = []
    reported: set[frozenset[str]] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in stack:
            cycle = [*stack[stack.index(node) :], node]
            key = frozenset(cycle)
            if key not in reported and any(
                _namespace_of(member, namespaces) not in owned for member in cycle
            ):
                reported.add(key)
                findings.append(
                    Finding(
                        f"{CODE}.cycle",
                        Severity.ERROR,
                        f"task reference cycle: {' -> '.join(cycle)}",
                        path=_owner_file(cycle[0], includes),
                    )
                )
            return
        if node in visited:
            return
        visited.add(node)
        for target in edges[node]:
            visit(target, [*stack, node])

    for node in sorted(edges):
        visit(node, [])
    return findings


def _unresolved_in(
    label: str, lines: list[str], first_line: int, graph: dict[str, object]
) -> list[Finding]:
    findings: list[Finding] = []
    for offset, text in enumerate(lines):
        for match in _TASK_CALL.finditer(text):
            name = match.group(1)
            if name not in graph:
                findings.append(
                    Finding(
                        f"{CODE}.unresolved-ref",
                        Severity.ERROR,
                        f"`task {name}` does not exist",
                        path=label,
                        line=first_line + offset,
                    )
                )
    return findings


def _run_values(lines: list[str]) -> list[tuple[int, str]]:
    """Every `run:` value as (1-indexed line, text), block scalars line by line."""
    values: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        match = _RUN_LINE.match(lines[index])
        index += 1
        if not match:
            continue
        indent, remainder = match.groups()
        if remainder and not _BLOCK_SCALAR.match(remainder.strip()):
            values.append((index, remainder))
            continue
        while index < len(lines):
            line = lines[index]
            if line.strip() and len(line) - len(line.lstrip()) <= len(indent):
                break
            values.append((index + 1, line))
            index += 1
    return values


def _check_owned_text(root: Path, graph: dict[str, object]) -> list[Finding]:
    """`task <name>` in managed workflows and managed blocks must resolve."""
    state_path = root / STATE_PATH
    if not state_path.exists():
        return []
    entries = json.loads(state_path.read_text(encoding="utf-8")).get("entries", {})
    findings: list[Finding] = []
    for _, entry in sorted(entries.items()):
        relative = str(entry.get("path", ""))
        path = root / relative
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        kind = entry.get("kind")
        if kind == "managed" and relative.startswith(".github/"):
            for number, text in _run_values(lines):
                findings.extend(_unresolved_in(relative, [text], number, graph))
        elif kind == "block" and entry.get("begin_marker") and entry.get("end_marker"):
            begin = str(entry["begin_marker"]).strip()
            end = str(entry["end_marker"]).strip()
            inside = False
            for number, text in enumerate(lines, start=1):
                if text.strip() == end:
                    inside = False
                elif inside:
                    findings.extend(_unresolved_in(relative, [text], number, graph))
                elif text.strip() == begin:
                    inside = True
    return findings


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

    document = _load_yaml(root_taskfile)
    root_tasks = task_specs(document)
    includes = include_map(document)
    section = getattr(config.document, "tasks", None)
    tasks_config = section if isinstance(section, TasksConfig) else TasksConfig()
    owned_paths = {Path(i.taskfile).as_posix() for i in tasks_config.includes}
    owned = {ns for ns, path in includes.items() if path in owned_paths}
    managed = set(includes) - owned

    findings: list[Finding] = []
    label = ROOT_TASKFILE.as_posix()
    findings.extend(_check_surface(root_tasks))
    for name, spec in root_tasks.items():
        findings.extend(_check_desc(label, name, spec))
        findings.extend(_check_wrapper_only(label, name, spec))

    findings.extend(_check_includes(root, includes, tasks_config, managed))
    for namespace in sorted(managed):
        path = includes[namespace]
        if not (root / path).is_file():
            continue
        for name, spec in task_specs(_load_yaml(root / path)).items():
            findings.extend(_check_desc(path, name, spec))
            if namespace in RESERVED_NAMESPACES:
                findings.extend(_check_internal(path, name, spec))

    graph, namespaces = load_graph(root)
    findings.extend(_check_refs(graph, includes, owned))
    findings.extend(_check_cycles(graph, includes, owned))
    findings.extend(
        _check_gate(
            graph, namespaces, tuple(archetypes.for_config(config).required_validate)
        )
    )
    findings.extend(_check_owned_text(root, graph))
    return findings
