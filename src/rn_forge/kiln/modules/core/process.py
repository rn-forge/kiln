"""Run a subprocess through `Process`, the one way kiln starts one."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from rn_forge.commons.runtime.subprocess import Process

__all__ = ["run"]


def run(
    label: str,
    *args: str | Path,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    check: bool = True,
    capture_output: bool = True,
) -> Process:
    """Run a command and return its `Process` record.

    Args:
        label: The name the process carries in logs and errors.
        *args: The command and its arguments.
        cwd: The working directory, if not the current one.
        env: The whole environment, if not the inherited one.
        check: Raise when the command exits non-zero.
        capture_output: Capture stdout and stderr instead of streaming them.

    Returns:
        The finished `Process`.

    Raises:
        AppException: *check* is set and the command fails.
    """
    options: dict[str, Any] = {}
    if env is not None:
        options["env"] = env
    return Process.execute(
        label,
        *(str(a) for a in args),
        fail_on_error=check,
        capture_output=capture_output,
        cwd=str(cwd) if cwd else None,
        **options,
    )
