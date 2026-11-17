"""`ci-entrypoint` — a CI step calls `task`, never a tool directly.

Handles both GitHub Actions (`run:`) and Azure Pipelines (`bash:`, `script:`,
`pwsh:`, `powershell:`) step syntax, including multi-line block scalars.

The forbidden list is the set of tools the task vocabulary wraps, plus the
generator itself: `kiln` may never appear directly in a workflow step, only
behind a committed `task` entrypoint.
"""

from __future__ import annotations

import re
from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.steps import step_commands

__all__ = ["CODE", "NAME", "check"]

NAME = "ci-entrypoint"
CODE = "ci.entrypoint"

_CI_DIRS = {"github": (Path(".github/workflows"),), "ado": (Path(".azure-pipelines"),)}

STEP_KEYS = ("run", "bash", "script", "pwsh", "powershell")


def _invocation_pattern(forbidden: tuple[str, ...]) -> re.Pattern[str]:
    """Match a forbidden tool as the first token of a command or after a separator.

    `task setup && uv sync` is still caught even though `task` legitimately
    appears in the same line. The optional `./` is what catches wrapper scripts
    invoked by path — `./gradlew test`, `./mvnw`.
    """
    return re.compile(r"(?:^|&&|\|\||;|\|)\s*(?:\./)?(" + "|".join(forbidden) + r")\b")


def _check_command_line(
    label: str,
    lineno: int,
    command: str,
    pattern: re.Pattern[str],
    exempt: frozenset[str],
) -> list[Finding]:
    if command.strip() in exempt:
        return []
    return [
        Finding(
            CODE,
            Severity.ERROR,
            f"step invokes `{match.group(1)}` directly — use `task` instead",
            path=label,
            line=lineno,
        )
        for match in pattern.finditer(command)
    ]


def _check_file(
    path: Path, label: str, pattern: re.Pattern[str], exempt: frozenset[str]
) -> list[Finding]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        finding
        for number, command in step_commands(lines, STEP_KEYS)
        for finding in _check_command_line(label, number, command, pattern, exempt)
    ]


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Scan every CI definition for a directly invoked tool."""
    archetype = archetypes.for_config(config)
    pattern = _invocation_pattern(tuple(archetype.forbidden_tools))
    exempt = frozenset(archetype.entrypoint_exempt)

    findings: list[Finding] = []
    for ci_dir in _CI_DIRS.get(config.ci_provider, ()):
        directory = root / ci_dir
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix in {".yml", ".yaml"}:
                findings.extend(
                    _check_file(
                        path, path.relative_to(root).as_posix(), pattern, exempt
                    )
                )
    return findings
