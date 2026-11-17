"""Scan the command lines of CI workflow steps and `.github` text."""

from __future__ import annotations

import re

__all__ = ["step_commands"]

_BLOCK_SCALAR = re.compile(r"^[|>][+-]?\d*$")


def step_commands(lines: list[str], keys: tuple[str, ...]) -> list[tuple[int, str]]:
    """Every `<key>:` step's command as (1-indexed line, text).

    Args:
        lines: The lines of a workflow file.
        keys: The step keys whose values are commands (`run`, `bash`, ...).

    Returns:
        A single-line value as written; a block scalar line by line.
    """
    step_line = re.compile(r"^(\s*)(?:- )?(?:" + "|".join(keys) + r"):\s*(.*)$")
    values: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        match = step_line.match(lines[index])
        index += 1
        if not match:
            continue
        indent, remainder = match.groups()
        if remainder and not _BLOCK_SCALAR.match(remainder.strip()):
            values.append((index, remainder))
            continue
        while index < len(lines):
            line = lines[index]
            if line.strip() and len(line) - len(line.lstrip()) <= len(indent):
                break
            values.append((index + 1, line))
            index += 1
    return values
