"""The `origin` remote of a Git worktree, read through `git`."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

__all__ = ["github_owner", "origin_url", "repository_name"]

_GITHUB = re.compile(r"^(?:https://github\.com/|git@github\.com:)(?P<owner>[^/]+)/")


def origin_url(root: Path) -> str | None:
    """The URL of *root*'s `origin` remote, or `None` if there is none.

    *root* must hold its own `.git`: a directory inside another worktree has no
    remote of its own.
    """
    if not (root / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    url = result.stdout.strip()
    return url if result.returncode == 0 and url else None


def repository_name(url: str) -> str:
    """The repository name in *url*: the last path part, `.git` stripped."""
    last = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    return last.removesuffix(".git")


def github_owner(url: str) -> str | None:
    """The owner in a GitHub https or ssh *url*, or `None` for any other host."""
    match = _GITHUB.match(url)
    return match.group("owner") if match else None
