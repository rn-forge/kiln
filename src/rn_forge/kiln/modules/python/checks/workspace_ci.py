"""`workspace-ci` — a member's `[tool.workspace-ci]` table is one the planner reads.

`kiln-devops` raises on the same three conditions when `task ci:plan` loads the
workspace; a render-free check may not import it, so the texts are restated here
and a parity test keeps the two together.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.lang.collections import DictUtils

from rn_forge.kiln.config import KilnConfig

__all__ = ["CODE", "NAME", "check"]

NAME = "workspace-ci"
CODE = "workspace-ci"

TABLE = "tool.workspace-ci"


def _member_findings(document: dict[str, object], label: str) -> list[Finding]:
    ci = DictUtils.get_mapping(document, TABLE)
    findings: list[Finding] = []

    def error(code: str, message: str) -> None:
        findings.append(Finding(f"{CODE}.{code}", Severity.ERROR, message, path=label))

    for old in ("postgres", "redis"):
        if old in ci:
            error(
                "legacy-service",
                f"[{TABLE}.{old}] was replaced by [{TABLE}.integration.{old}]",
            )
    for name, table in DictUtils.as_mapping(ci.get("integration")).items():
        service = DictUtils.as_mapping(table)
        if "image" not in service:
            error("missing-image", f"[{TABLE}.integration.{name}] needs an image")
        wait = service.get("health-wait", 120)
        if not isinstance(wait, int) or wait < 1:
            error(
                "bad-health-wait",
                f"[{TABLE}.integration.{name}] health-wait "
                "must be a whole number of seconds, 1 or more",
            )
    return findings


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Report each member's legacy, imageless or mistimed `workspace-ci` service."""
    if config.archetype != "python-lib":
        return []
    findings: list[Finding] = []
    for package in config.packages:
        relative = f"{package}/pyproject.toml"
        path = root / relative
        if path.exists():
            findings.extend(_member_findings(DocumentUtils.read(path), relative))
    return findings
