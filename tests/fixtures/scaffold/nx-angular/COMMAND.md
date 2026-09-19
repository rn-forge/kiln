# How this fixture was captured

**Date:** 2026-09-17 · **`create-nx-workspace` version:** 23.2.1
(`NX_VERSION` in `modules/python/frontend.py`)

The story's planned one-liner —

```bash
pnpm dlx create-nx-workspace@23.2.1 workspace --preset=angular-monorepo --appName=web \
  --style=scss --bundler=esbuild --ssr=false --e2eTestRunner=none --unitTestRunner=vitest \
  --packageManager=pnpm --nxCloud=skip --ci=skip --interactive=false --skipGit
```

does not reproduce on this release. Two upstream changes broke it:

1. **`create-nx-workspace` v23 no longer honours `--preset=angular-monorepo`
   with `--appName`.** In an environment with `CLAUDECODE` (or `OPENCODE`) set,
   it silently reroutes any legacy preset to its new "AI Agent Mode" template
   flow ("Mapping legacy preset 'angular-monorepo' to template
   'nrwl/angular-template'"), which ignores `--appName=web` and instead
   generates unrelated demo apps (`shop`, `api`) plus a tree of `.claude/`,
   `.cursor/`, `.codex/` etc. agent-config directories. Unsetting
   `CLAUDECODE`/`OPENCODE`/`CLAUDE_CODE_ENTRYPOINT` for the capture restores
   the classic preset flow. This is an environment hazard specific to running
   the capture from an agent shell, not a kiln behaviour — `scaffold_frontend`
   itself must run with those variables unset (or absent) too, or a live
   `kiln new --frontend angular` run from inside an agent session would hit
   the same rerouting.
2. **Even with the classic flow, the `angular-monorepo` preset does not wire a
   test target when `--unitTestRunner=vitest` is passed.** Angular's vitest
   integration on this Nx/Angular pairing is exposed through the
   `@nx/angular:application` generator's `--unitTestRunner=vitest-angular`
   option (`@angular/build:unit-test` executor), not through the
   `create-nx-workspace` preset flag, which only sets an `nx.json` generator
   default that the preset's own app generation never reads.

**What actually ran**, in `/tmp` with `CLAUDECODE`/`OPENCODE`/
`CLAUDE_CODE_ENTRYPOINT` unset:

```bash
pnpm dlx create-nx-workspace@23.2.1 workspace --preset=apps --packageManager=pnpm \
  --nxCloud=skip --ci=skip --interactive=false --skipGit
cd workspace
pnpm add -D @nx/angular@23.2.1
pnpm nx g @nx/angular:application apps/web --name=web --style=scss \
  --bundler=esbuild --ssr=false --e2eTestRunner=none \
  --unitTestRunner=vitest-angular --standalone=true --routing=true \
  --linter=eslint --interactive=false
```

The application generator brought in `@nx/eslint` and wrote
`eslint.config.mjs` (root and `apps/web`) itself, since no linter existed yet
in the freshly-created `apps`-preset workspace.

**pnpm's build-script gate.** pnpm 12 blocks native build scripts
(`@parcel/watcher`, `esbuild`, `lmdb`, `msgpackr-extract`) behind an
allow-list (`ERR_PNPM_IGNORED_BUILDS`) unless approved. Both `pnpm install`
steps above fail on the first pass and leave `pnpm-workspace.yaml` stamped
with an `allowBuilds` stub naming exactly the blocked packages; setting each
to `true` and re-running `pnpm install` completes it. `scaffold_frontend`
must do the same before treating a non-zero exit as failure, or must let the
scaffolder command itself set `allowBuilds` (e.g. by pre-seeding the
temporary workspace's `pnpm-workspace.yaml`) so the recorded command succeeds
unattended, with stdin closed, on a first `kiln new` run.

**Verified working**, from the finished `workspace/`:

```bash
pnpm nx run-many -t lint test build --projects=web   # all three pass
```

`nx.json`'s generator defaults (`unitTestRunner: vitest`, `linter: eslint`)
were left as `create-nx-workspace --preset=apps` wrote them; they are cosmetic
now that `apps/web` itself has concrete targets.

**What was stripped before committing:** `node_modules/`, `.nx/`, `dist/`,
`.angular/`, `coverage/` — everything `reconcile_frontend`'s exclusion list
and a normal `.gitignore` already exclude from a real `kiln new` run.
`pnpm-lock.yaml` is kept, as the story requires.
