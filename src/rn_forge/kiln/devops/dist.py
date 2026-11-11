"""A built package's manifest: resolve `workspace:` ranges and verify it."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

_PREFIX = "workspace:"
_FIELDS = ("dependencies", "peerDependencies", "optionalDependencies")


def _range(range_: str, dep: str, version: str | None) -> str:
    if not version:
        raise ValueError(
            f'Cannot resolve "{range_}" for "{dep}": no local package version found'
        )
    value = range_.removeprefix(_PREFIX)
    if value in ("*", ""):
        return version
    if value in ("^", "~"):
        return f"{value}{version}"
    return value


def resolve(
    manifest: dict[str, Any], versions: Callable[[], Mapping[str, str]]
) -> tuple[dict[str, Any], bool]:
    """Rewrite each `workspace:` range to a real semver range, and drop `workspace-ci`.

    Args:
        manifest: The dist `package.json` content.
        versions: Returns the local packages' versions; called at most once, and
            only when a `workspace:` range is found.

    Returns:
        The new manifest and whether anything changed.

    Raises:
        ValueError: When a dependency has no local version.
    """
    result = copy.deepcopy(manifest)
    known: Mapping[str, str] | None = None
    changed = False
    for field in _FIELDS:
        deps = result.get(field)
        if not deps:
            continue
        for dep, range_ in deps.items():
            if isinstance(range_, str) and range_.startswith(_PREFIX):
                if known is None:
                    known = versions()
                deps[dep] = _range(range_, dep, known.get(dep))
                changed = True
    if result.pop("workspace-ci", None) is not None:
        changed = True
    return result, changed


def problems(manifest: dict[str, Any]) -> list[str]:
    """Return what is wrong with a dist manifest, in report order; `[]` when valid."""
    found: list[str] = []
    for field in _FIELDS:
        deps: dict[str, Any] = manifest.get(field) or {}
        for dep, range_ in deps.items():
            if isinstance(range_, str) and range_.startswith(_PREFIX):
                found.append(
                    f'{field}["{dep}"] uses "workspace:" protocol ({range_}) in dist manifest'
                )
    for field in ("name", "version"):
        if not manifest.get(field):
            found.append(f'missing required field "{field}"')
    if not manifest.get("module") and not manifest.get("exports"):
        found.append('missing both "module" and "exports" (no entry point referenced)')
    if not manifest.get("typings") and not manifest.get("exports"):
        found.append(
            'missing both "typings" and "exports" (no type declarations referenced)'
        )
    return found
