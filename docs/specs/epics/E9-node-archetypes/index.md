# E9 — The node archetypes

**Status:** deferred

**Entry criteria:** a repo in scope needs a second toolchain — pnpm release,
node CI, no uv.

## Scope

`node-lib` (pnpm/Nx workspace of published UI libraries; prior art ngkit;
release tag `<package>-v<version>`) and `node-web-app` (standalone pnpm-managed
Nx frontend consuming remote APIs; release tag `v<version>`). Both are named in
the catalogue ([ADR-0005](../../../adr/ADR-0005.md)) so the taxonomy is fixed,
and deferred to post-v1 because nothing in v1 scope uses them.

## Open questions

1. **ngkit** (the Nx + Angular library monorepo): is it `node-lib` when this
   epic unparks, or hand-managed? (Open question 6, first raised as a fourth
   archetype `ng-lib`.)
