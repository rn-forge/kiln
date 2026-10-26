"""The render-dependent half of `kiln doctor`, run by `--full`."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.generation import Action, ArtifactKind

from rn_forge.kiln.modules.core import cycle

__all__ = ["full"]

_CODES = {
    Action.CREATE: "artifact.stale",
    Action.UPDATE: "artifact.stale",
    Action.DELETE: "artifact.stale",
    Action.INSERT: "block.stale",
    Action.REMOVE: "block.stale",
}


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
        findings.append(
            Finding(
                code,
                Severity.ERROR,
                f"would be {change.action.value} by a fresh render — run `kiln apply`",
                path=change.path,
            )
        )
    return findings
