"""The `[ci]` config section."""

from __future__ import annotations

from typing import Literal

from rn_forge.commons.lang.models import StrictModel

__all__ = ["CiConfig"]


class CiConfig(StrictModel):
    """Which CI provider the workflows target, and what they run."""

    provider: Literal["github", "ado"] = "github"
    """`ado` is reserved."""
    sonar: bool = True
    release: Literal["tag-exists", "none"] = "tag-exists"
