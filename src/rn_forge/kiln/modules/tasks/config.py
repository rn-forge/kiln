"""The `[tasks]` config section."""

from __future__ import annotations

import re

from pydantic import Field, field_validator

from rn_forge.kiln.modules.core.config.schema import ConfigModel

__all__ = ["ROOT_VERBS", "AuditConfig", "AuditIgnore", "TaskInclude", "TasksConfig"]

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


_VULN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


class AuditIgnore(ConfigModel):
    """A vulnerability the dependency audit accepts, and why."""

    id: str
    """The advisory id (`GHSA-…`, `PYSEC-…`, `CVE-…`) the audit accepts.
    Changing it rewrites the audit command on `kiln apply`."""
    reason: str
    """Why the vulnerability is accepted; never empty. It is recorded beside the
    id, and changing it rewrites the audit task on `kiln apply`."""

    @field_validator("id")
    @classmethod
    def _id_is_an_advisory_id(cls, value: str) -> str:
        if not _VULN_ID.match(value):
            raise ValueError(f"tasks.audit.ignore id {value!r} is not an advisory id")
        return value

    @field_validator("reason")
    @classmethod
    def _reason_is_given(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tasks.audit.ignore reason must not be empty")
        return value.strip()


class AuditConfig(ConfigModel):
    """The dependency audit (`pip-audit`) settings."""

    ignore: list[AuditIgnore] = Field(default_factory=list[AuditIgnore])
    """Accepted vulnerabilities, passed to `pip-audit --ignore-vuln` in order.
    Changing the list rewrites the audit task on `kiln apply`."""

    @field_validator("ignore")
    @classmethod
    def _ids_are_unique(cls, value: list[AuditIgnore]) -> list[AuditIgnore]:
        ids = [entry.id for entry in value]
        if len(set(ids)) != len(ids):
            raise ValueError("tasks.audit.ignore ids must be unique")
        return value


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
    audit: AuditConfig = Field(default_factory=AuditConfig)
    """How the dependency audit runs."""

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
