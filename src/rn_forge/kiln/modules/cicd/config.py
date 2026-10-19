"""The `[ci]` config section."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, field_validator
from rn_forge.commons.lang.models import StrictModel

__all__ = ["GENERATED_JOBS", "CiConfig", "CiJob"]

GENERATED_JOBS = frozenset(
    {
        "validate",
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


class CiJob(StrictModel):
    """A repository-declared job that runs one `task` after `validate`."""

    name: str
    task: str
    events: list[Literal["pull_request", "push", "workflow_dispatch"]] = Field(
        default_factory=lambda: ["pull_request", "push", "workflow_dispatch"],
        min_length=1,
    )
    """The events the job runs on; default all three."""

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
    release: Literal["tag-exists", "none"] = "tag-exists"
    node: bool = False
    """Install pnpm and Node in the setup action, as `python-web-app` always does."""
    jobs: list[CiJob] = Field(default_factory=list[CiJob])
    """Extra jobs, each running one `task` after `validate`."""

    @field_validator("jobs")
    @classmethod
    def _names_are_unique(cls, value: list[CiJob]) -> list[CiJob]:
        names = [job.name for job in value]
        if len(set(names)) != len(names):
            raise ValueError("ci.jobs names must be unique")
        return value
