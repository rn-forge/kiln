"""The `python` module: its artifacts, and the rules it owns."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from rn_forge.kiln.modules.base import Option
from rn_forge.kiln.modules.python.config import ArchetypeConfig

if TYPE_CHECKING:
    from rn_forge.commons.findings import Finding
    from rn_forge.tooling.generation import Artifact

    from rn_forge.kiln.config import KilnConfig

__all__ = ["PYTHON", "PythonModule"]


class PythonModule:
    """The `python` module."""

    name = "python"
    section: str | None = "archetype"
    config_model = ArchetypeConfig

    def options(self) -> Sequence[Option]:
        """The `kiln new` flags this module adds."""
        return ()

    def artifacts(self, config: KilnConfig) -> Sequence[Artifact]:
        """Render `.importlinter` for *config*."""
        # Imported here so importing a module object never loads jinja2.
        from rn_forge.kiln.modules.python import artifacts

        return artifacts.render(config)

    def checks(self, config: KilnConfig, root: Path) -> Sequence[Finding]:
        """This module's render-free checks."""
        # Imported here so importing a module object never loads its checks.
        from rn_forge.kiln.modules.python.checks import pyproject, rn_forge_deps

        return [*rn_forge_deps.check(config, root), *pyproject.check(config, root)]


PYTHON = PythonModule()
