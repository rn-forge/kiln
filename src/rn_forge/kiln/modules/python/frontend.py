"""S5.2.1 — the frontend scaffolder, and reconciling its output into the repo.

`scaffold_frontend` is the one part of kiln that runs someone else's
generator: a pinned `create-nx-workspace` + `@nx/angular:application` sequence
into a scratch directory, `reconcile_frontend` folds every top-level entry it
wrote into the repo at `config.web_dir`. Every file the frontend scaffolder
writes is repo-owned; kiln templates nothing under `web_dir` (F5.1's design).

`--frontend` values other than `angular` never reach here: `kiln new` refuses
them as untested before scaffolding starts.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.runtime.subprocess import Process

from rn_forge.kiln.config import KilnConfig

__all__ = ["reconcile_frontend", "scaffold_frontend"]

NX_VERSION = "23.2.1"
"""`create-nx-workspace`/`@nx/angular`'s pinned release (recorded 2026-09-17,
`tests/fixtures/scaffold/nx-angular/COMMAND.md`)."""

_SCAFFOLD_APP_DIR = "apps/web"
"""Where the pinned command always creates the app; renamed to `web_dir` by
`reconcile_frontend` when a repo's `web_dir` differs."""

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

_ALLOW_BUILDS = ("@parcel/watcher", "esbuild", "lmdb", "msgpackr-extract")
"""Native build scripts pnpm 12 blocks by default (`ERR_PNPM_IGNORED_BUILDS`);
`create-nx-workspace` stamps `pnpm-workspace.yaml` with an `allowBuilds` stub
naming exactly these the first time an install is blocked on them."""

_AGENT_ENV_VARS = ("CLAUDECODE", "OPENCODE", "CLAUDE_CODE_ENTRYPOINT")
"""Unset before scaffolding: their presence reroutes `create-nx-workspace` to
its AI-agent template flow, which ignores `--appName` (COMMAND.md)."""


def scaffold_frontend(root: Path, config: KilnConfig) -> None:
    """Scaffold the Nx/Angular frontend into *root* at `config.web_dir`.

    Returns at once unless `config.archetype == "python-web-app"`.

    Raises:
        AppException: a scaffold command is not on `PATH`, `pnpm install`
            fails after builds are approved, or the reconcile finds a
            conflicting root file.
    """
    if config.archetype != "python-web-app":
        return

    env = {k: v for k, v in os.environ.items() if k not in _AGENT_ENV_VARS}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        Process.execute(
            "nx-workspace",
            "pnpm",
            "dlx",
            f"create-nx-workspace@{NX_VERSION}",
            "workspace",
            "--preset=apps",
            "--packageManager=pnpm",
            "--nxCloud=skip",
            "--ci=skip",
            "--interactive=false",
            "--skipGit",
            cwd=str(tmp_path),
            env=env,
        )
        workspace = tmp_path / "workspace"
        Process.execute(
            "nx-angular-plugin",
            "pnpm",
            "add",
            "-D",
            f"@nx/angular@{NX_VERSION}",
            cwd=str(workspace),
            env=env,
        )
        # This step's own `pnpm install` is expected to fail here: it is the
        # first time pnpm sees the native builds below, and it stamps
        # `pnpm-workspace.yaml` with the `allowBuilds` stub this approves
        # before installing for real (COMMAND.md).
        Process.execute(
            "nx-angular-app",
            "pnpm",
            "nx",
            "g",
            "@nx/angular:application",
            _SCAFFOLD_APP_DIR,
            "--name=web",
            "--style=scss",
            "--bundler=esbuild",
            "--ssr=false",
            "--e2eTestRunner=none",
            "--unitTestRunner=vitest-angular",
            "--standalone=true",
            "--routing=true",
            "--linter=eslint",
            "--interactive=false",
            cwd=str(workspace),
            env=env,
            fail_on_error=False,
        )
        _approve_pnpm_builds(workspace / "pnpm-workspace.yaml")
        Process.execute("nx-install", "pnpm", "install", cwd=str(workspace), env=env)

        reconcile_frontend(root, workspace, config)


def _approve_pnpm_builds(path: Path) -> None:
    if not path.is_file():
        return
    DocumentUtils.update(path, {"allowBuilds": dict.fromkeys(_ALLOW_BUILDS, True)})


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
    web_dir = config.web_dir or _SCAFFOLD_APP_DIR

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

    if web_dir != _SCAFFOLD_APP_DIR:
        shutil.move(str(root / _SCAFFOLD_APP_DIR), str(root / web_dir))
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
    old_prefix = f"{_SCAFFOLD_APP_DIR}/"
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
