"""The pinned action set kiln renders into workflows and tasks."""

from __future__ import annotations

from importlib.resources import files
from typing import cast

from rn_forge.commons.fs.documents import DocumentUtils

__all__ = ["load_pins"]

_PACKAGE = "rn_forge.kiln.modules.core"


def load_pins() -> dict[str, dict[str, str]]:
    """The pinned action set, one table per action, from `pins.toml`."""
    return cast(
        "dict[str, dict[str, str]]",
        DocumentUtils.read(files(_PACKAGE).joinpath("pins.toml")),
    )
