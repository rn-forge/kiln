"""`ci-hooks` — each `[ci.hooks]` action and each declared job's workflow exists and can be used.

Three rules:

1. Every `[ci.hooks]` `setup` and `docs` entry has an `action.yml` or `action.yaml`.
2. Every `[[ci.jobs]]` `uses` file exists, and its `on:` includes `workflow_call`.
3. No `[[ci.jobs]]` `uses` names a reusable stage workflow kiln renders.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import YamlUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.config import STAGE_WORKFLOWS, CiConfig

__all__ = ["MISSING", "NAME", "NOT_CALLABLE", "RESERVED", "check"]

NAME = "ci-hooks"
MISSING = "ci.hook-missing"
NOT_CALLABLE = "ci.hook-not-callable"
RESERVED = "ci.hook-reserved"


def _calls(workflow: object) -> bool:
    """Whether the parsed workflow's `on:` includes `workflow_call`."""
    if not isinstance(workflow, dict):
        return False
    table = cast("dict[object, object]", workflow)
    triggers = table.get("on")
    if isinstance(triggers, str):
        return triggers == "workflow_call"
    if isinstance(triggers, (list, dict)):
        return "workflow_call" in cast("list[object] | dict[object, object]", triggers)
    return False


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Report a hook or declared job whose file is missing, a workflow that cannot be called, or a call to a workflow kiln renders."""
    section = getattr(config.document, "ci", None)
    ci = section if isinstance(section, CiConfig) else CiConfig()
    findings: list[Finding] = []
    for entry in dict.fromkeys([*ci.hooks.setup, *ci.hooks.docs]):
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
        if job.uses in STAGE_WORKFLOWS:
            findings.append(
                Finding(
                    RESERVED,
                    Severity.ERROR,
                    f"job `{job.name}` calls `{job.uses}`, a workflow kiln renders",
                    path=job.uses,
                )
            )
        elif not path.is_file():
            findings.append(
                Finding(
                    MISSING,
                    Severity.ERROR,
                    f"job `{job.name}` calls `{job.uses}`, which does not exist",
                    path=job.uses,
                )
            )
        elif not _calls(YamlUtils.read_file(path, encoding="utf-8")):
            findings.append(
                Finding(
                    NOT_CALLABLE,
                    Severity.ERROR,
                    f"job `{job.name}` calls `{job.uses}`, whose `on:` lacks `workflow_call`",
                    path=job.uses,
                )
            )
    return findings
