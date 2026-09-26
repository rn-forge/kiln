"""S5.2.1 — the frontend scaffolder, and reconciling its output into the repo.

`scaffold_frontend` is the one part of kiln that runs someone else's
generator: it dispatches on `config.frontend` to that frontend's scaffolder
(`angular.py`), which builds a workspace in a scratch directory, and
`reconcile_frontend` folds every top-level entry it
wrote into the repo at `config.web_dir`. Every file the frontend scaffolder
writes is repo-owned; kiln templates nothing under `web_dir` (F5.1's design).

`--frontend` values other than `angular` normally never reach here: `kiln new`
refuses them as untested before scaffolding starts. One that does is rejected
before any subprocess runs.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.frontend.angular import SCAFFOLD_APP_DIR, scaffold_angular

__all__ = ["reconcile_frontend", "scaffold_frontend"]

_SCAFFOLDERS: dict[str, Callable[[Path], Path]] = {"angular": scaffold_angular}
"""Each implemented frontend: it scaffolds into a scratch directory and returns
the finished workspace."""

_EXCLUDED_TOP_LEVEL = {".git", "node_modules", ".nx"}

_GITIGNORE = ".gitignore"

_DROPPED = {".editorconfig"}
"""Scaffolder-written root files kiln's own `core` module unconditionally
renders for every archetype, with no earlier scaffold step of its own to
reconcile against (unlike `pyproject.toml` or `README.md`, whose scaffolded
content already matches what `apply` renders). Moving the scaffolder's copy
into root would only have `apply` reject it as an unapproved conflict once it
tries to write its own; dropping it here is a no-op, since `apply` writes the
real one right after."""


def scaffold_frontend(root: Path, config: KilnConfig) -> None:
    """Scaffold the selected frontend into *root* at `config.web_dir`.

    Returns at once unless `config.archetype == "python-web-app"`.

    Raises:
        AppException: the frontend has no scaffolder, a scaffold command is
            not on `PATH`, `pnpm install` fails after builds are approved, or
            the reconcile finds a conflicting root file.
    """
    if config.archetype != "python-web-app":
        return

    scaffolder = _SCAFFOLDERS.get(config.frontend or "")
    if scaffolder is None:
        raise AppException(
            "no scaffolder for frontend {!r}; kiln implements {}",
            config.frontend,
            ", ".join(sorted(_SCAFFOLDERS)),
        )

    with tempfile.TemporaryDirectory() as tmp:
        reconcile_frontend(root, scaffolder(Path(tmp)), config)


def reconcile_frontend(root: Path, workspace: Path, config: KilnConfig) -> None:
    """Fold *workspace* (a finished frontend scaffold) into *root*.

    Every top-level entry of *workspace* moves into *root*, except `.git`,
    `node_modules` and `.nx`. The scaffolder's `.gitignore` body is appended
    to `root/.gitignore` (created if absent) rather than moved, since apply's
    own `.gitignore` block still has to land in the same file afterwards. If
    the scaffolder's app directory (`apps/web`) differs from `config.web_dir`,
    it is renamed and every reference to its old path in `project.json`'s
    `sourceRoot`/`root` and in `tsconfig.base.json`'s `paths` is rewritten to
    the new one — nothing else.

    A shared top-level directory (`apps/`, holding the API member too) merges
    rather than conflicts: only an actual file colliding with an existing file
    at the same path is a conflict.

    Raises:
        AppException: a file *workspace* would move already exists at that
            same path under *root*, naming it.
    """
    web_dir = config.web_dir or SCAFFOLD_APP_DIR

    entries = [
        p
        for p in workspace.iterdir()
        if p.name not in _EXCLUDED_TOP_LEVEL and p.name not in _DROPPED
    ]
    conflicts = [
        conflict
        for entry in entries
        if entry.name != _GITIGNORE
        for conflict in _conflicts(entry, root / entry.name)
    ]
    if conflicts:
        raise AppException(
            "frontend scaffold conflicts with existing root file(s): {}",
            ", ".join(sorted(conflicts)),
        )

    for entry in entries:
        if entry.name == _GITIGNORE:
            _append_gitignore(root, entry)
            continue
        _move_or_merge(entry, root / entry.name)

    if web_dir != SCAFFOLD_APP_DIR:
        shutil.move(str(root / SCAFFOLD_APP_DIR), str(root / web_dir))
        _rewrite_app_dir(root, web_dir)


def _conflicts(src: Path, dst: Path) -> list[str]:
    if not dst.exists():
        return []
    if src.is_dir() and dst.is_dir():
        return [
            c for child in src.iterdir() for c in _conflicts(child, dst / child.name)
        ]
    return [str(dst)]


def _move_or_merge(src: Path, dst: Path) -> None:
    if not dst.exists():
        shutil.move(str(src), str(dst))
        return
    for child in src.iterdir():
        _move_or_merge(child, dst / child.name)
    src.rmdir()


def _append_gitignore(root: Path, scaffolded: Path) -> None:
    body = scaffolded.read_text(encoding="utf-8")
    target = root / _GITIGNORE
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    separator = "" if not existing or existing.endswith("\n") else "\n"
    target.write_text(existing + separator + body, encoding="utf-8")


def _rewrite_app_dir(root: Path, web_dir: str) -> None:
    project_path = root / web_dir / "project.json"
    project = DocumentUtils.read(project_path)
    project["sourceRoot"] = f"{web_dir}/src"
    project["root"] = web_dir
    DocumentUtils.write(project_path, project)

    tsconfig_path = root / "tsconfig.base.json"
    if not tsconfig_path.is_file():
        return
    tsconfig = DocumentUtils.read(tsconfig_path)
    paths = tsconfig.get("compilerOptions", {}).get("paths", {})
    old_prefix = f"{SCAFFOLD_APP_DIR}/"
    new_prefix = f"{web_dir}/"
    changed = False
    for key, values in paths.items():
        paths[key] = [
            new_prefix + v[len(old_prefix) :] if v.startswith(old_prefix) else v
            for v in values
        ]
        changed = changed or paths[key] != values
    if changed:
        DocumentUtils.write(tsconfig_path, tsconfig)
