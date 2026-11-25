"""The security control catalog a release's evidence record reports."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rn_forge.kiln.modules.cicd import registry

__all__ = ["CONTROLS", "Effect", "SecurityControl", "Source", "render_catalog"]


class Effect(StrEnum):
    """What a control does when it finds a problem."""

    FAILS = "fails the build"
    BLOCKS_PUSH = "blocks the push"
    REPORTS = "reports only"


class Source(StrEnum):
    """Where the evidence collector reads a control's result."""

    LINT_JOB = "lint-job"
    JOB = "job"
    NOT_CHECKED = "not-checked"
    RELEASE_ASSET = "release-asset"
    ATTESTATION = "attestation"
    FILE = "file"
    SCORECARD_RUN = "scorecard-run"


@dataclass(frozen=True)
class SecurityControl:
    """One security control: its effect, where its result comes from, its evidence."""

    name: str
    effect: Effect
    source: Source
    result_from: str
    evidence: str
    checks: tuple[str, ...] = ()


CONTROLS: tuple[SecurityControl, ...] = (
    SecurityControl(
        "Dependency audit",
        Effect.FAILS,
        Source.LINT_JOB,
        "the conclusion of the job that runs `task lint`",
        "that job's URL and the step name",
        ("pip-audit", "pnpm-audit"),
    ),
    SecurityControl(
        "Licence inventory",
        Effect.FAILS,
        Source.LINT_JOB,
        "the conclusion of the job that runs `task lint`",
        "that job's URL and the step name, with the deny list in force",
        ("licenses",),
    ),
    SecurityControl(
        "Source scan",
        Effect.FAILS,
        Source.LINT_JOB,
        "the conclusion of the job that runs `task lint`",
        "that job's URL and the step name",
        ("ruff check and format", "Nx lint, typecheck, test, build"),
    ),
    SecurityControl(
        "Secret scan",
        Effect.FAILS,
        Source.JOB,
        "the `secret-scan` job's conclusion",
        "the job's URL",
        ("secret-scan",),
    ),
    SecurityControl(
        "Push protection",
        Effect.BLOCKS_PUSH,
        Source.NOT_CHECKED,
        "not read by CI: recorded `not checked` and filled when the page is rendered",
        "the API call and its date",
    ),
    SecurityControl(
        "SBOM",
        Effect.REPORTS,
        Source.RELEASE_ASSET,
        "a `*.cdx.json` asset on each package's GitHub release",
        "the release URL and the asset names",
    ),
    SecurityControl(
        "Attestation",
        Effect.REPORTS,
        Source.ATTESTATION,
        "`gh attestation verify` on each released artifact, or the PyPI "
        'integrity API for each wheel when `[ci] release = "pypi"`',
        "the HTTP status per file",
    ),
    SecurityControl(
        "`SECURITY.md`",
        Effect.REPORTS,
        Source.FILE,
        "the file exists at the repository root at the pushed commit",
        "its path",
    ),
    SecurityControl(
        "Scorecard",
        Effect.REPORTS,
        Source.SCORECARD_RUN,
        "the newest `scorecard.yml` run on the default branch",
        "its run URL, score, version and the commit it scored",
        ("scorecard",),
    ),
)
"""Every security control, in the order the catalog lists them."""


def _control_cell(control: SecurityControl, archetype: str) -> str:
    by_name = {c.name: c for c in registry.CHECKS}
    run = [
        registry.name_cell(name)
        for name in control.checks
        if archetype in by_name[name].archetypes
    ]
    return f"{control.name} ({', '.join(run)})" if run else control.name


def render_catalog(archetype: str) -> str:
    """The control catalog as a Markdown table, naming the checks *archetype* runs."""
    rows = [
        [
            _control_cell(c, archetype),
            c.effect.value,
            c.result_from,
            c.evidence,
        ]
        for c in CONTROLS
    ]
    return registry.table(["Control", "Effect", "Result from", "Evidence"], rows)
