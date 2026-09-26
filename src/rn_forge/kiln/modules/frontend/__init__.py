"""The `frontend` module: scaffolding for the pnpm/Nx frontend workspace."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from rn_forge.kiln.modules.base import Option

if TYPE_CHECKING:
    from rn_forge.commons.findings import Finding
    from rn_forge.commons.lang.models import StrictModel
    from rn_forge.tooling.generation import Artifact

    from rn_forge.kiln.config import KilnConfig

__all__ = ["FRONTEND", "FrontendModule"]


class FrontendModule:
    """The `frontend` module.

    Owns no config section and renders nothing: the archetype owns the
    validated `frontend` and `web_dir` values, and every file the frontend
    scaffold writes is repo-owned. It owns the `--frontend` selector and the
    scaffold that runs it.
    """

    name = "frontend"
    section: str | None = None
    config_model: type[StrictModel] | None = None

    def options(self) -> Sequence[Option]:
        """The `kiln new` flags this module adds."""
        return (
            Option(
                "frontend",
                "archetype.<archetype>.frontend",
                "The frontend: angular, react or svelte (python-web-app only).",
            ),
        )

    def artifacts(self, config: KilnConfig, root: Path) -> Sequence[Artifact]:
        """Nothing: kiln templates nothing under `web_dir`."""
        del config, root
        return ()

    def checks(self, config: KilnConfig, root: Path) -> Sequence[Finding]:
        """Nothing yet: this module has no render-free checks."""
        del config, root
        return ()


FRONTEND = FrontendModule()
