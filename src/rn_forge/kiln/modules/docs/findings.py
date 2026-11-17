"""The finding every docs check builds."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

__all__ = ["error"]


def error(code: str, path: Path | str, message: str) -> Finding:
    """An error finding at *path*, with `docs.` put before *code*."""
    return Finding(f"docs.{code}", Severity.ERROR, message, path=str(path))
