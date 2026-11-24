"""`kiln doctor`: the render-free checks, and with `--full` the render-dependent ones."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.generation import BLOCKING_ACTIONS, Action, ArtifactKind
from rn_forge.commons.runtime.console import console

from rn_forge.kiln import checks
from rn_forge.kiln.commands import output
from rn_forge.kiln.modules.core import cycle

__all__ = ["doctor", "full"]

_CODES = {
    Action.CREATE: "artifact.stale",
    Action.UPDATE: "artifact.stale",
    Action.DELETE: "artifact.stale",
    Action.INSERT: "block.stale",
    Action.REMOVE: "block.stale",
    Action.CONFLICT: "artifact.conflict",
    Action.DRIFT: "artifact.drift",
    Action.MISSING: "artifact.missing",
}


def doctor(
    paths: list[Path],
    full: bool = False,
    json: bool = False,
    all: bool = False,
) -> None:
    """Run every render-free check over each of PATHS' committed files.

    Prints each finding and raises `AppException` if any is an error. `--full`
    also reports every managed artifact and block a fresh render would change.
    `--json` prints the findings as one JSON object. More than one path needs
    `--all`, which checks each independently, reports a path whose config will
    not load as a `config.load` error for that path alone, and prints a table of
    paths with their error and warning counts.

    Raises:
        AppException: several paths are given without `--all`, or a finding is an
            error.
    """
    if len(paths) > 1 and not all:
        raise AppException("several paths need --all")
    output.use_json(json)
    if all:
        _run_all(paths, full)
    else:
        _run_one(paths[0], full)


def _run_one(path: Path, full: bool) -> None:
    findings = _findings(path, full)
    output.emit({"findings": [output.finding_json(f) for f in findings]}, lambda: None)
    output.report_findings(findings, path)


def _run_all(paths: list[Path], full: bool) -> None:
    reports: list[tuple[Path, list[Finding]]] = []
    for path in paths:
        try:
            reports.append((path, _findings(path, full)))
        except AppException as exc:
            reports.append(
                (path, [Finding("config.load", Severity.ERROR, str(exc), path=None)])
            )
    error_counts = [sum(f.is_error for f in found) for _, found in reports]
    warning_counts = [len(found) - n for (_, found), n in zip(reports, error_counts)]

    def text() -> None:
        console.table(
            "repo",
            "errors",
            "warnings",
            rows=[
                (path, errors, warnings)
                for (path, _), errors, warnings in zip(
                    reports, error_counts, warning_counts
                )
            ],
        )
        for path, found in reports:
            if found:
                console.print("{}", path, markup=False)
            for finding in found:
                console.error("{}", finding)

    output.emit(
        {
            "repos": [
                {"path": str(path), "findings": [output.finding_json(f) for f in found]}
                for path, found in reports
            ],
            "summary": {
                "repos": len(reports),
                "errors": sum(error_counts),
                "warnings": sum(warning_counts),
            },
        },
        text,
    )
    if sum(error_counts):
        raise AppException(
            "{} check(s) failed across {} repo(s)",
            sum(error_counts),
            sum(1 for n in error_counts if n),
        )


def _findings(path: Path, render: bool) -> list[Finding]:
    root = path.resolve()
    findings = checks.run(root)
    if render:
        seen = {(f.code, f.path) for f in findings}
        findings.extend(f for f in full(root) if (f.code, f.path) not in seen)
    return findings


def full(root: Path) -> list[Finding]:
    """Findings for each managed artifact or block a fresh render would change.

    Raises:
        AppException: The config is invalid, or a legacy kiln tree is present.
    """
    findings: list[Finding] = []
    for change in cycle.plan(root).changes:
        code = _CODES.get(change.action)
        if code is None or change.kind is ArtifactKind.SEEDED:
            continue
        if change.action in BLOCKING_ACTIONS:
            message = (
                f"is {change.action.value} against a fresh render; "
                "resolve it, then run kiln apply"
            )
        else:
            message = (
                f"would be {change.action.value} by a fresh render — run `kiln apply`"
            )
        findings.append(Finding(code, Severity.ERROR, message, path=change.path))
    return findings
