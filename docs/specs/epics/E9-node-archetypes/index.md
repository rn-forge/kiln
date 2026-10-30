# E9 — The node archetypes

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-10-29 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F9.1 — `node-lib` renders ngkit's CI](F9.1-node-lib-hosts-ngkit-ci.md) | Active | release-1 | 2 New · 11 Closed |
| [F9.2 — One node scaffold](F9.2-one-node-scaffold.md) | Active | release-1 | 3 New · 7 Closed |

<!-- END derived features -->

## Scope

`node-lib` (pnpm/Nx workspace of published UI libraries; prior art ngkit;
release tag `v<version>` for one fixed group, as ngkit does —
[ADR-0015](../../../adr/ADR-0015.md)) and `node-web-app` (standalone
pnpm-managed Nx frontend consuming remote APIs; release tag `v<version>`). Both
are named in the catalogue ([ADR-0005](../../../adr/ADR-0005.md)) so the
taxonomy is fixed. `node-lib` is release-1, so that ngkit can adopt kiln.
`node-web-app` stays deferred, because nothing in scope uses it.

Frontend support here builds on E5's shared frontend module
([S5.2.4](../E5-web-archetypes/F5.2-kiln-new-web-end-to-end.md#s524-frontend-scaffolding-has-its-own-module));
it is not copied into the node module. Keep `--frontend` as the implementation
selector, validated against each archetype; the archetype selects the toolchain
and component topology ([ADR-0005](../../../adr/ADR-0005.md)).

Markdown in a node archetype is formatted by mdformat under the seeded
`.mdformat.toml`, as in every other archetype, never by prettier: the seeded
`.prettierignore` excludes `*.md`, so the docs tree is byte-identical across
archetypes. ngkit's configuration is the prior art.

## Decisions

**Unparked 2026-10-14.** The owner wants ngkit to adopt kiln before release-1
ships, so `node-lib` moves into release-1. `node-web-app` stays deferred: no
repository in scope uses it. The decisions are
[ADR-0015](../../../adr/ADR-0015.md).

1. **ngkit is `node-lib`**, not hand-managed. Its template-owned and
   repository-owned split (`docs/architecture/ci-template.md`) maps onto
   kiln's generated and seeded files.
1. **mdformat runs through uv.** [ADR-0012](../../../adr/ADR-0012.md) already
   decided this on 2026-10-01: MkDocs and mdformat are pinned and run through
   `uv` in every repository. A `node-lib` repository has a root
   `pyproject.toml` with no package, whose dev group pins the docs tooling and
   kiln.
1. **`node-lib` meets [ADR-0016](../../../adr/ADR-0016.md)'s CI contract.** It
   may keep its Nx-native affected CI ([ADR-0015](../../../adr/ADR-0015.md))
   only while it does. Where ngkit's CI diverges is listed on
   [F9.1](F9.1-node-lib-hosts-ngkit-ci.md#audit-against-the-ci-contract).
