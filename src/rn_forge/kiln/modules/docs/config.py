"""The `[docs]` config section."""

from __future__ import annotations

from typing import Literal

from rn_forge.commons.lang.models import StrictModel

__all__ = ["DocsConfig"]


class DocsConfig(StrictModel):
    """How the repo publishes its documentation."""

    profile: Literal["mkdocs", "external", "none"] = "none"
    site_dir: str = ".docs-site"
    """Where `mkdocs` builds the site; `mkdocs` only."""
    external_url: str = ""
    """Where the docs live; `external` only."""
