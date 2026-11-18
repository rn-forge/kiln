"""kiln, as pykit's lifecycle verbs see it.

`[lifecycle]` in `cli.toml` names `PRODUCT`; `rn-forge-tooling` mounts all six verbs
under `kiln self`, so the install-health check is `kiln self doctor` and
`kiln doctor` stays the repository check.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from rn_forge.commons.findings import Finding, Severity
from rn_forge.tooling.install import Check, PythonTool, ToolHome

from rn_forge.kiln import __version__

__all__ = ["PRODUCT", "Installed", "Kiln", "running_install"]


@dataclass(frozen=True)
class Installed:
    """The install the running kiln was started from, as `state.json` records it."""

    ref: str
    commit: str | None


def running_install(home: ToolHome | None = None) -> Installed | None:
    """The install kiln is running from, or `None` when it runs from anywhere else."""
    home = home or ToolHome("kiln")
    try:
        relative = Path(sys.prefix).resolve().relative_to(home.versions_dir.resolve())
        if not relative.parts or relative.parts[0] != home.current_version():
            return None
        state: object = json.loads(home.state_path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    if not isinstance(state, dict):
        return None
    fields = cast("dict[str, object]", state)
    ref = fields.get("ref")
    if not isinstance(ref, str) or not ref:
        return None
    commit = fields.get("commit")
    return Installed(ref, commit if isinstance(commit, str) and commit else None)


def check_home(home: ToolHome) -> list[Finding]:
    """Report where kiln is, or would be, installed."""
    return [Finding("kiln.home", Severity.INFO, f"home is {home.product_dir}")]


class Kiln(PythonTool):
    """kiln: installed with `uv tool install`, one check of its own."""

    def checks(self) -> Sequence[Check]:
        """Check the install's home."""
        return (check_home,)


PRODUCT = Kiln(name="kiln", version=__version__, repo="rn-forge/kiln")
