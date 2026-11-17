"""Read a Taskfile's tasks, references and includes."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.lang.collections import DictUtils, ListUtils

__all__ = ["include_map", "task_refs", "task_specs"]


def task_specs(document: object) -> dict[str, object]:
    """The `tasks:` mapping of a Taskfile, or empty if there isn't one."""
    return DictUtils.get_mapping(DictUtils.as_mapping(document), "tasks")


def task_refs(spec: object) -> list[str]:
    """The `task:` targets a task calls, in order."""
    refs: list[str] = []
    for entry in ListUtils.as_list(DictUtils.as_mapping(spec).get("cmds")):
        target = DictUtils.as_mapping(entry).get("task")
        if isinstance(target, str):
            refs.append(target)
    return refs


def include_map(document: object) -> dict[str, str]:
    """The root file's `includes:`, namespace to path (posix, no `./`)."""
    includes: dict[str, str] = {}
    for namespace, value in DictUtils.get_mapping(
        DictUtils.as_mapping(document), "includes"
    ).items():
        path = (
            value
            if isinstance(value, str)
            else DictUtils.as_mapping(value).get("taskfile")
        )
        if isinstance(path, str):
            includes[namespace] = Path(path).as_posix()
    return includes
