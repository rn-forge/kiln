"""Scaffolding: `uv init`, then reconciling toward what check 8a expects.

Runs once, from `kiln new`, before the first `apply` (kiln ADR-0005). This is
the only subprocess kiln starts — `apply` never shells out — and it never
templates `uv init`'s own output (D16): it only fixes the `pyproject.toml`
sections check 8a verifies, using the same expected values that check reads.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from collections.abc import Mapping
from copy import copy
from functools import cache
from pathlib import Path
from typing import Any, cast

from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.lang.collections import DictUtils
from rn_forge.commons.runtime.subprocess import Process

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import gitignore
from rn_forge.kiln.modules.core.versions import PYTHON_VERSION
from rn_forge.kiln.modules.python.checks.rn_forge_deps import distribution

__all__ = [
    "SAMPLE_TEST",
    "TASK_TOOLS",
    "add_package",
    "docs_group",
    "reconcile_backend",
    "sample_test",
    "scaffold",
    "scaffold_backend",
    "uv_gitignore",
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

TASK_TOOLS = (
    "actionlint-py",
    "google-yamlfmt",
    "import-linter",
    "pip-audit",
    "pip-licenses",
    "pyright",
    "pytest",
    "pytest-cov",
    "ruff",
    "taplo",
    "zizmor",
)
"""The tools `task lint`, `task typecheck` and `task test` invoke through `uv run`.

kiln is not listed: `{{.KILN}}` runs the pinned release with `uvx`, outside the
repository's lock."""


def docs_group(config: KilnConfig) -> list[str]:
    """The `docs` dependency group `kiln new` writes for *config*, entry by entry."""
    return _docs_group(
        mkdocs=config.docs_profile == "mkdocs", lib=config.archetype == "python-lib"
    )


def _docs_group(*, mkdocs: bool, lib: bool) -> list[str]:
    mkdocs_group = _DOCS_GROUP_MKDOCS_LIB if lib else _DOCS_GROUP_MKDOCS
    return [*_DOCS_GROUP, *(mkdocs_group if mkdocs else [])]


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

    `node-lib` gets the bare root alone. For `python-lib` and the web
    archetypes, also runs `uv init` for each workspace member in
    `config.packages` and wires the workspace table at the root. `uv init`
    itself refuses a directory that already holds a `pyproject.toml`, so *raw*
    must be empty. Writes uv's own ignore body to `raw/.gitignore`, once, from
    `uv_gitignore`, and `SAMPLE_TEST` into each package `uv init` creates.

    Raises:
        AppException: `uv` is not on `PATH`, or exits non-zero.
    """
    workspace = config.archetype == "python-lib"
    web = config.archetype in {"python-web-api", "python-web-app"}
    if config.archetype == "node-lib":
        _uv_init(raw, name=config.name, bare=True)
    elif workspace or web:
        _uv_init(raw, name=config.name, bare=True)
        for package in config.packages:
            member = raw / package
            member.mkdir(parents=True, exist_ok=True)
            member_name = f"{config.name}-api" if web else Path(package).name
            module = config.module_for(package) if workspace else None
            _uv_init(
                member,
                name=member_name,
                bare=False,
                member=True,
                lib=workspace,
                module=module,
            )
            _write_sample_test(member, member_name, module)
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
        _uv_init(raw, name=config.name, bare=False, module=config.module)
        _write_sample_test(raw, config.name, config.module)
    (raw / gitignore.GITIGNORE).write_text(uv_gitignore(), encoding="utf-8")


def add_package(root: Path, config: KilnConfig, name: str, remote: str) -> None:
    """Add the `python-lib` member `packages/<name>` to the repository at *root*.

    Runs `uv init` and the reconcile for the member alone, then lists it in the
    root's workspace members, sources and `workspace` dependency group, and
    writes its `[project.urls]` from *remote*.

    Args:
        root: The repository root.
        config: The config, already listing the package.
        name: The package's distribution name.
        remote: The GitHub repository, as `https://github.com/<owner>/<repo>`,
            built from the config's `repository.owner` and name.

    Raises:
        AppException: `uv` is not on `PATH`, or exits non-zero.
    """
    relative = f"packages/{name}"
    member = root / relative
    member.mkdir(parents=True, exist_ok=True)
    module = config.module_for(relative)
    _uv_init(member, name=name, bare=False, member=True, lib=True, module=module)
    _reconcile_pyproject(root, config, Path(relative) / "pyproject.toml")
    _join_workspace(root / "pyproject.toml", relative, name)
    slug = remote.removeprefix("https://github.com/")
    owner, repo = slug.split("/")
    DocumentUtils.update(
        member / "pyproject.toml",
        {
            "project": {
                "urls": {
                    "Documentation": f"https://{owner}.github.io/{repo}/packages/{name}/latest/",
                    "Source": remote,
                    "Changelog": f"{remote}/blob/main/{relative}/CHANGELOG.md",
                    "Issues": f"{remote}/issues",
                }
            }
        },
    )
    _tidy(member / "pyproject.toml")


def _join_workspace(pyproject: Path, relative: str, name: str) -> None:
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
    _tidy(pyproject)


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


SAMPLE_TEST = Path("tests") / "test_package.py"
"""The sample test `scaffold_backend` writes into each package `uv init` creates."""


def sample_test(name: str, module: str | None = None) -> str:
    """The body of `SAMPLE_TEST` for the package *name* (dashes allowed).

    *module* is the dotted import module; it defaults to *name* with dashes
    as underscores.

    A new package has no tests, and pytest exits 5 on an empty suite, so
    without this a fresh repository's `task validate` fails.
    """
    module = module or name.replace("-", "_")
    return (
        f"import {module}\n\n\n"
        "def test_package_imports():\n"
        f"    assert {module}.__spec__ is not None\n"
    )


def _write_sample_test(package: Path, name: str, module: str | None = None) -> None:
    path = package / SAMPLE_TEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sample_test(name, module), encoding="utf-8")


@cache
def uv_gitignore() -> str:
    """The `.gitignore` body uv writes into a new Git repository.

    Captured in a temporary directory, once per process: the target itself
    never gets a `.git/`.

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
        gitignore.append(root, body, "uv")
    _reconcile_pyprojects(root, config)


def _reconcile_pyprojects(root: Path, config: KilnConfig) -> None:
    for relative in archetypes.pyproject_paths(config):
        _reconcile_pyproject(root, config, relative)


def _reconcile_pyproject(root: Path, config: KilnConfig, relative: Path) -> None:
    workspace = config.archetype == "python-lib"
    web = config.archetype in {"python-web-api", "python-web-app"}
    required = archetypes.for_config(config).dependencies.required
    path = root / relative
    is_root = path.parent == root
    is_member = not is_root
    is_workspace_root = (workspace or web or config.archetype == "node-lib") and is_root
    name = _member_name(config, path, root, web=web, is_member=is_member)
    if workspace and is_member:
        module = config.module_for(path.parent.relative_to(root).as_posix())
    elif config.archetype in {"python-tool", "python-app"} and is_root:
        module = config.module
    else:
        module = name.replace("-", "_")
    extra_dev = _extra_dev(config, web=web, is_member=is_member)
    _reconcile(
        path,
        name=name,
        module=module,
        venv_path=os.path.relpath(root, path.parent) or ".",
        is_root=is_root,
        is_workspace_root=is_workspace_root,
        dependencies=()
        if is_workspace_root
        else tuple(
            archetypes.requirement(d)
            for d in required
            if distribution(d) != distribution(name)
        ),
        mkdocs=config.docs_profile == "mkdocs",
        lib=workspace,
        extra_dev=extra_dev,
    )
    if config.archetype in {"python-tool", "python-app"} and is_root:
        DocumentUtils.update(
            path,
            {"project": {"scripts": {config.name: f"{config.module}.main:app"}}},
        )
        _tidy(path)


def _member_name(
    config: KilnConfig, path: Path, root: Path, *, web: bool, is_member: bool
) -> str:
    if web and is_member:
        return f"{config.name}-api"
    return path.parent.name if path.parent != root else config.name


def _extra_dev(config: KilnConfig, *, web: bool, is_member: bool) -> tuple[str, ...]:
    if web and is_member and config.backend == "fastapi":
        return ("uvicorn>=0.30", "httpx>=0.28.1")
    return ()


def _uv_init(
    target: Path,
    *,
    name: str,
    bare: bool,
    member: bool = False,
    lib: bool = False,
    module: str | None = None,
) -> None:
    args = ["uv", "init", "--name", name, "--vcs", "none", "--no-readme"]
    if bare:
        args += ["--bare", "--pin-python"]
    else:
        args += ["--lib" if lib else "--package", "--build-backend", "uv"]
    # A root must not join a uv project above `.staging/`; a member joins its
    # root, and its Python pin comes from the root's `.python-version`.
    args += ["--no-pin-python"] if member else ["--no-workspace"]
    Process.execute(f"uv-init[{name}]", *args, cwd=str(target))
    if not bare:
        derived = target / "src" / name.replace("-", "_")
        package_dir = target / "src" / (module or derived.name).replace(".", "/")
        if package_dir != derived:
            package_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(derived, package_dir)
        if not lib:
            # `uv init --package` writes a `main()` stub the starter's
            # `main:app` console script never uses.
            (package_dir / "__init__.py").write_text("", encoding="utf-8")
        typed = package_dir / "py.typed"
        if not typed.exists():
            typed.touch()


def _reconcile(
    path: Path,
    *,
    name: str,
    module: str,
    venv_path: str,
    is_root: bool,
    is_workspace_root: bool,
    dependencies: tuple[str, ...],
    mkdocs: bool,
    lib: bool = False,
    extra_dev: tuple[str, ...] = (),
) -> None:
    test_glob = "**/tests/*" if is_workspace_root else "tests/*"
    tool: dict[str, object] = {
        "pyright": {**PYRIGHT_EXPECTED, "venv": ".venv", "venvPath": venv_path},
        "pytest": {"ini_options": {"addopts": PYTEST_ADDOPTS}},
    }
    if not (lib and not is_root):
        tool["ruff"] = {
            "lint": {"per-file-ignores": {test_glob: sorted(RUFF_TEST_IGNORES)}}
        }
    if not is_workspace_root:
        tool["uv"] = {
            "build-backend": {
                "module-name": module,
                "source-exclude": ["**/.DS_Store"],
            }
        }
    if is_root and not lib:
        # pykit's workspace sources resolve per tag; see F7.1 S7.1.2.
        uv = cast("dict[str, object]", tool.setdefault("uv", {}))
        uv["no-sources"] = True
    project: dict[str, object] = {"requires-python": REQUIRES_PYTHON}
    if (is_root and not is_workspace_root) or (lib and not is_root):
        project["readme"] = "README.md"
    if dependencies:
        existing = _existing_list(path, "project", "dependencies")
        project["dependencies"] = [*existing, *dependencies]
    if lib and is_workspace_root:
        tool["pyright"] = {
            **cast("dict[str, object]", tool["pyright"]),
            "include": ["packages"],
        }
        tool["pytest"] = {
            "ini_options": {"addopts": PYTEST_ADDOPTS, "testpaths": ["packages"]}
        }
    updates: dict[str, object] = {"project": project, "tool": tool}
    if is_root:
        coverage = ["coverage[toml]>=7.6"] if lib else []
        dev = [*_DEV_GROUP, *coverage]
        docs = _docs_group(mkdocs=mkdocs, lib=lib)
        updates["dependency-groups"] = {
            "dev": [*_existing_list(path, "dependency-groups", "dev"), *dev],
            "docs": [*_existing_list(path, "dependency-groups", "docs"), *docs],
        }
    elif extra_dev:
        updates["dependency-groups"] = {
            "dev": [*_existing_list(path, "dependency-groups", "dev"), *extra_dev],
        }
    DocumentUtils.update(path, updates)
    if "dependency-groups" in updates:
        document = DocumentUtils.read_document(path)
        for group in document["dependency-groups"].values():
            _sort_group(group)
        DocumentUtils.write_document(path, document)
    _multiline_lists(path)
    _tidy(path)


_TABLE_HEADER = re.compile(r"^\[\[?[A-Za-z0-9_.\"'-]+\]\]?$")


def _tidy(path: Path) -> None:
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
