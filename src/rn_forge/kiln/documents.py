"""Typed reads of untyped documents.

`tomllib` and `yaml.safe_load` both hand back arbitrarily shaped data. These
four helpers narrow one step of it to a known type each.

They never raise: a value of the wrong shape reads as absent.
"""

from __future__ import annotations

from typing import cast

__all__ = ["mapping", "sequence", "strings", "table"]


def mapping(value: object) -> dict[str, object]:
    """*value* as a string-keyed mapping, or empty if it is anything else."""
    if not isinstance(value, dict):
        return {}
    # `isinstance` narrows to `dict[Unknown, Unknown]`, which is exactly what a
    # parsed document is; the cast says so rather than leaking it to callers.
    return {str(key): item for key, item in cast("dict[object, object]", value).items()}


def table(document: object, *keys: str) -> dict[str, object]:
    """The nested mapping at *keys*, or empty if any step is missing."""
    current = mapping(document)
    for key in keys[:-1]:
        current = mapping(current.get(key))
    return mapping(current.get(keys[-1])) if keys else current


def sequence(value: object) -> list[object]:
    """*value* as a list. A lone scalar reads as a one-element list."""
    if isinstance(value, list):
        return list(cast("list[object]", value))
    return [] if value is None else [value]


def strings(value: object) -> list[str]:
    """The string elements of *value* as a list, ignoring anything else."""
    return [item for item in sequence(value) if isinstance(item, str)]
