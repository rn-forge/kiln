"""Scaffolding: `uv init`, then reconciling toward what check 8a expects.

Runs once, from `kiln new`, before the first `apply` (kiln ADR-0005). This is
the only subprocess kiln starts — `apply` never shells out — and it never
templates `uv init`'s own output (D16): it only fixes the `pyproject.toml`
sections check 8a verifies, using the same expected values that check reads.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import cast

from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.runtime.subprocess import Process

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.python.checks.pyproject import (
    PYRIGHT_EXPECTED,
    PYTEST_ADDOPTS,
    REQUIRES_PYTHON,
    RUFF_TEST_IGNORES,
)

__all__ = ["scaffold"]

_DEV_GROUP = ["import-linter", "pyright", "pytest", "pytest-cov", "pyyaml", "ruff"]
"""The dev tools every archetype's `pyproject.toml` names; `rn-forge-kiln` too,
added separately since its distribution name differs from its PyPI-style
default and it is the one the dependency check itself excludes from the
rn-forge contract."""

_DOCS_GROUP = [
    "mdformat>=1.0.0",
    "mdformat-gfm>=0.4",
    "mdformat-front-matters>=2.0.0",
    "mdformat-mkdocs>=5.3.0",
]
"""The `docs` dependency group's shared entries, present for every docs profile."""
_DOCS_GROUP_MKDOCS = ["mkdocs-material>=9.6", "mkdocstrings[python]>=0.30"]
"""Added to the `docs` group only when `docs.profile == "mkdocs"`."""


def scaffold(root: Path, config: KilnConfig) -> None:
    """Run `uv init` into *root*, then reconcile every `pyproject.toml` it makes.

    For `python-lib`, also runs `uv init` for each workspace member in
    `config.packages` and wires the workspace table at the root. `uv init`
    itself refuses a directory that already holds a `pyproject.toml`, so this
    is meant to run once, into an empty directory, before the first `apply`.

    Raises:
        AppException: `uv` is not on `PATH`, or exits non-zero.
    """
    workspace = config.archetype == "python-lib"
    if workspace:
        _uv_init(root, name=config.name, bare=True)
        for package in config.packages:
            member = root / package
            member.mkdir(parents=True, exist_ok=True)
            _uv_init(member, name=Path(package).name, bare=False)
        DocumentUtils.update(
            root / "pyproject.toml",
            {
                "tool": {
                    "uv": {
                        "package": False,
                        "workspace": {"members": list(config.packages)},
                    }
                }
            },
        )
    else:
        _uv_init(root, name=config.name, bare=False)

    required = archetypes.for_config(config).dependencies.required
    for relative in archetypes.pyproject_paths(config):
        path = root / relative
        is_root = path.parent == root
        is_workspace_root = workspace and is_root
        _reconcile(
            path,
            name=path.parent.name if path.parent != root else config.name,
            venv_path=os.path.relpath(root, path.parent) or ".",
            is_root=is_root,
            is_workspace_root=is_workspace_root,
            dependencies=()
            if is_workspace_root
            else tuple(archetypes.requirement(d) for d in required),
            mkdocs=config.docs_profile == "mkdocs",
        )


def _uv_init(target: Path, *, name: str, bare: bool) -> None:
    args = ["uv", "init", "--name", name, "--vcs", "none", "--no-readme"]
    args += ["--bare"] if bare else ["--package", "--build-backend", "uv"]
    Process.execute(f"uv-init[{name}]", *args, cwd=str(target))


def _reconcile(
    path: Path,
    *,
    name: str,
    venv_path: str,
    is_root: bool,
    is_workspace_root: bool,
    dependencies: tuple[str, ...],
    mkdocs: bool,
) -> None:
    test_glob = "**/tests/*" if is_workspace_root else "tests/*"
    tool: dict[str, object] = {
        "pyright": {**PYRIGHT_EXPECTED, "venv": ".venv", "venvPath": venv_path},
        "pytest": {"ini_options": {"addopts": PYTEST_ADDOPTS}},
        "ruff": {"lint": {"per-file-ignores": {test_glob: sorted(RUFF_TEST_IGNORES)}}},
    }
    if not is_workspace_root:
        tool["uv"] = {
            "build-backend": {
                "module-name": name.replace("-", "_"),
                "source-exclude": ["**/.DS_Store"],
            }
        }
    project: dict[str, object] = {"requires-python": REQUIRES_PYTHON}
    if dependencies:
        existing = _existing_list(path, "project", "dependencies")
        project["dependencies"] = [*existing, *dependencies]
    updates: dict[str, object] = {"project": project, "tool": tool}
    if is_root:
        dev = [*_DEV_GROUP, f"rn-forge-kiln @ {archetypes.KILN_SOURCE}"]
        docs = [*_DOCS_GROUP, *(_DOCS_GROUP_MKDOCS if mkdocs else [])]
        updates["dependency-groups"] = {
            "dev": [*_existing_list(path, "dependency-groups", "dev"), *dev],
            "docs": [*_existing_list(path, "dependency-groups", "docs"), *docs],
        }
    DocumentUtils.update(path, updates)


def _existing_list(path: Path, *keys: str) -> list[str]:
    """The list already at *keys* in *path*'s document, or `[]`.

    `DocumentUtils.update` deep-merges tables but replaces lists wholesale, so
    callers that mean to extend a list read it first.
    """
    if not path.is_file():
        return []
    value: object = tomllib.loads(path.read_text(encoding="utf-8"))
    for key in keys:
        value = (
            cast("dict[str, object]", value).get(key)
            if isinstance(value, dict)
            else None
        )
    return cast("list[str]", value) if isinstance(value, list) else []
