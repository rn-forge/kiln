"""The modules this kiln ships."""

from __future__ import annotations

from rn_forge.kiln.modules.base import ModuleRegistry
from rn_forge.kiln.modules.cicd import CICD
from rn_forge.kiln.modules.core import CORE
from rn_forge.kiln.modules.docs import DOCS
from rn_forge.kiln.modules.instructions import INSTRUCTIONS
from rn_forge.kiln.modules.python import PYTHON
from rn_forge.kiln.modules.tasks import TASKS

__all__ = ["builtin"]


def builtin() -> ModuleRegistry:
    """A registry of every module this kiln ships."""
    return ModuleRegistry([CORE, PYTHON, DOCS, TASKS, CICD, INSTRUCTIONS])
