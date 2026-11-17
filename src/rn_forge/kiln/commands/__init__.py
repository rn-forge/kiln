"""The commands kiln's CLI exposes, one module each."""

from __future__ import annotations

from rn_forge.kiln.commands.apply import apply
from rn_forge.kiln.commands.config import config_update, config_upgrade, pin
from rn_forge.kiln.commands.diff import diff
from rn_forge.kiln.commands.doctor import doctor
from rn_forge.kiln.commands.generate import (
    docs_generate,
    generate_app,
    generate_package,
)
from rn_forge.kiln.commands.info import prompt, version
from rn_forge.kiln.commands.new import new

__all__ = [
    "apply",
    "config_update",
    "config_upgrade",
    "diff",
    "docs_generate",
    "doctor",
    "generate_app",
    "generate_package",
    "new",
    "pin",
    "prompt",
    "version",
]
