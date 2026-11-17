"""Names derived from other names."""

from __future__ import annotations

__all__ = ["module_name"]


def module_name(distribution: str) -> str:
    """The import module of the distribution *distribution*."""
    return distribution.replace("-", "_")
