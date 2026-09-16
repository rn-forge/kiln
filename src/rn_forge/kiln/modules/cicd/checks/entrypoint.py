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

__all__ = ["CODE", "NAME", "check"]

NAME = "ci-entrypoint"
CODE = "ci.entrypoint"

_CI_DIRS = {"github": (Path(".github/workflows"),), "ado": (Path(".azure-pipelines"),)}

STEP_KEYS = ("run", "bash", "script", "pwsh", "powershell")

# A step's command line — single-line `key: cmd` or the first line of a
# `key: |` block scalar.
STEP_LINE = re.compile(r"^(\s*)(?:- )?(?:" + "|".join(STEP_KEYS) + r"):\s*(.*)$")
BLOCK_SCALAR = re.compile(r"^[|>][+-]?\d*$")


def _invocation_pattern(forbidden: tuple[str, ...]) -> re.Pattern[str]:
    """Match a forbidden tool as the first token of a command or after a separator.

    `task setup && uv sync` is still caught even though `task` legitimately
    appears in the same line. The optional `./` is what catches wrapper scripts
    invoked by path — `./gradlew test`, `./mvnw`.
    """
    return re.compile(r"(?:^|&&|\|\||;|\|)\s*(?:\./)?(" + "|".join(forbidden) + r")\b")


def _check_command_line(
    label: str, lineno: int, command: str, pattern: re.Pattern[str]
) -> list[Finding]:
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


def _check_file(path: Path, label: str, pattern: re.Pattern[str]) -> list[Finding]:
    findings: list[Finding] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        match = STEP_LINE.match(lines[index])
        if not match:
            index += 1
            continue
        indent, remainder = match.groups()
        if remainder and not BLOCK_SCALAR.match(remainder.strip()):
            findings.extend(_check_command_line(label, index + 1, remainder, pattern))
            index += 1
            continue
        # Block scalar: consume subsequent, more-indented lines as the body.
        base_indent = len(indent)
        index += 1
        while index < len(lines):
            line = lines[index]
            if line.strip() and (len(line) - len(line.lstrip())) <= base_indent:
                break
            findings.extend(_check_command_line(label, index + 1, line, pattern))
            index += 1
    return findings


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Scan every CI definition for a directly invoked tool."""
    pattern = _invocation_pattern(tuple(archetypes.for_config(config).forbidden_tools))

    findings: list[Finding] = []
    for ci_dir in _CI_DIRS.get(config.ci_provider, ()):
        directory = root / ci_dir
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix in {".yml", ".yaml"}:
                findings.extend(
                    _check_file(path, path.relative_to(root).as_posix(), pattern)
                )
    return findings
