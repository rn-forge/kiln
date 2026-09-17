"""Scaffolding: the repo-owned bodies of `README.md`, `CLAUDE.md` and `AGENTS.md`.

Runs once, from `kiln new`, before the first `apply`. `CLAUDE.md`'s body carries
no block markers, so the apply that follows appends the kiln block beneath it.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.instructions.artifacts import context

__all__ = ["BODIES", "scaffold"]

BODIES = ("README.md", "CLAUDE.md", "AGENTS.md")
"""Every scaffolded body, each rendered from `templates/<name>.j2`."""


def scaffold(root: Path, config: KilnConfig) -> None:
    """Write each of `README.md`, `CLAUDE.md` and `AGENTS.md` into *root* that is absent."""
    engine = TemplateEngine(package="rn_forge.kiln.modules.instructions")
    values = context(config)
    for name in BODIES:
        target = root / name
        if not target.exists():
            target.write_text(engine.render(f"{name}.j2", values), encoding="utf-8")
