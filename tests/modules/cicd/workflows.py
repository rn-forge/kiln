"""Job lookup over a rendered `ci.yml` and its reusable `_*.yml` workflows."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from rn_forge.commons.fs.documents import YamlUtils

_WORKFLOWS = ".github/workflows"


def jobs(files: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Return the merged `jobs` mappings of `ci.yml` and every `_*.yml` in `files`.

    Args:
        files: The rendered file map, path to content.

    Returns:
        Job name to job body, `ci.yml`'s jobs first.
    """
    merged: dict[str, dict[str, Any]] = {}
    paths = [f"{_WORKFLOWS}/ci.yml"] + sorted(
        p
        for p in files
        if PurePosixPath(p).parent.as_posix() == _WORKFLOWS
        and PurePosixPath(p).name.startswith("_")
        and p.endswith(".yml")
    )
    for path in paths:
        if path in files:
            merged.update(YamlUtils.load(files[path]).get("jobs") or {})
    return merged
