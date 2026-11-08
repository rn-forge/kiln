"""`nx-version` — a node-lib's Nx is not behind the one kiln pins.

kiln does not run `nx migrate`: it edits the repository's own code. The check
says when the migrate is due.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.node.angular import NX_VERSION

__all__ = ["CODE", "NAME", "check"]

NAME = "nx-version"
CODE = "node"

_VERSION = re.compile(r"^(?:\^|~|>=)?(\d+)\.(\d+)\.(\d+)$")


def _numeric(version: str) -> tuple[int, int, int] | None:
    match = _VERSION.match(version.strip())
    return (int(match[1]), int(match[2]), int(match[3])) if match else None


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Report a root `package.json` whose `nx` is below kiln's `NX_VERSION`."""
    path = root / "package.json"
    if config.archetype != "node-lib" or not path.is_file():
        return []
    manifest = json.loads(path.read_text(encoding="utf-8"))
    found = next(
        (
            nx
            for section in ("devDependencies", "dependencies")
            if isinstance(nx := manifest.get(section, {}).get("nx"), str)
        ),
        "",
    )
    current = _numeric(found)
    pinned = _numeric(NX_VERSION)
    if current is None or pinned is None or current >= pinned:
        return []
    return [
        Finding(
            f"{CODE}.nx-behind",
            Severity.ERROR,
            f"nx {found.lstrip('^~>=')} is below kiln's {NX_VERSION}; run "
            f"`pnpm exec nx migrate {NX_VERSION}` and its migrations",
            path="package.json",
        )
    ]
