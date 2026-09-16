"""The `docs` module: its artifacts, and the rules it owns."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from rn_forge.kiln.modules.base import Option
from rn_forge.kiln.modules.docs.config import DocsConfig

if TYPE_CHECKING:
    from rn_forge.commons.findings import Finding
    from rn_forge.tooling.generation import Artifact

    from rn_forge.kiln.config import KilnConfig

__all__ = ["DOCS", "DocsModule"]


class DocsModule:
    """The `docs` module."""

    name = "docs"
    section: str | None = "docs"
    config_model = DocsConfig

    def options(self) -> Sequence[Option]:
        """The `kiln new` flags this module adds."""
        return (
            Option(
                "docs", "docs.profile", "The docs profile: mkdocs, external or none."
            ),
        )

    def artifacts(self, config: KilnConfig) -> Sequence[Artifact]:
        """No artifacts."""
        del config
        return ()

    def checks(self, config: KilnConfig, root: Path) -> Sequence[Finding]:
        """This module's render-free checks."""
        from rn_forge.kiln.modules.docs.checks import nav, site, structure

        return [
            *structure.check(config, root),
            *nav.check(config, root),
            *site.check(config, root),
        ]


DOCS = DocsModule()
