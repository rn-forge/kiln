"""The `core` module: the `.rn-forge/kiln/` umbrella, the config manager and the apply cycle."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from rn_forge.kiln.modules.base import Option

if TYPE_CHECKING:
    from rn_forge.commons.findings import Finding
    from rn_forge.tooling.generation import Artifact

    from rn_forge.kiln.config import KilnConfig

__all__ = ["CORE", "CoreModule"]


class CoreModule:
    """The `core` module. Its config is the root `[repository]` table."""

    name = "core"
    section: str | None = None
    config_model = None

    def options(self) -> Sequence[Option]:
        """The `kiln new` flags this module adds."""
        return (
            Option(
                "archetype", "repository.archetype", "The archetype the repo asserts."
            ),
        )

    def artifacts(self, config: KilnConfig) -> Sequence[Artifact]:
        """`.editorconfig` and the `.gitignore` block."""
        # Imported here: rendering loads Jinja, which `kiln doctor` must not.
        from rn_forge.kiln.modules.core import artifacts

        return artifacts.render(config)

    def checks(self, config: KilnConfig, root: Path) -> Sequence[Finding]:
        """The committed-state baseline check."""
        from rn_forge.kiln.modules.core.checks import generated

        return generated.check(config, root)


CORE = CoreModule()
