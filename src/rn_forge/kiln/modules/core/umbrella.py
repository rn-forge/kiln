"""The `.rn-forge/kiln/` umbrella: finding a repo's root, and refusing legacy trees."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.paths import PathUtils

from rn_forge.kiln.config import CONFIG_PATH

__all__ = [
    "BACKUPS",
    "LEGACY_CODE",
    "RENDERED",
    "STATE_PATH",
    "UMBRELLA",
    "find_root",
    "legacy",
]

UMBRELLA = Path(".rn-forge/kiln")
STATE_PATH = UMBRELLA / "state.json"
BACKUPS = UMBRELLA / "backups"
RENDERED = UMBRELLA / "rendered"

LEGACY_CODE = "legacy.kiln-state"


def find_root(start: Path) -> Path:
    """The nearest ancestor of *start*, itself included, holding a kiln config.

    Raises:
        AppException: No ancestor holds one.
    """
    return PathUtils.find_root(start, markers=(CONFIG_PATH,), fallback="raise")


def legacy(*trees: Path) -> list[Finding]:
    """A `legacy.kiln-state` error for each non-empty tree that declares no `schema_version`.

    Args:
        trees: `.rn-forge/kiln/` directories to inspect — a repo's, and
            `$RNF_HOME/kiln/`. One that does not exist is fine.
    """
    return [
        Finding(
            LEGACY_CODE,
            Severity.ERROR,
            "a kiln tree without schema_version belongs to kiln's retired "
            "predecessor — remove it, then run kiln again",
            path=str(tree),
        )
        for tree in trees
        if tree.is_dir() and any(tree.iterdir()) and not _declares_schema_version(tree)
    ]


def _declares_schema_version(tree: Path) -> bool:
    config = tree / "config.toml"
    state = tree / "state.json"
    try:
        if config.is_file() and "schema_version" in tomllib.loads(
            config.read_text(encoding="utf-8")
        ):
            return True
        if state.is_file() and "schema_version" in json.loads(
            state.read_text(encoding="utf-8")
        ):
            return True
    except tomllib.TOMLDecodeError, json.JSONDecodeError:
        return False
    return False
