"""The public task surface of a repository, read from the task files kiln renders."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import NamedTuple

from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.commons.lang.collections import DictUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.tasks import artifacts
from rn_forge.kiln.modules.tasks.checks.layout import include_map, task_specs
from rn_forge.kiln.modules.tasks.config import TasksConfig

__all__ = ["PublicTask", "public_tasks"]


class PublicTask(NamedTuple):
    """One task `task --list` shows."""

    name: str
    desc: str


def _content(content: str | bytes) -> str:
    return content if isinstance(content, str) else content.decode("utf-8")


def public_tasks(config: KilnConfig) -> list[PublicTask]:
    """Every task of the rendered task files that is not `internal: true`.

    Args:
        config: the repository's configuration.

    Returns:
        The tasks sorted by name, as `<name>` from the root file and
        `<namespace>:<name>` from an include. Repository-owned includes are
        skipped.
    """
    rendered = {a.path: _content(a.content) for a in artifacts.render(config)}
    section = getattr(config.document, "tasks", None)
    tasks_config = section if isinstance(section, TasksConfig) else TasksConfig()
    owned = {PurePosixPath(i.taskfile).as_posix() for i in tasks_config.includes}
    root = YamlUtils.load(rendered["Taskfile.yml"])
    found = {("", name): spec for name, spec in task_specs(root).items()}
    for namespace, path in include_map(root).items():
        if path in owned or path not in rendered:
            continue
        for name, spec in task_specs(YamlUtils.load(rendered[path])).items():
            found[(namespace, name)] = spec
    return sorted(
        (
            PublicTask(f"{ns}:{name}" if ns else name, desc)
            for (ns, name), spec in found.items()
            if DictUtils.as_mapping(spec).get("internal") is not True
            and (desc := str(DictUtils.as_mapping(spec).get("desc", "")))
        ),
        key=lambda t: t.name,
    )
