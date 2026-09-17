"""The `instructions` module: its artifacts, and the rules it owns."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from rn_forge.kiln.modules.base import Option

if TYPE_CHECKING:
    from rn_forge.commons.findings import Finding
    from rn_forge.tooling.generation import Artifact

    from rn_forge.kiln.config import KilnConfig

__all__ = ["INSTRUCTIONS", "InstructionsModule"]


class InstructionsModule:
    """The `instructions` module."""

    name = "instructions"
    section: str | None = None
    config_model = None

    def options(self) -> Sequence[Option]:
        """The `kiln new` flags this module adds."""
        return ()

    def artifacts(self, config: KilnConfig, root: Path) -> Sequence[Artifact]:
        """Render the kiln block in `CLAUDE.md` and `.rn-forge/kiln/standard.md`."""
        del root
        # Imported here so importing a module object never loads jinja2.
        from rn_forge.kiln.modules.instructions import artifacts

        return artifacts.render(config)

    def checks(self, config: KilnConfig, root: Path) -> Sequence[Finding]:
        """This module's render-free checks."""
        from rn_forge.kiln.modules.instructions.checks import hygiene

        return hygiene.check(config, root)


INSTRUCTIONS = InstructionsModule()
