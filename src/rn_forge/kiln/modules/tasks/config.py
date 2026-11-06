"""The `[tasks]` config section."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from rn_forge.kiln.modules.core.config.schema import ConfigModel

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


class TaskInclude(ConfigModel):
    """A repo-owned taskfile the generated `Taskfile.yml` includes."""

    namespace: str
    """The namespace its tasks are called under (`task <namespace>:<task>`).
    Changing it rewrites the include in `Taskfile.yml` on `kiln apply`."""
    taskfile: str
    """The taskfile's path, relative to the repository root. Changing it
    rewrites the include in `Taskfile.yml` on `kiln apply`."""


class TasksConfig(ConfigModel):
    """What the repo adds to the generated task surface."""

    includes: list[TaskInclude] = Field(default_factory=list[TaskInclude])
    """Repo-owned taskfiles the generated `Taskfile.yml` includes. Changing
    the list rewrites `Taskfile.yml` on `kiln apply`."""
    extra_refs: dict[str, list[str]] = Field(default_factory=dict)
    """Extra tasks a root verb calls, keyed by that verb (`validate`, `test`, ...).
    Changing it rewrites the root verb in `Taskfile.yml` on `kiln apply`."""
    command_overrides: dict[str, str] = Field(default_factory=dict)
    """A replacement command for an inner task, keyed by the task's name.
    Changing it rewrites that task in `tasks/*.yml` on `kiln apply`."""

    @model_validator(mode="before")
    @classmethod
    def _audit_moved(cls, data: Any) -> Any:
        if "audit" in (data or {}):
            raise ValueError("tasks.audit moved to [ci.checks] pip-audit")
        return data

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
