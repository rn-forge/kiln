"""Scaffolding: `uv init`, then reconciling toward what check 8a expects.

Runs once, from `kiln new`, before the first `apply` (kiln ADR-0005). This is
the only subprocess kiln starts — `apply` never shells out — and it never
templates `uv init`'s own output (D16): it only fixes the `pyproject.toml`
sections check 8a verifies, using the same expected values that check reads.
"""

from __future__ import annotations

import os
from pathlib import Path

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

    for relative in archetypes.pyproject_paths(config):
        path = root / relative
        _reconcile(
            path,
            name=path.parent.name if path.parent != root else config.name,
            venv_path=os.path.relpath(root, path.parent) or ".",
            is_root=path.parent == root,
            is_workspace_root=workspace and path.parent == root,
        )


def _uv_init(target: Path, *, name: str, bare: bool) -> None:
    args = ["uv", "init", "--name", name, "--vcs", "none", "--no-readme"]
    args += ["--bare"] if bare else ["--package", "--build-backend", "uv"]
    Process.execute(f"uv-init[{name}]", *args, cwd=str(target))


def _reconcile(
    path: Path, *, name: str, venv_path: str, is_root: bool, is_workspace_root: bool
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
    updates: dict[str, object] = {
        "project": {"requires-python": REQUIRES_PYTHON},
        "tool": tool,
    }
    if is_root:
        updates["dependency-groups"] = {"dev": [*_DEV_GROUP, "rn-forge-kiln"]}
    DocumentUtils.update(path, updates)
