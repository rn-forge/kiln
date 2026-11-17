"""Reconciling a repository's `pyproject.toml` files toward what the checks expect.

The expected values here are the ones `check 8a` reads, so a reconciled file
passes it.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.lang.collections import DictUtils

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.names import module_name
from rn_forge.kiln.modules.core.versions import PYTHON_VERSION
from rn_forge.kiln.modules.python.checks.rn_forge_deps import distribution

__all__ = [
    "PYRIGHT_EXPECTED",
    "PYTEST_ADDOPTS",
    "REQUIRES_PYTHON",
    "TASK_TOOLS",
    "docs_group",
    "join_workspace",
    "reconcile_pyproject",
    "reconcile_pyprojects",
    "tidy",
]

REQUIRES_PYTHON = f">={PYTHON_VERSION}"
PYTEST_ADDOPTS = "-ra --import-mode=importlib"
PYRIGHT_EXPECTED = {"typeCheckingMode": "strict", "reportMissingTypeStubs": False}
RUFF_TEST_IGNORES = {"S101", "D", "ANN", "PLR2004"}

_DEV_GROUP = [
    "actionlint-py>=1.7",
    "google-yamlfmt>=0.21.0",
    "import-linter>=2.15",
    "pip-audit>=2.10",
    "pip-licenses>=5",
    "pyright>=1.1",
    "pytest>=9.1",
    "pytest-cov>=7.1",
    "ruff>=0.16",
    "taplo>=0.9",
    "zizmor>=1.31",
]
"""The dev tools every archetype's `pyproject.toml` names."""

_DOCS_GROUP = [
    "mdformat>=1.0.0",
    "mdformat-front-matters>=2.0.0",
    "mdformat-gfm>=0.4",
    "mdformat-mkdocs>=5.3.0",
]
"""The `docs` dependency group's shared entries, present for every docs profile."""
_DOCS_GROUP_MKDOCS = ["mkdocs-material>=9.6", "mkdocstrings[python]>=0.30"]
"""Added to the `docs` group only when `docs.profile == "mkdocs"`."""
_DOCS_GROUP_MKDOCS_LIB = [
    "mkdocs-material>=9.6",
    "mkdocs-monorepo-plugin>=1.1",
    "mkdocstrings[python]>=0.30",
]
"""`_DOCS_GROUP_MKDOCS` plus the monorepo plugin, for `python-lib`, which
includes each package's site."""

TASK_TOOLS = tuple(distribution(entry) for entry in _DEV_GROUP)
"""The tools `task lint`, `task typecheck` and `task test` invoke through `uv run`.

kiln is not listed: `{{.KILN}}` runs the pinned release with `uvx`, outside the
repository's lock."""


def docs_group(config: KilnConfig) -> list[str]:
    """The `docs` dependency group `kiln new` writes for *config*, entry by entry."""
    return _docs_group(mkdocs=config.docs_profile == "mkdocs", lib=config.is_workspace)


def _docs_group(*, mkdocs: bool, lib: bool) -> list[str]:
    mkdocs_group = _DOCS_GROUP_MKDOCS_LIB if lib else _DOCS_GROUP_MKDOCS
    return [*_DOCS_GROUP, *(mkdocs_group if mkdocs else [])]


@dataclass(frozen=True)
class _Target:
    """One `pyproject.toml` and what the reconcile writes into it."""

    path: Path
    name: str
    module: str
    role: Literal["root", "workspace-root", "member"]
    venv_path: str
    dependencies: tuple[str, ...]
    mkdocs: bool
    lib: bool
    extra_dev: tuple[str, ...]

    @property
    def is_root(self) -> bool:
        return self.role != "member"

    @property
    def is_workspace_root(self) -> bool:
        return self.role == "workspace-root"


def reconcile_pyprojects(root: Path, config: KilnConfig) -> None:
    """Reconcile every `pyproject.toml` the archetype expects under *root*."""
    for relative in archetypes.pyproject_paths(config):
        reconcile_pyproject(root, config, relative)


def reconcile_pyproject(root: Path, config: KilnConfig, relative: Path) -> None:
    """Reconcile the `pyproject.toml` at *relative* under *root*."""
    workspace = config.is_workspace
    web = config.is_web
    scripted = config.archetype in {"python-tool", "python-app"}
    path = root / relative
    is_root = path.parent == root
    is_member = not is_root
    is_workspace_root = (workspace or web or config.is_node_lib) and is_root
    name = _member_name(config, path, root, web=web, is_member=is_member)
    if workspace and is_member:
        module = config.module_for(path.parent.relative_to(root).as_posix())
    elif scripted and is_root:
        module = config.module
    else:
        module = module_name(name)
    role = "member" if is_member else "workspace-root" if is_workspace_root else "root"
    _reconcile(
        _Target(
            path=path,
            name=name,
            module=module,
            role=role,
            venv_path=os.path.relpath(root, path.parent) or ".",
            dependencies=() if is_workspace_root else _dependencies(config, name),
            mkdocs=config.docs_profile == "mkdocs",
            lib=workspace,
            extra_dev=_extra_dev(config, web=web, is_member=is_member),
        )
    )
    if web and is_member:
        document = DocumentUtils.read_document(path)
        document["project"].pop("scripts", None)
        DocumentUtils.write_document(path, document)
        tidy(path)
    if scripted and is_root:
        DocumentUtils.update(
            path,
            {"project": {"scripts": {config.name: f"{config.module}.main:app"}}},
        )
        tidy(path)


def _dependencies(config: KilnConfig, name: str) -> tuple[str, ...]:
    required = archetypes.for_config(config).dependencies.required
    return tuple(
        archetypes.requirement(d)
        for d in required
        if distribution(d) != distribution(name)
    )


def _member_name(
    config: KilnConfig, path: Path, root: Path, *, web: bool, is_member: bool
) -> str:
    if web and is_member and config.api_package is not None:
        return config.api_package
    return path.parent.name if path.parent != root else config.name


def _extra_dev(config: KilnConfig, *, web: bool, is_member: bool) -> tuple[str, ...]:
    if web and is_member and config.backend == "fastapi":
        return ("uvicorn>=0.30", "httpx>=0.28.1")
    return ()


def _reconcile(target: _Target) -> None:
    path = target.path
    updates: dict[str, object] = {
        "project": _project_table(target),
        "tool": _tool_table(target),
    }
    if target.is_root:
        coverage = ["coverage[toml]>=7.6"] if target.lib else []
        docs = _docs_group(mkdocs=target.mkdocs, lib=target.lib)
        updates["dependency-groups"] = {
            "dev": [
                *_existing_list(path, "dependency-groups", "dev"),
                *_DEV_GROUP,
                *coverage,
            ],
            "docs": [*_existing_list(path, "dependency-groups", "docs"), *docs],
        }
    elif target.extra_dev:
        updates["dependency-groups"] = {
            "dev": [
                *_existing_list(path, "dependency-groups", "dev"),
                *target.extra_dev,
            ],
        }
    DocumentUtils.update(path, updates)
    if "dependency-groups" in updates:
        document = DocumentUtils.read_document(path)
        for group in document["dependency-groups"].values():
            _sort_group(group)
        DocumentUtils.write_document(path, document)
    _multiline_lists(path)
    tidy(path)


def _project_table(target: _Target) -> dict[str, object]:
    project: dict[str, object] = {"requires-python": REQUIRES_PYTHON}
    lib_member = target.lib and not target.is_root
    if (target.is_root and not target.is_workspace_root) or lib_member:
        project["readme"] = "README.md"
    if target.dependencies:
        existing = _existing_list(target.path, "project", "dependencies")
        project["dependencies"] = [*existing, *target.dependencies]
    return project


def _tool_table(target: _Target) -> dict[str, object]:
    test_glob = "**/tests/*" if target.is_workspace_root else "tests/*"
    tool: dict[str, object] = {
        "pyright": {**PYRIGHT_EXPECTED, "venv": ".venv", "venvPath": target.venv_path},
        "pytest": {"ini_options": {"addopts": PYTEST_ADDOPTS}},
    }
    if not (target.lib and not target.is_root):
        tool["ruff"] = {
            "lint": {"per-file-ignores": {test_glob: sorted(RUFF_TEST_IGNORES)}}
        }
    if not target.is_workspace_root:
        tool["uv"] = {
            "build-backend": {
                "module-name": target.module,
                "source-exclude": ["**/.DS_Store"],
            }
        }
    if target.is_root and not target.lib:
        # pykit's workspace sources resolve per tag.
        uv = cast("dict[str, object]", tool.setdefault("uv", {}))
        uv["no-sources"] = True
    if target.lib and target.is_workspace_root:
        tool["pyright"] = {
            **cast("dict[str, object]", tool["pyright"]),
            "include": ["packages"],
        }
        tool["pytest"] = {
            "ini_options": {"addopts": PYTEST_ADDOPTS, "testpaths": ["packages"]}
        }
    return tool


def join_workspace(pyproject: Path, relative: str, name: str) -> None:
    """List *relative* in the root's workspace members, sources and `workspace` group."""
    members = [*_existing_list(pyproject, "tool", "uv", "workspace", "members")]
    group = _existing_list(pyproject, "dependency-groups", "workspace")
    dev: list[Any] = _existing_list(pyproject, "dependency-groups", "dev")
    include = {"include-group": "workspace"}
    DocumentUtils.update(
        pyproject,
        {
            "tool": {
                "uv": {
                    "workspace": {
                        "members": members
                        if relative in members
                        else [*members, relative]
                    },
                    "sources": {name: {"workspace": True}},
                }
            },
            "dependency-groups": {
                "workspace": [*group, name],
                "dev": dev if include in dev else [include, *dev],
            },
        },
    )
    _multiline_lists(pyproject)
    tidy(pyproject)


def _sort_group(array: Any) -> None:
    """Sort a round-trip TOML dependency *array* by normalized distribution name.

    Inline tables (`{ include-group = ... }`) follow the strings. A trailing
    comment stays on its entry, and a comment on lines of its own travels with
    the entry below it.
    """
    groups: list[Any] = array._value  # tomlkit has no public reorder
    commas = [g.comma for g in groups if g.comma is not None]
    carried: list[Any] = []
    strings: list[list[Any]] = []
    tables: list[list[Any]] = []
    for group in groups:
        carried.append(group)
        if isinstance(group.value, str):
            strings.append(carried)
        elif isinstance(group.value, Mapping):
            tables.append(carried)
        else:
            continue
        carried = []
    strings.sort(key=lambda chunk: distribution(str(chunk[-1].value)))
    ordered = [group for chunk in (*strings, *tables, carried) for group in chunk]
    for group in ordered[:-1]:
        if group.comma is None and group.value is not None and commas:
            group.comma = copy(commas[0])
    groups[:] = ordered
    entries: list[object] = [chunk[-1].value for chunk in (*strings, *tables)]
    list[object].__setitem__(array, slice(None), entries)  # not tomlkit's override
    array._reindex()


_TABLE_HEADER = re.compile(r"^\[\[?[A-Za-z0-9_.\"'-]+\]\]?$")


def tidy(path: Path) -> None:
    """Sort `[tool.pyright]`'s keys and put a blank line before every table."""
    document = DocumentUtils.read_document(path)
    pyright = document["tool"]["pyright"]
    for key in sorted(pyright):
        pyright[key] = pyright.pop(key)
    DocumentUtils.write_document(path, document)
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if lines and lines[-1] and _TABLE_HEADER.match(line):
            lines.append("")
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _multiline_lists(path: Path) -> None:
    """Rewrite *path*'s non-empty dependency and author lists one entry per line.

    Inline-table entries are respaced as `{ key = value }`, as taplo and uv write them.
    """
    document = DocumentUtils.read_document(path)
    DocumentUtils.multiline_arrays(
        document,
        "project.dependencies",
        "project.authors",
        *(
            f"dependency-groups.{name}"
            for name in DictUtils.as_mapping(document.get("dependency-groups"))
        ),
    )
    DocumentUtils.write_document(path, document)


def _existing_list(path: Path, *keys: str) -> list[str]:
    """The list already at *keys* in *path*'s document, or `[]`.

    `DocumentUtils.update` deep-merges tables but replaces lists wholesale, so
    callers that mean to extend a list read it first.
    """
    return DictUtils.get_strings(
        DocumentUtils.read(path, missing_ok=True), ".".join(keys)
    )
