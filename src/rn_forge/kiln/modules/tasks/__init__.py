"""The `tasks` module: its artifacts, and the rules it owns."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from rn_forge.kiln.modules.base import Option
from rn_forge.kiln.modules.tasks.config import TasksConfig

if TYPE_CHECKING:
    from rn_forge.commons.generation import Artifact

    from rn_forge.kiln.config import KilnConfig

__all__ = ["TASKS", "TasksModule"]


class TasksModule:
    """The `tasks` module."""

    name = "tasks"
    section: str | None = "tasks"
    config_model = TasksConfig

    def options(self) -> Sequence[Option]:
        """The `kiln new` flags this module adds."""
        return ()

    def artifacts(self, config: KilnConfig, root: Path) -> Sequence[Artifact]:
        """Render `Taskfile.yml`, `tasks/*.yml`, and any repo-owned includes."""
        del root
        # Imported here so importing a module object never loads jinja2.
        from rn_forge.kiln.modules.tasks import artifacts

        return artifacts.render(config)


TASKS = TasksModule()
