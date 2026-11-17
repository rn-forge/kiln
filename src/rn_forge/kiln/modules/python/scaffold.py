"""The scaffold steps `kiln new` and `kiln generate package` run.

Runs once, before the first `apply`: `uv init`, then a reconcile of the
`pyproject.toml` sections the checks verify.
"""

from __future__ import annotations

import dataclasses
import re
import shutil
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import gitignore
from rn_forge.kiln.modules.python.config import MODULE_PATTERN
from rn_forge.kiln.modules.python.pyproject import (
    PYRIGHT_EXPECTED,
    PYTEST_ADDOPTS,
    REQUIRES_PYTHON,
    TASK_TOOLS,
    docs_group,
    join_workspace,
    reconcile_pyproject,
    reconcile_pyprojects,
    tidy,
)
from rn_forge.kiln.modules.python.uv_init import (
    SAMPLE_TEST,
    sample_test,
    uv_gitignore,
    uv_init,
    write_sample_test,
)

__all__ = [
    "PYRIGHT_EXPECTED",
    "PYTEST_ADDOPTS",
    "REQUIRES_PYTHON",
    "SAMPLE_TEST",
    "TASK_TOOLS",
    "add_package",
    "declared_modules",
    "docs_group",
    "package_preflight",
    "reconcile_backend",
    "sample_test",
    "scaffold_backend",
    "uv_gitignore",
    "without_members",
]


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
    workspace = config.is_workspace
    web = config.is_web
    members = (workspace or web) and not config.is_node_lib
    if config.is_node_lib or members:
        uv_init(raw, name=config.name, bare=True)
    if members:
        for package in config.packages:
            member = raw / package
            member.mkdir(parents=True, exist_ok=True)
            member_name = config.api_package or Path(package).name
            module = config.module_for(package) if workspace else None
            uv_init(
                member,
                name=member_name,
                bare=False,
                member=True,
                lib=workspace,
                module=module,
            )
            write_sample_test(member, member_name, module)
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
    elif not config.is_node_lib:
        uv_init(raw, name=config.name, bare=False, module=config.module)
        write_sample_test(raw, config.name, config.module)
    (raw / gitignore.GITIGNORE).write_text(uv_gitignore(), encoding="utf-8")


_PACKAGE_NAME = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def package_preflight(
    root: Path, config: KilnConfig, name: str, module: str | None = None
) -> None:
    """Refuse every case `generate package` cannot write.

    Raises:
        AppException: The archetype is not `python-lib`
            (`generate.unsupported-archetype`), *name* is not a kebab-case
            distribution name (`generate.invalid-name`), *module* is not a
            dotted import module (`generate.invalid-module`), or the package
            already exists (`generate.package-exists`).
    """
    if config.archetype != "python-lib":
        raise AppException(
            "generate.unsupported-archetype: kiln generate package supports "
            "python-lib only, not {}",
            config.archetype,
        )
    if not _PACKAGE_NAME.match(name):
        raise AppException(
            "generate.invalid-name: {!r} is not a kebab-case distribution name", name
        )
    if module is not None and not MODULE_PATTERN.match(module):
        raise AppException(
            "generate.invalid-module: {!r} is not a dotted import module name",
            module,
        )
    relative = f"packages/{name}"
    if relative in config.packages or (root / relative).exists():
        raise AppException("generate.package-exists: {} already exists", relative)


def add_package(
    root: Path, config: KilnConfig, name: str, owner: str, repo: str
) -> None:
    """Add the `python-lib` member `packages/<name>` to the repository at *root*.

    Runs `uv init` and the reconcile for the member alone, then lists it in the
    root's workspace members, sources and `workspace` dependency group, and
    writes its `[project.urls]` from *owner* and *repo*.

    Args:
        root: The repository root.
        config: The config, already listing the package.
        name: The package's distribution name.
        owner: The GitHub owner, the config's `repository.owner`.
        repo: The GitHub repository, the config's name.

    Raises:
        AppException: `uv` is not on `PATH`, or exits non-zero.
    """
    relative = f"packages/{name}"
    member = root / relative
    member.mkdir(parents=True, exist_ok=True)
    module = config.module_for(relative)
    uv_init(member, name=name, bare=False, member=True, lib=True, module=module)
    reconcile_pyproject(root, config, Path(relative) / "pyproject.toml")
    join_workspace(root / "pyproject.toml", relative, name)
    remote = f"https://github.com/{owner}/{repo}"
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
    tidy(member / "pyproject.toml")


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
    reconcile_pyprojects(root, config)


def declared_modules(config: KilnConfig) -> dict[str, str]:
    """A `python-lib` config's `modules` table; empty for any other archetype."""
    section = config.archetype_section
    lib = section.python_lib if section is not None else None
    return dict(lib.modules) if config.is_workspace and lib else {}


def without_members(config: KilnConfig) -> KilnConfig:
    """*config* with a `python-lib`'s `packages` and `modules` emptied."""
    section = config.archetype_section
    if section is None or section.python_lib is None:
        return config
    lib = section.python_lib.model_copy(update={"packages": [], "modules": {}})
    bare = config.document.model_copy(
        update={"archetype": section.model_copy(update={"python_lib": lib})}
    )
    return dataclasses.replace(config, document=bare)
