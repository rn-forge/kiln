"""How a kiln command reports: JSON mode, JSON-or-text output, artifact rows and findings."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from rn_forge.commons import generation
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import checks

__all__ = [
    "artifact_rows",
    "change_rows",
    "emit",
    "emit_rows",
    "fail_on_errors",
    "finding_json",
    "report_findings",
    "use_json",
]


def use_json(flag: bool) -> None:
    """Switch the console to JSON mode when *flag* is set."""
    if flag:
        console.set_mode(OutputMode.JSON)


def emit(payload: Mapping[str, object], text: Callable[[], None]) -> None:
    """Print *payload* as JSON in JSON mode, else call *text* to print the text form."""
    if console.mode is OutputMode.JSON:
        console.json(payload)
    else:
        text()


def emit_rows(payload: Mapping[str, object], rows: Sequence[Mapping[str, str]]) -> None:
    """Emit *payload* in JSON mode, else one `key kind action` line per row."""

    def text() -> None:
        for row in rows:
            console.info("{} {} {}", row["key"], row["kind"], row["action"])

    emit(payload, text)


def finding_json(finding: Finding) -> dict[str, str | None]:
    """*finding* as a JSON-ready mapping."""
    return {
        "code": finding.code,
        "severity": finding.severity.value,
        "message": finding.message,
        "path": finding.path,
    }


def report_findings(
    findings: Sequence[Finding], where: object, what: str = "check(s) failed in"
) -> None:
    """Print each finding, then raise if any is an error.

    Raises:
        AppException: A finding is an error; the message is `"<n> <what> <where>"`.
    """
    for finding in findings:
        console.error("{}", finding)
    errors = [finding for finding in findings if finding.is_error]
    if errors:
        raise AppException("{} " + what + " {}", len(errors), where)


def _row(key: str, path: str, kind: str, action: str) -> dict[str, str]:
    return {"key": key, "path": path, "kind": kind, "action": action}


def change_rows(changes: Sequence[generation.Change]) -> list[dict[str, str]]:
    """*changes* as `{key, path, kind, action}` rows."""
    return [
        _row(change.key, change.path, change.kind.value, change.action.value)
        for change in changes
    ]


def artifact_rows(
    directory: Path, artifacts: Sequence[generation.Artifact]
) -> list[dict[str, str]]:
    """*artifacts* as `{key, path, kind, action}` rows, classified against no state."""
    return [
        _row(
            artifact.key,
            artifact.path,
            artifact.kind.value,
            generation.classify(directory, artifact, None).value,
        )
        for artifact in artifacts
    ]


def fail_on_errors(root: Path) -> None:
    """Run `kiln doctor`'s ownership checks over *root*, raising if any is an error."""
    report_findings(checks.run(root, scope="ownership"), root)
