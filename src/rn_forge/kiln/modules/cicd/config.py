"""The `[ci]` config section."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, ValidationInfo, field_validator

from rn_forge.kiln.modules.core.config.schema import ConfigModel

__all__ = [
    "GENERATED_JOBS",
    "CiConfig",
    "CiHooks",
    "CiJob",
    "LicensePolicy",
    "resolve_release",
]

GENERATED_JOBS = frozenset(
    {
        "validate",
        "dependency-review",
        "secret-scan",
        "plan",
        "test",
        "integration",
        "smoke",
        "suites",
        "sonar",
        "release",
        "external-install",
        "docs",
        "scorecard",
        "checks-ok",
        "ci-ok",
    }
)
"""The job names `ci.yml` renders itself, which a declared job cannot take."""

_KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
_HOOK = re.compile(r"^\./\.github/actions/[a-z0-9][a-z0-9-]*$")
_SETUP_ACTION = "./.github/actions/setup"
_CALLABLE = re.compile(r"^\./\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml$")
_GENERATED_WORKFLOW = "./.github/workflows/ci.yml"


class LicensePolicy(ConfigModel):
    """The policy of the `licenses` check."""

    deny: list[str] = Field(
        default_factory=lambda: ["GPL", "GPL-*", "AGPL", "AGPL-*", "UNKNOWN"]
    )
    """License identifiers (globs allowed) the check fails on."""
    ignore: list[str] = Field(default_factory=list[str])
    """Packages the check skips."""


class CiHooks(ConfigModel):
    """The anchors a repository extends the generated CI at, by reference."""

    setup: list[str] = Field(default_factory=list[str])
    """Local composite actions the generated setup action runs as its last steps.
    Changing the list rewrites the setup action on `kiln apply`."""

    docs: list[str] = Field(default_factory=list[str])
    """Local composite actions every Pages-uploading job runs before the upload,
    with `SITE_DIR` set. Changing the list rewrites the workflows on
    `kiln apply`."""

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


class CiJob(ConfigModel):
    """A repository-declared job that calls a reusable workflow after `validate`."""

    name: str
    """The job's name in `ci.yml`: kebab-case, and not a job kiln generates.
    Changing it renames the job on `kiln apply`."""
    uses: str
    """The called workflow: `./.github/workflows/<file>.yml`, not `ci.yml`.
    Changing it rewrites the job in `ci.yml` on `kiln apply`."""
    events: list[Literal["pull_request", "push", "workflow_dispatch"]] = Field(
        default_factory=lambda: ["pull_request", "push", "workflow_dispatch"],
        min_length=1,
    )
    """The events the job runs on. Changing them rewrites the job's condition in
    `ci.yml` on `kiln apply`."""
    contents: Literal["read", "write"] = "read"
    """The job's `contents` permission; `write` for a job that creates releases.
    Changing it rewrites the job's permissions in `ci.yml` on `kiln apply`."""
    required: bool = True
    """`False` keeps the job out of `ci-ok`'s `needs`."""

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


class CiConfig(ConfigModel):
    """Which CI provider the workflows target, and what they run."""

    provider: Literal["github", "ado"] = "github"
    """The CI provider the workflows target. `ado` is reserved and not yet
    rendered; changing it re-renders the CI files on `kiln apply`."""
    sonar: bool = True
    """Whether CI runs a Sonar analysis. Turning it off removes the Sonar job and
    its properties file on `kiln apply`."""
    release: Literal["tag-exists", "pypi", "nx-dispatch", "none"] | None = None
    """How a release is published: `tag-exists` tags the default branch, `pypi`
    publishes a library to PyPI, `nx-dispatch` is the `node-lib` flow, and
    `none` has no release job. Changing it rewrites the release workflow on
    `kiln apply`. Default: `tag-exists`; `nx-dispatch` for `node-lib`."""
    doctor_full: Literal["default-branch", "every-run"] = "default-branch"
    """When CI runs `kiln doctor --full`: on pushes to the default branch and on
    dispatch, or on every run. Changing it rewrites the validate job in
    `ci.yml` on `kiln apply`."""
    sonar_exclusions: list[str] = Field(default_factory=list[str])
    """Paths Sonar skips, added to the archetype's own. Changing the list rewrites
    the Sonar properties on `kiln apply`."""
    sonar_coverage_exclusions: list[str] = Field(default_factory=list[str])
    """Paths Sonar counts but does not expect to have coverage. Changing the list
    rewrites the Sonar properties on `kiln apply`."""
    hooks: CiHooks = Field(default_factory=CiHooks)
    """Local actions the generated CI runs at its extension points."""
    jobs: list[CiJob] = Field(default_factory=list[CiJob])
    """Extra jobs, each calling one reusable workflow after `validate`. Changing
    the list rewrites `ci.yml` on `kiln apply`."""
    checks: dict[str, bool | dict[str, object]] = Field(default_factory=dict)
    """Switches for the configurable checks: a name from the check registry set to
    a bool, or for `licenses` a table of its policy. Changing it re-renders
    `ci.yml` and the check tasks on `kiln apply`."""

    @field_validator("checks")
    @classmethod
    def _checks_are_configurable(
        cls, value: dict[str, bool | dict[str, object]]
    ) -> dict[str, bool | dict[str, object]]:
        from rn_forge.kiln.modules.cicd import registry

        rows = {c.name: c for c in registry.CHECKS}
        for name, entry in value.items():
            field = f"ci.checks.{name}"
            row = rows.get(name)
            if row is None:
                raise ValueError(f"{field} is not a configurable check")
            if row.switch is not registry.Switch.CONFIGURED:
                raise ValueError(f"{field} is {row.switch} and has no switch")
            if isinstance(entry, dict):
                if row.policy is None:
                    raise ValueError(f"{field} takes no policy")
                row.policy.model_validate(entry)
        return value

    def licenses_policy(self) -> LicensePolicy:
        """The `licenses` check's policy: the `[ci.checks]` table, or the default."""
        entry = self.checks.get("licenses")
        return LicensePolicy.model_validate(entry if isinstance(entry, dict) else {})

    @field_validator("sonar_exclusions", "sonar_coverage_exclusions")
    @classmethod
    def _exclusions_are_valid(cls, value: list[str], info: ValidationInfo) -> list[str]:
        field = f"ci.{info.field_name}"
        for entry in value:
            if not entry or "," in entry or "\n" in entry:
                raise ValueError(
                    f"{field} entry {entry!r} must be non-empty, with no comma or newline"
                )
        return value

    @field_validator("jobs")
    @classmethod
    def _names_are_unique(cls, value: list[CiJob]) -> list[CiJob]:
        names = [job.name for job in value]
        if len(set(names)) != len(names):
            raise ValueError("ci.jobs names must be unique")
        return value


def resolve_release(ci: CiConfig, archetype: str) -> str:
    """The release mode *archetype* runs: `ci.release`, or the archetype's default when unset.

    Raises:
        ValueError: the mode does not fit the archetype. `pypi` needs `python-lib`;
            `nx-dispatch` needs `node-lib`, which takes neither `tag-exists` nor `pypi`.
    """
    node_lib = archetype == "node-lib"
    release = ci.release or ("nx-dispatch" if node_lib else "tag-exists")
    if release == "pypi" and archetype != "python-lib":
        raise ValueError("ci.release = 'pypi' needs a library workspace")
    if release == "nx-dispatch" and not node_lib:
        raise ValueError("ci.release = 'nx-dispatch' needs the node-lib archetype")
    if release == "tag-exists" and node_lib:
        raise ValueError("ci.release = 'tag-exists' is not available for node-lib")
    return release
