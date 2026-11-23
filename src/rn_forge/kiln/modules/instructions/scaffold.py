"""Scaffolding: the repo-owned body of `README.md`.

Runs once, from `kiln new`, before the first `apply`. The apply that follows
creates `AGENTS.md` holding only the kiln block.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.instructions.artifacts import context

__all__ = ["BODIES", "scaffold"]

BODIES = ("README.md",)
"""Every scaffolded body, each rendered from `templates/<name>.j2`."""


def scaffold(root: Path, config: KilnConfig) -> None:
    """Write `README.md` into *root* when it is absent."""
    engine = TemplateEngine.cached(package="rn_forge.kiln.modules.instructions")
    values = context(config)
    for name in BODIES:
        target = root / name
        if not target.exists():
            target.write_text(engine.render(f"{name}.j2", values), encoding="utf-8")
