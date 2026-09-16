"""Fetching the source layer a config resolves from: a local path or a git URL."""

from __future__ import annotations

import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rn_forge.commons.exceptions import AppException

from rn_forge.kiln.modules.core.config.schema import SourceConfig

__all__ = ["Fetched", "Source", "fetch"]

_GIT_PREFIX = "git+"
_LAYER_FILE = "config.toml"


@dataclass(frozen=True, slots=True)
class Source:
    """Where a config layer comes from.

    Args:
        location: A local path (a `config.toml`, or a directory holding one),
            or a `git+` URL of a repository holding `config.toml` at its root.
        ref: The branch, tag or commit to read, for a git location.
    """

    location: str
    ref: str | None = None

    @classmethod
    def parse(cls, value: str) -> Source:
        """Read `path` or `git+url[@ref]` as a source."""
        if value.startswith(_GIT_PREFIX):
            head, at, ref = value.rpartition("@")
            if at and "/" not in ref and ":" not in ref:
                return cls(head, ref)
        return cls(value)

    @property
    def is_git(self) -> bool:
        """Whether this source is a git repository."""
        return self.location.startswith(_GIT_PREFIX)


@dataclass(frozen=True, slots=True)
class Fetched:
    """A fetched source layer, and the `[source]` record it resolves to."""

    document: dict[str, Any]
    record: SourceConfig


def fetch(source: Source, base: Path) -> Fetched:
    """Read *source*'s layer; a relative path resolves against *base*.

    Raises:
        AppException: The source cannot be read, or holds no valid TOML layer.
    """
    if not source.is_git:
        path = base / source.location
        return Fetched(_read_layer(path), SourceConfig(location=source.location))

    with tempfile.TemporaryDirectory(prefix="kiln-source-") as scratch:
        checkout = Path(scratch)
        url = source.location.removeprefix(_GIT_PREFIX)
        _git("clone", "--quiet", url, str(checkout))
        if source.ref is not None:
            _git("-C", str(checkout), "checkout", "--quiet", source.ref)
        commit = _git("-C", str(checkout), "rev-parse", "HEAD")
        return Fetched(
            _read_layer(checkout),
            SourceConfig(location=source.location, ref=source.ref, commit=commit),
        )


def _read_layer(path: Path) -> dict[str, Any]:
    file = path / _LAYER_FILE if path.is_dir() else path
    try:
        document = tomllib.loads(file.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise AppException("config source {}: {}", file, error) from error
    # A layer supplies values; the record of where it came from is kiln's to write.
    document.pop("source", None)
    return document


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AppException(
            "git {} failed: {}",
            " ".join(args),
            result.stderr.strip() or result.stdout.strip(),
        )
    return result.stdout.strip()
