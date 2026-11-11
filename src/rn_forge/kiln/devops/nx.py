"""The Nx adapter: the only module that runs `pnpm exec nx`."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _nx(root: Path, *args: str) -> object:
    result = subprocess.run(
        ["pnpm", "exec", "nx", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def projects(root: Path, target: str | None = None) -> list[str]:
    """Return the names of the workspace's Nx projects.

    Args:
        root: The workspace root.
        target: When given, only the projects that have this target.
    """
    args = ["show", "projects", "--json"]
    if target:
        args += ["--with-target", target]
    return list(_nx(root, *args))  # type: ignore[call-overload]


def project_root(root: Path, project: str) -> str:
    """Return the root directory of `project`, relative to the workspace root."""
    return str(_nx(root, "show", "project", project, "--json")["root"])  # type: ignore[index]


def local_versions(root: Path) -> dict[str, str]:
    """Map each local package's name to its version.

    A project with no readable `package.json`, or one without both fields, is skipped.
    """
    versions: dict[str, str] = {}
    for project in projects(root):
        try:
            package = json.loads(
                (root / project_root(root, project) / "package.json").read_text(
                    encoding="utf-8"
                )
            )
        except OSError, ValueError:
            continue
        if package.get("name") and package.get("version"):
            versions[package["name"]] = package["version"]
    return versions
