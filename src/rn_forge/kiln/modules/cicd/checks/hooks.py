"""`ci-hooks` — each `[ci.hooks]` action and each declared job's workflow exists and can be used.

Two rules:

1. Every `[ci.hooks]` `setup` entry has an `action.yml` or `action.yaml`.
2. Every `[[ci.jobs]]` `uses` file exists, and its `on:` includes `workflow_call`.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml
from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.config import CiConfig

__all__ = ["MISSING", "NAME", "NOT_CALLABLE", "check"]

NAME = "ci-hooks"
MISSING = "ci.hook-missing"
NOT_CALLABLE = "ci.hook-not-callable"


def _calls(workflow: object) -> bool:
    """Whether the parsed workflow's `on:` includes `workflow_call`."""
    if not isinstance(workflow, dict):
        return False
    table = cast("dict[object, object]", workflow)
    # YAML 1.1 reads the key `on` as the boolean True.
    triggers = table.get("on", table.get(True))
    if isinstance(triggers, str):
        return triggers == "workflow_call"
    if isinstance(triggers, (list, dict)):
        return "workflow_call" in cast("list[object] | dict[object, object]", triggers)
    return False


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Report a hook or declared job whose file is missing, or a workflow that cannot be called."""
    section = getattr(config.document, "ci", None)
    ci = section if isinstance(section, CiConfig) else CiConfig()
    findings: list[Finding] = []
    for entry in ci.hooks.setup:
        directory = root / entry
        if not any(
            (directory / name).is_file() for name in ("action.yml", "action.yaml")
        ):
            findings.append(
                Finding(
                    MISSING,
                    Severity.ERROR,
                    f"`[ci.hooks]` action `{entry}` has no action.yml or action.yaml",
                    path=entry,
                )
            )
    for job in ci.jobs:
        path = root / job.uses
        if not path.is_file():
            findings.append(
                Finding(
                    MISSING,
                    Severity.ERROR,
                    f"job `{job.name}` calls `{job.uses}`, which does not exist",
                    path=job.uses,
                )
            )
        elif not _calls(yaml.safe_load(path.read_text(encoding="utf-8"))):
            findings.append(
                Finding(
                    NOT_CALLABLE,
                    Severity.ERROR,
                    f"job `{job.name}` calls `{job.uses}`, whose `on:` lacks `workflow_call`",
                    path=job.uses,
                )
            )
    return findings
