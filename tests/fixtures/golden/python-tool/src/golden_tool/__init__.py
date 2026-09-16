"""The one function this golden repo exists to have."""

from __future__ import annotations

from rn_forge.commons import DictUtils

DEFAULTS: dict[str, str] = {"greeting": "Hello", "punctuation": "!"}


def greet(name: str, **overrides: str) -> str:
    """Return a greeting for ``name``, with ``DEFAULTS`` overridable per call."""
    settings = DictUtils.merge(dict(DEFAULTS), overrides)
    return f"{settings['greeting']}, {name}{settings['punctuation']}"
