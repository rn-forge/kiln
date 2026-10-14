# E9 — The node archetypes

|  |  |
| -- | -- |
| **State** | New |
| **Tags** | deferred |
| **Entry criteria** | a repo in scope needs a second toolchain — pnpm release, node CI, no uv |

## Scope

`node-lib` (pnpm/Nx workspace of published UI libraries; prior art ngkit;
release tag `v<version>` for one fixed group, as ngkit does, with per-package
`<package>-v<version>` an open choice — [F9.1](F9.1-node-lib-hosts-ngkit-ci.md))
and `node-web-app` (standalone pnpm-managed Nx frontend consuming remote APIs;
release tag `v<version>`). Both are named in the catalogue
([ADR-0005](../../../adr/ADR-0005.md)) so the taxonomy is fixed, and deferred to
post-v1 because nothing in v1 scope uses them.

Frontend support here builds on E5's shared frontend module
([S5.2.4](../E5-web-archetypes/F5.2-kiln-new-web-end-to-end.md#s524-frontend-scaffolding-has-its-own-module));
it is not copied into the node module. Keep `--frontend` as the implementation
selector, validated against each archetype; the archetype selects the toolchain
and component topology ([ADR-0005](../../../adr/ADR-0005.md)).

Markdown in a node archetype is formatted by mdformat under the seeded
`.mdformat.toml`, as in every other archetype, never by prettier: the seeded
`.prettierignore` excludes `*.md`, so the docs tree is byte-identical across
archetypes. ngkit's configuration is the prior art.

## Features

| ID | Feature | Depends on | State |
| -- | -- | -- | -- |
| [F9.1](F9.1-node-lib-hosts-ngkit-ci.md) | `node-lib` renders ngkit's CI | F6.3; the entry criterion | New |

## Open questions

1. **ngkit** (the Nx + Angular library monorepo): is it `node-lib` when this
   epic unparks, or hand-managed? (Open question 6, first raised as a fourth
   archetype `ng-lib`.) ngkit's CI is now written as a portable template with
   template-owned files and repository-owned declarations
   (`docs/architecture/ci-template.md`), which is the shape `node-lib` would
   generate; [F9.1](F9.1-node-lib-hosts-ngkit-ci.md) lists what kiln lacks.
1. **Running mdformat without uv.** A node archetype has no Python toolchain, so
   its `task format` needs another way to run the pinned mdformat — `uvx`, or
   a small uv project for the docs tooling alone.
