"""`root-hygiene` — prose lives in `docs/`, not in loose Markdown at the repo root."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln.config import KilnConfig

__all__ = ["ALLOWED", "CODE", "NAME", "check"]

NAME = "root-hygiene"
CODE = "hygiene.stray-root-file"

ALLOWED = frozenset(
    {"README.md", "CLAUDE.md", "AGENTS.md", "CHANGELOG.md", "CONTRIBUTING.md"}
)
"""The root-level Markdown files a repo may carry."""


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Warn on every root-level `*.md` file outside the allow-list."""
    del config
    return [
        Finding(
            CODE,
            Severity.WARNING,
            f"{path.name} is Markdown at the repo root — move it under docs/",
            path=path.name,
        )
        for path in sorted(root.glob("*.md"))
        if path.is_file() and path.name not in ALLOWED
    ]
