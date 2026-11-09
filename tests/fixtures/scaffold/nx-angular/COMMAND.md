# How this fixture was captured

**Date:** 2026-11-06 (first captured 2026-09-17 at 23.2.1) · **`create-nx-workspace` version:** 24.0.4
(`NX_VERSION` in `modules/node/angular.py`)

The story's planned one-liner —

```bash
pnpm dlx create-nx-workspace@24.0.4 workspace --preset=angular-monorepo --appName=web \
  --style=scss --bundler=esbuild --ssr=false --e2eTestRunner=none --unitTestRunner=vitest \
  --packageManager=pnpm --nxCloud=skip --ci=skip --interactive=false --skipGit
```

does not reproduce on this release (it did not on 23.2.1, and 24.0.4 is no different). Two upstream changes broke it:

1. **`create-nx-workspace` v23 no longer honours `--preset=angular-monorepo`
   with `--appName`.** In an environment with `CLAUDECODE` (or `OPENCODE`) set,
   it silently reroutes any legacy preset to its new "AI Agent Mode" template
   flow ("Mapping legacy preset 'angular-monorepo' to template
   'nrwl/angular-template'"), which ignores `--appName=web` and instead
   generates unrelated demo apps (`shop`, `api`) plus a tree of `.claude/`,
   `.cursor/`, `.codex/` etc. agent-config directories. Unsetting
   `CLAUDECODE`/`OPENCODE`/`CLAUDE_CODE_ENTRYPOINT` for the capture restores
   the classic preset flow. This is an environment hazard specific to running
   the capture from an agent shell, not a kiln behaviour — `scaffold_node`
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
pnpm dlx create-nx-workspace@24.0.4 workspace --preset=apps --packageManager=pnpm \
  --nxCloud=skip --ci=skip --interactive=false --skipGit
cd workspace
pnpm add -D @nx/angular@24.0.4
pnpm nx g @nx/angular:application apps/web --name=web --style=scss \
  --bundler=esbuild --ssr=false --e2eTestRunner=none \
  --unitTestRunner=vitest-angular --standalone=true --routing=true \
  --linter=eslint --interactive=false
```

The application generator brought in `@nx/eslint` and wrote
`eslint.config.mjs` (root and `apps/web`) itself, since no linter existed yet
in the freshly-created `apps`-preset workspace.

The scaffold then adds Prettier (2026-11-09, S16.7.3) with `pnpm add -D prettier@~3.9.10`.

**`node-lib`.** A `node-lib` runs the same commands, then removes the
application, because only the application generator writes the root files
(`eslint.config.mjs`, `tsconfig.base.json`):

```bash
pnpm nx g @nx/workspace:remove web --forceRemove --interactive=false
```

**Nx 24 changes (2026-11-06).** The commands below ran unchanged at 24.0.4,
and `@nx/workspace:remove` still removes the app. What differs in the output:
`@nx/angular` 24.0.4 writes `angularVersion = '~22.2.0'` (23.x wrote `~22.1.0`),
so `@angular/router` resolves to 22.2.4, clear of the advisories on 22.1.8;
`@nx/eslint` is now an inferred plugin (`nx.json` gains `plugins`, and
`apps/web/project.json` loses its `lint` target); `serve` targets gain
`readyWhen`; the root `README.md` title is `# Workspace`. The `@nx/angular:application`
step no longer failed on the build-script gate (with pnpm 12.16.1): it left
`allowBuilds` entries set to `false` for `esbuild`, `lmdb`, `msgpackr-extract`
and `@parcel/watcher`, which `scaffold_angular`'s approval step overwrites with
`true` as before.

**pnpm's build-script gate.** pnpm 12 blocks native build scripts
(`@parcel/watcher`, `esbuild`, `lmdb`, `msgpackr-extract`) behind an
allow-list (`ERR_PNPM_IGNORED_BUILDS`) unless approved. At 23.2.1 both `pnpm install`
steps above failed on the first pass and left `pnpm-workspace.yaml` stamped
with an `allowBuilds` stub naming exactly the blocked packages; setting each
to `true` and re-running `pnpm install` completes it. `scaffold_node`
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
`.angular/`, `coverage/` — everything `reconcile_node`'s exclusion list
and a normal `.gitignore` already exclude from a real `kiln new` run.
`pnpm-lock.yaml` is kept, as the story requires.
