"""The `requirements` check: workspace members depend on each other by range."""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from rn_forge.kiln.devops import uv


def _problem(requirement: Requirement, current: Version) -> str | None:
    """Return what is wrong with how `requirement` bounds a member, if anything."""
    specs = list(requirement.specifier)
    if any(s.operator in ("==", "===") and "*" not in s.version for s in specs):
        return "exact pin"
    floors = [
        Version(s.version.rstrip(".*"))
        for s in specs
        if s.operator in (">=", ">", "~=")
    ]
    if not floors:
        return "no lower bound"
    floor = max(floors)
    if floor > current:
        return f"lower bound {floor} is above {current}"
    return None


def check(root: Path) -> list[str]:
    """Return one `a -> b: problem` line per internal dependency that is not a range.

    Checks the `dependencies` and `optional-dependencies` of every member of the
    uv workspace at `root` that name another member. Dependency groups are not
    published, so they are not checked.

    Args:
        root: The workspace root.
    """
    members = {
        canonicalize_name(package.name): root / package.dir
        for package in uv.load_workspace(root).packages.values()
    }
    projects = {
        name: tomllib.loads((path / uv.MANIFEST).read_text(encoding="utf-8"))["project"]
        for name, path in members.items()
    }
    versions = {name: Version(p["version"]) for name, p in projects.items()}
    problems: list[str] = []
    for name, project in sorted(projects.items()):
        entries: list[str] = list(project.get("dependencies", []))
        for extra in project.get("optional-dependencies", {}).values():
            entries += extra
        for entry in entries:
            requirement = Requirement(entry)
            target = canonicalize_name(requirement.name)
            if target == name or target not in members:
                continue
            problem = _problem(requirement, versions[target])
            if problem:
                problems.append(f"{name} -> {target}: {problem}")
    return problems
