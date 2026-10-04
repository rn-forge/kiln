"""The Angular frontend: a pinned `create-nx-workspace` + `@nx/angular` run.

Runs the pinned Nx sequence into a scratch directory and hands back the
finished workspace for `scaffold.reconcile_frontend` to fold into the repo.
"""

from __future__ import annotations

import os
from pathlib import Path

from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.runtime.subprocess import Process

__all__ = ["NX_VERSION", "SCAFFOLD_APP_DIR", "scaffold_angular"]

NX_VERSION = "23.2.1"
"""`create-nx-workspace`/`@nx/angular`'s pinned release (recorded 2026-09-17,
`tests/fixtures/scaffold/nx-angular/COMMAND.md`)."""

SCAFFOLD_APP_DIR = "apps/web"
"""Where the pinned command always creates the app; renamed to `web_dir` by
`reconcile_frontend` when a repo's `web_dir` differs."""

_ALLOW_BUILDS = ("@parcel/watcher", "esbuild", "lmdb", "msgpackr-extract")
"""Native build scripts pnpm 12 blocks by default (`ERR_PNPM_IGNORED_BUILDS`);
`create-nx-workspace` stamps `pnpm-workspace.yaml` with an `allowBuilds` stub
naming exactly these the first time an install is blocked on them."""

_AGENT_ENV_VARS = ("CLAUDECODE", "OPENCODE", "CLAUDE_CODE_ENTRYPOINT")
"""Unset before scaffolding: their presence reroutes `create-nx-workspace` to
its AI-agent template flow, which ignores `--appName` (COMMAND.md)."""


def scaffold_angular(raw: Path) -> Path:
    """Run the Nx/Angular scaffold inside *raw*; return the workspace it made."""
    env = {k: v for k, v in os.environ.items() if k not in _AGENT_ENV_VARS}
    # Keep Nx's native scanner from inheriting staging and checkout ignore rules.
    Process.execute("nx-git-boundary", "git", "init", "-q", cwd=str(raw), env=env)
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
        cwd=str(raw),
        env=env,
    )
    workspace = raw / "workspace"
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
        SCAFFOLD_APP_DIR,
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
    return workspace


def _approve_pnpm_builds(path: Path) -> None:
    if not path.is_file():
        return
    DocumentUtils.update(path, {"allowBuilds": dict.fromkeys(_ALLOW_BUILDS, True)})
