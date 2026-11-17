"""The git adapter: the revisions, changes and tags the planner reads."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# A revision name never starts with `-`, so it cannot be read as a git option.
REVISION = r"[A-Za-z0-9_][A-Za-z0-9_./@-]*"


def _quiet(root: Path, command: list[str]) -> bool:
    result = subprocess.run(
        command,
        check=False,
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def usable_base(root: Path, base: str) -> bool:
    """Return whether `base` is a plain revision name for a commit that is an ancestor of `HEAD`."""
    return (
        re.fullmatch(REVISION, base) is not None
        and _quiet(
            root, ["git", "cat-file", "-e", "--end-of-options", f"{base}^{{commit}}"]
        )
        and _quiet(
            root,
            ["git", "merge-base", "--is-ancestor", "--end-of-options", base, "HEAD"],
        )
    )


def changed_files(root: Path, base: str) -> list[str]:
    """Return the paths changed between `base` and `HEAD`.

    Raises:
        ValueError: When `base` is not a plain revision name.
    """
    if not re.fullmatch(REVISION, base):
        raise ValueError(f"invalid base {base!r}")
    out = subprocess.run(
        ["git", "diff", "--name-only", "--end-of-options", f"{base}...HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return out.splitlines()


def tags_at_head(root: Path) -> list[str]:
    """Return the tags that point at `HEAD`."""
    return subprocess.run(
        ["git", "tag", "--points-at", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
