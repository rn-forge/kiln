"""The Angular workspace: a pinned `create-nx-workspace` + `@nx/angular` run.

Runs the pinned Nx sequence into a scratch directory and hands back the
finished workspace, application included, for `scaffold.reconcile_node` to
fold into the repo. `add_ngkit` and `remove_scaffold_app` adjust that
workspace afterwards.
"""

from __future__ import annotations

import os
from pathlib import Path

from rn_forge.commons.fs.documents import DocumentUtils

from rn_forge.kiln.modules.core.process import run

__all__ = [
    "NGKIT_URL",
    "NX_VERSION",
    "OPENAPI_TS",
    "OPENAPI_TS_VERSION",
    "PRETTIER",
    "PRETTIER_VERSION",
    "SCAFFOLD_APP_DIR",
    "VITEST_COVERAGE",
    "WEB_PROJECT",
    "add_ngkit",
    "remove_scaffold_app",
    "scaffold_angular",
    "scaffold_env",
]

NX_VERSION = "24.0.4"
"""`create-nx-workspace`/`@nx/angular`'s pinned release (recorded 2026-11-06,
`tests/fixtures/scaffold/nx-angular/COMMAND.md`)."""

NGKIT_URL = (
    "https://github.com/rn-forge/ngkit/releases/download/v0.5.0/rn-forge-ng-0.5.0.tgz"
)
"""`@rn-forge/ng`'s release tarball (npm publishing is disabled)."""

WEB_PROJECT = "web"
"""The Nx project the scaffold creates, wherever its directory ends up."""

SCAFFOLD_APP_DIR = "apps/web"
"""Where the pinned command always creates the app; renamed to `web_dir` by
`reconcile_node` when a repo's `web_dir` differs."""

VITEST_COVERAGE = "@vitest/coverage-v8@^4.0.8"
"""The coverage provider the scaffold adds; its major matches `vitest`'s."""

PRETTIER_VERSION = "3.9.10"
"""The release `scaffold.format_node` runs with `pnpm dlx`."""

PRETTIER = f"prettier@~{PRETTIER_VERSION}"
"""The formatter the scaffold adds as a dev dependency (ngkit's range)."""

OPENAPI_TS_VERSION = "0.99.0"
"""The `@hey-api/openapi-ts` release that generates the Angular API client."""

OPENAPI_TS = f"@hey-api/openapi-ts@{OPENAPI_TS_VERSION}"
"""The generator the scaffold adds as a dev dependency, pinned exactly."""

_ALLOW_BUILDS = ("@parcel/watcher", "esbuild", "lmdb", "msgpackr-extract")
"""Native build scripts pnpm 12 blocks by default (`ERR_PNPM_IGNORED_BUILDS`);
`create-nx-workspace` stamps `pnpm-workspace.yaml` with an `allowBuilds` stub
naming exactly these the first time an install is blocked on them."""

_AGENT_ENV_VARS = ("CLAUDECODE", "OPENCODE", "CLAUDE_CODE_ENTRYPOINT")
"""Unset before scaffolding: their presence reroutes `create-nx-workspace` to
its AI-agent template flow, which ignores `--appName` (COMMAND.md)."""


def scaffold_nx_workspace(raw: Path) -> Path:
    """Run `create-nx-workspace` with the `apps` preset inside *raw*; return the workspace."""
    env = scaffold_env()
    # Keep Nx's native scanner from inheriting staging and checkout ignore rules.
    run("nx-git-boundary", "git", "init", "-q", cwd=raw, env=env)
    run(
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
        cwd=raw,
        env=env,
    )
    return raw / "workspace"


def scaffold_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in _AGENT_ENV_VARS}


def scaffold_angular(raw: Path) -> Path:
    """Run the Nx/Angular scaffold inside *raw*; return the workspace it made.

    The workspace holds the application at `SCAFFOLD_APP_DIR`, and has been
    installed.
    """
    env = scaffold_env()
    workspace = scaffold_nx_workspace(raw)
    run(
        "nx-angular-plugin",
        "pnpm",
        "add",
        "-D",
        f"@nx/angular@{NX_VERSION}",
        cwd=workspace,
        env=env,
    )
    # This step's own `pnpm install` is expected to fail here: it is the
    # first time pnpm sees the native builds below, and it stamps
    # `pnpm-workspace.yaml` with the `allowBuilds` stub this approves
    # before installing for real (COMMAND.md).
    run(
        "nx-angular-app",
        "pnpm",
        "nx",
        "g",
        "@nx/angular:application",
        SCAFFOLD_APP_DIR,
        f"--name={WEB_PROJECT}",
        "--style=scss",
        "--bundler=esbuild",
        "--ssr=false",
        "--e2eTestRunner=none",
        "--unitTestRunner=vitest-angular",
        "--standalone=true",
        "--routing=true",
        "--linter=eslint",
        "--interactive=false",
        cwd=workspace,
        env=env,
        check=False,
    )
    _approve_pnpm_builds(workspace / "pnpm-workspace.yaml")
    run(
        "coverage-v8",
        "pnpm",
        "add",
        "-D",
        VITEST_COVERAGE,
        cwd=workspace,
        env=env,
    )
    run("prettier", "pnpm", "add", "-D", PRETTIER, cwd=workspace, env=env)
    run("nx-install", "pnpm", "install", cwd=workspace, env=env)
    return workspace


def add_ngkit(workspace: Path) -> None:
    """Add the `@rn-forge/ng` package to *workspace*'s root `package.json`."""
    run(
        "ngkit-core",
        "pnpm",
        "add",
        NGKIT_URL,
        cwd=workspace,
        env=scaffold_env(),
    )


def remove_scaffold_app(workspace: Path) -> None:
    """Remove the scaffolded application from *workspace*, keeping its root files."""
    run(
        "nx-remove-app",
        "pnpm",
        "nx",
        "g",
        "@nx/workspace:remove",
        WEB_PROJECT,
        "--forceRemove",
        "--interactive=false",
        cwd=workspace,
        env=scaffold_env(),
    )


def _approve_pnpm_builds(path: Path) -> None:
    if not path.is_file():
        return
    DocumentUtils.update(path, {"allowBuilds": dict.fromkeys(_ALLOW_BUILDS, True)})
