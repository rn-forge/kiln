"""`task-layout` — the repository's own task files, against the config.

kiln's rendered Taskfiles are held to their shape by the render tests and by
`generated`; this check reads only what the repository owns: the
`tasks.includes` files and each root verb's `tasks.extra_refs`.

1. Every owned include's `taskfile` exists.
2. Every `extra_refs` target into an owned namespace names a task the owned
   file defines.
3. The owned tasks and the root verbs form no reference cycle. A root verb's
   edges are its `extra_refs`; an owned task's `task:` call to a root verb is an
   edge to that verb.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import YamlUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.tasks.config import ROOT_VERBS, WEB_APP_VERBS
from rn_forge.kiln.modules.tasks.taskfile import task_refs, task_specs

__all__ = ["CODE", "NAME", "check"]

NAME = "task-layout"
CODE = "taskgraph"


def _split(target: str) -> tuple[str | None, str]:
    """The namespace and task of an `extra_refs` target; a bare one has no namespace."""
    namespace, sep, task = target.removeprefix(":").partition(":")
    return (namespace, task) if sep else (None, namespace)


def _owned_graph(
    root: Path, config: KilnConfig
) -> tuple[dict[str, str], dict[str, object]]:
    """Each owned namespace's file, and every owned task by qualified name."""
    files = {i.namespace: Path(i.taskfile).as_posix() for i in config.tasks.includes}
    graph: dict[str, object] = {}
    for namespace, path in files.items():
        if (root / path).is_file():
            specs = task_specs(YamlUtils.read_file(root / path, encoding="utf-8"))
            graph.update({f"{namespace}:{name}": spec for name, spec in specs.items()})
    return files, graph


def _edges(
    config: KilnConfig, graph: dict[str, object], verbs: tuple[str, ...]
) -> dict[str, list[str]]:
    """The reference graph: owned tasks, and one node per root verb."""
    edges: dict[str, list[str]] = {}
    for verb in verbs:
        targets = (t.removeprefix(":") for t in config.tasks.extra_refs.get(verb, []))
        edges[verb] = [t for t in targets if t in graph or t in verbs]
    for name, spec in graph.items():
        namespace = name.split(":", 1)[0]
        resolved = (
            ref.removeprefix(":")
            if ref.startswith(":") or f"{namespace}:{ref}" not in graph
            else f"{namespace}:{ref}"
            for ref in task_refs(spec)
        )
        edges[name] = [ref for ref in resolved if ref in graph or ref in verbs]
    return edges


def _cycles(edges: dict[str, list[str]], files: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    reported: set[frozenset[str]] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in stack:
            cycle = [*stack[stack.index(node) :], node]
            if frozenset(cycle) not in reported:
                reported.add(frozenset(cycle))
                owned = next(
                    (m.split(":", 1)[0] for m in cycle if m.split(":", 1)[0] in files),
                    None,
                )
                findings.append(
                    Finding(
                        f"{CODE}.cycle",
                        Severity.ERROR,
                        f"task reference cycle: {' -> '.join(cycle)}",
                        path=files[owned] if owned else "Taskfile.yml",
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


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Hold the repository's own includes to the config that declares them."""
    if not config.tasks.includes:
        return []
    files, graph = _owned_graph(root, config)
    findings = [
        Finding(
            f"{CODE}.missing-include",
            Severity.ERROR,
            f"include `{namespace}` points at `{path}`, which does not exist",
            path=path,
        )
        for namespace, path in files.items()
        if not (root / path).is_file()
    ]
    for verb, targets in sorted(config.tasks.extra_refs.items()):
        for target in targets:
            namespace, task = _split(target)
            if (
                namespace in files
                and (root / files[namespace]).is_file()
                and f"{namespace}:{task}" not in graph
            ):
                findings.append(
                    Finding(
                        f"{CODE}.unresolved",
                        Severity.ERROR,
                        f"`tasks.extra_refs.{verb}` calls `{target}`, which "
                        f"`{files[namespace]}` does not define",
                        path=files[namespace],
                    )
                )
    verbs = ROOT_VERBS + (WEB_APP_VERBS if config.is_web_app else ())
    return findings + _cycles(_edges(config, graph, verbs), files)
