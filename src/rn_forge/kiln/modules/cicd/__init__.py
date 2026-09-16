"""The `cicd` module: its artifacts, and the rules it owns."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from rn_forge.kiln.modules.base import Option
from rn_forge.kiln.modules.cicd.config import CiConfig

if TYPE_CHECKING:
    from rn_forge.commons.findings import Finding
    from rn_forge.tooling.generation import Artifact

    from rn_forge.kiln.config import KilnConfig

__all__ = ["CICD", "CicdModule"]


class CicdModule:
    """The `cicd` module."""

    name = "cicd"
    section: str | None = "ci"
    config_model = CiConfig

    def options(self) -> Sequence[Option]:
        """The `kiln new` flags this module adds."""
        return ()

    def artifacts(self, config: KilnConfig) -> Sequence[Artifact]:
        """No artifacts."""
        del config
        return ()

    def checks(self, config: KilnConfig, root: Path) -> Sequence[Finding]:
        """This module's render-free checks."""
        from rn_forge.kiln.modules.cicd.checks import entrypoint

        return entrypoint.check(config, root)


CICD = CicdModule()
