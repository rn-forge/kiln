"""The `[tasks]` config section."""

from __future__ import annotations

from pydantic import Field, field_validator
from rn_forge.commons.lang.models import StrictModel

__all__ = ["ROOT_VERBS", "TaskInclude", "TasksConfig"]

ROOT_VERBS = (
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
)
"""The root Taskfile's fixed vocabulary (kiln ADR-0007)."""


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

    @field_validator("extra_refs")
    @classmethod
    def _keys_are_root_verbs(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        for key in value:
            if key not in ROOT_VERBS:
                raise ValueError(
                    f"tasks.extra_refs.{key} is not one of the ten root verbs "
                    f"({', '.join(ROOT_VERBS)})"
                )
        return value
