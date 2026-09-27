"""Scaffolding: `uv init`, then reconciling toward what check 8a expects.

Runs once, from `kiln new`, before the first `apply` (kiln ADR-0005). This is
the only subprocess kiln starts — `apply` never shells out — and it never
templates `uv init`'s own output (D16): it only fixes the `pyproject.toml`
sections check 8a verifies, using the same expected values that check reads.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import tomllib
from pathlib import Path
from typing import Any, cast

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.runtime.subprocess import Process

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import gitignore
from rn_forge.kiln.modules.python.checks.pyproject import (
    PYRIGHT_EXPECTED,
    PYTEST_ADDOPTS,
    REQUIRES_PYTHON,
    RUFF_TEST_IGNORES,
)

__all__ = [
    "UV_VERSION",
    "reconcile_backend",
    "scaffold",
    "scaffold_backend",
    "uv_gitignore",
]

UV_VERSION = "0.12.19"
"""The uv release this scaffold is recorded against (2026-09-27,
`tests/fixtures/scaffold/uv/COMMAND.md`)."""

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

    `scaffold_backend` and `reconcile_backend` in one place: the output is
    reconciled where it was written. `kiln new` runs the two halves apart.

    Raises:
        AppException: `uv` is not on `PATH`, or exits non-zero.
    """
    scaffold_backend(root, config)
    _reconcile_tree(root, config)


def scaffold_backend(raw: Path, config: KilnConfig) -> None:
    """Run `uv init` into *raw*: the raw output, before any reconcile.

    For `python-lib` and the web archetypes, also runs `uv init` for each
    workspace member in `config.packages` and wires the workspace table at the
    root. `uv init` itself refuses a directory that already holds a
    `pyproject.toml`, so *raw* must be empty. Writes uv's own ignore body to
    `raw/.gitignore`, once, from `uv_gitignore`.

    Raises:
        AppException: `uv` is not on `PATH`, is not `UV_VERSION`, or exits
            non-zero.
    """
    _verify_uv()
    workspace = config.archetype == "python-lib"
    web = config.archetype in {"python-web-api", "python-web-app"}
    if workspace or web:
        _uv_init(raw, name=config.name, bare=True)
        for package in config.packages:
            member = raw / package
            member.mkdir(parents=True, exist_ok=True)
            member_name = f"{config.name}-api" if web else Path(package).name
            _uv_init(member, name=member_name, bare=False)
        DocumentUtils.update(
            raw / "pyproject.toml",
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
        _uv_init(raw, name=config.name, bare=False)
    (raw / gitignore.GITIGNORE).write_text(uv_gitignore(), encoding="utf-8")


def uv_gitignore() -> str:
    """The `.gitignore` body uv writes into a new Git repository.

    Captured in a temporary directory: the target itself never gets a `.git/`.

    Raises:
        AppException: `uv` is not on `PATH`, or exits non-zero.
    """
    with tempfile.TemporaryDirectory(prefix="kiln-uv-") as scratch:
        Process.execute(
            "uv-init[gitignore]",
            "uv",
            "init",
            "--name",
            "capture",
            "--vcs",
            "git",
            "--no-readme",
            "--bare",
            cwd=scratch,
        )
        return (Path(scratch) / gitignore.GITIGNORE).read_text(encoding="utf-8")


def _verify_uv() -> None:
    output = Process.execute("uv-version", "uv", "--version").stdout or ""
    words = output.split()
    found = words[1] if len(words) > 1 else output.strip()
    if found != UV_VERSION:
        raise AppException(
            "kiln scaffolds with uv {}, but `uv --version` reports {!r}; "
            "install uv {} to run `kiln new`",
            UV_VERSION,
            found,
            UV_VERSION,
        )


def reconcile_backend(raw: Path, workspace: Path, config: KilnConfig) -> None:
    """Copy *raw* into *workspace*, then reconcile its `pyproject.toml` files.

    *raw* is left untouched: the reconcile only ever rewrites the copy.
    """
    shutil.copytree(raw, workspace, symlinks=True, dirs_exist_ok=True)
    _reconcile_tree(workspace, config)


def _reconcile_tree(root: Path, config: KilnConfig) -> None:
    path = root / gitignore.GITIGNORE
    if path.is_file():
        body = path.read_text(encoding="utf-8")
        path.unlink()
        gitignore.append(root, body)
    _reconcile_pyprojects(root, config)


def _reconcile_pyprojects(root: Path, config: KilnConfig) -> None:
    workspace = config.archetype == "python-lib"
    web = config.archetype in {"python-web-api", "python-web-app"}
    required = archetypes.for_config(config).dependencies.required
    for relative in archetypes.pyproject_paths(config):
        path = root / relative
        is_root = path.parent == root
        is_member = not is_root
        is_workspace_root = (workspace or web) and is_root
        name = _member_name(config, path, root, web=web, is_member=is_member)
        extra_dev = _extra_dev(config, web=web, is_member=is_member)
        _reconcile(
            path,
            name=name,
            venv_path=os.path.relpath(root, path.parent) or ".",
            is_root=is_root,
            is_workspace_root=is_workspace_root,
            dependencies=()
            if is_workspace_root
            else tuple(archetypes.requirement(d) for d in required),
            mkdocs=config.docs_profile == "mkdocs",
            extra_dev=extra_dev,
        )


def _member_name(
    config: KilnConfig, path: Path, root: Path, *, web: bool, is_member: bool
) -> str:
    if web and is_member:
        return f"{config.name}-api"
    return path.parent.name if path.parent != root else config.name


def _extra_dev(config: KilnConfig, *, web: bool, is_member: bool) -> tuple[str, ...]:
    if web and is_member and config.backend == "fastapi":
        return ("uvicorn>=0.30",)
    return ()


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
    extra_dev: tuple[str, ...] = (),
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
    elif extra_dev:
        updates["dependency-groups"] = {
            "dev": [*_existing_list(path, "dependency-groups", "dev"), *extra_dev],
        }
    DocumentUtils.update(path, updates)
    _multiline_lists(path)


def _multiline_lists(path: Path) -> None:
    """Rewrite *path*'s non-empty dependency lists one entry per line."""
    document = DocumentUtils.read_document(path)
    arrays: list[Any] = [document.get("project", {}).get("dependencies")]
    arrays += list(document.get("dependency-groups", {}).values())
    for array in arrays:
        if array:
            array.multiline(True)
    DocumentUtils.write_document(path, document)


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
