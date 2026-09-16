"""The `[tasks]` config section."""

from __future__ import annotations

from pydantic import Field
from rn_forge.commons.lang.models import StrictModel

__all__ = ["TaskInclude", "TasksConfig"]


class TaskInclude(StrictModel):
    """A repo-owned taskfile the generated `Taskfile.yml` includes."""

    namespace: str
    taskfile: str


class TasksConfig(StrictModel):
    """What the repo adds to the generated task surface."""

    includes: list[TaskInclude] = Field(default_factory=list[TaskInclude])
    extra_refs: dict[str, list[str]] = Field(default_factory=dict)
    """Extra tasks a root verb calls, keyed by that verb."""
    command_overrides: dict[str, str] = Field(default_factory=dict)
    """A replacement command for an inner task, keyed by the task's name."""
