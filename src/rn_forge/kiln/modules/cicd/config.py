"""The `[ci]` config section."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, ValidationInfo, field_validator
from rn_forge.commons.lang.models import StrictModel

__all__ = ["GENERATED_JOBS", "CiConfig", "CiHooks", "CiJob"]

GENERATED_JOBS = frozenset(
    {
        "validate",
        "dependency-review",
        "plan",
        "verify",
        "postgres",
        "smoke",
        "suites",
        "sonar",
        "release",
        "external-install",
        "docs",
        "ci-ok",
    }
)
"""The job names `ci.yml` renders itself, which a declared job cannot take."""

_KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
_HOOK = re.compile(r"^\./\.github/actions/[a-z0-9][a-z0-9-]*$")
_SETUP_ACTION = "./.github/actions/setup"
_CALLABLE = re.compile(r"^\./\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml$")
_GENERATED_WORKFLOW = "./.github/workflows/ci.yml"


class CiHooks(StrictModel):
    """The anchors a repository extends the generated CI at, by reference."""

    setup: list[str] = Field(default_factory=list[str])
    """Local composite actions the generated setup action runs as its last steps."""

    docs: list[str] = Field(default_factory=list[str])
    """Local composite actions every Pages-uploading job runs before the upload, with `SITE_DIR` set."""

    @field_validator("setup", "docs")
    @classmethod
    def _entries_are_valid(cls, value: list[str], info: ValidationInfo) -> list[str]:
        field = f"ci.hooks.{info.field_name}"
        for entry in value:
            if not _HOOK.match(entry):
                raise ValueError(
                    f"{field} entry {entry!r} is not ./.github/actions/<name>"
                )
            if entry == _SETUP_ACTION:
                raise ValueError(f"{field} cannot name kiln's own setup action")
        if len(set(value)) != len(value):
            raise ValueError(f"{field} entries must be unique")
        return value


class CiJob(StrictModel):
    """A repository-declared job that calls a reusable workflow after `validate`."""

    name: str
    uses: str
    """The called workflow: `./.github/workflows/<file>.yml`, not `ci.yml`."""
    events: list[Literal["pull_request", "push", "workflow_dispatch"]] = Field(
        default_factory=lambda: ["pull_request", "push", "workflow_dispatch"],
        min_length=1,
    )
    """The events the job runs on; default all three."""
    contents: Literal["read", "write"] = "read"
    """The job's `contents` permission; `write` for a job that creates releases."""

    @field_validator("uses")
    @classmethod
    def _uses_is_a_local_workflow(cls, value: str) -> str:
        if not _CALLABLE.match(value) or value == _GENERATED_WORKFLOW:
            raise ValueError(
                f"ci.jobs uses {value!r} is not a local ./.github/workflows/<file>.yml "
                "other than ci.yml"
            )
        return value

    @field_validator("name")
    @classmethod
    def _name_is_free(cls, value: str) -> str:
        if not _KEBAB.match(value):
            raise ValueError(f"ci.jobs name {value!r} is not kebab-case")
        if value in GENERATED_JOBS:
            raise ValueError(f"ci.jobs name {value!r} is a job kiln generates")
        return value


class CiConfig(StrictModel):
    """Which CI provider the workflows target, and what they run."""

    provider: Literal["github", "ado"] = "github"
    """`ado` is reserved."""
    sonar: bool = True
    release: Literal["tag-exists", "pypi", "none"] = "tag-exists"
    doctor_full: Literal["default-branch", "every-run"] = "default-branch"
    """When CI runs `kiln doctor --full`: pushes to the default branch and
    dispatch, or every run."""
    hooks: CiHooks = Field(default_factory=CiHooks)
    jobs: list[CiJob] = Field(default_factory=list[CiJob])
    """Extra jobs, each calling one reusable workflow after `validate`."""

    @field_validator("jobs")
    @classmethod
    def _names_are_unique(cls, value: list[CiJob]) -> list[CiJob]:
        names = [job.name for job in value]
        if len(set(names)) != len(names):
            raise ValueError("ci.jobs names must be unique")
        return value
