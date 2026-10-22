# Decisions

Durable choices that constrain kiln's architecture and the repository standard
it generates. Each record opens with the decision, what follows from it, and
what it influences; alternatives and history are at the bottom.

Scope, supported configurations, implementation details and migration work
belong in [specs](../specs/index.md); exact rules belong in
[the reference](../reference/standard-repo.md).

Read in order — the first two set the product's footing, the rest constrain what
it generates.

| # | Decision | Scope |
| -- | -- | -- |
| [0001](ADR-0001.md) | Ship kiln as one pinned distribution of modules | kiln and its generated repositories |
| [0002](ADR-0002.md) | Build on the rn-forge platform; keep repository policy in kiln | the rn-forge workspace |
| [0003](ADR-0003.md) | Ownership is complete or absent | generated repositories |
| [0004](ADR-0004.md) | Render only from committed configuration | renders and verification runs |
| [0005](ADR-0005.md) | Archetypes define topology; flags form independent dimensions | the archetype catalogue |
| [0006](ADR-0006.md) | Commit generated CI, and run the pinned kiln read-only | CI in generated repositories |
| [0007](ADR-0007.md) | Compose a declared public task vocabulary from modules | the task surface |
| [0008](ADR-0008.md) | Only published packages get their own docs site | the docs layout of Python repositories |
| [0009](ADR-0009.md) | A repository's specs are accepted inside that repository | every repository's specs |
| [0010](ADR-0010.md) | The canon carries an architecture baseline, as managed records (proposed) | the product code of every generated repository |
| [0011](ADR-0011.md) | Work is tracked as Azure DevOps-shaped work items | the specs and releases of every generated repository, and kiln's |
| [0012](ADR-0012.md) | Every repository publishes one MkDocs site, whatever its language | the docs site of every generated repository |
| [0013](ADR-0013.md) | The docs site navigates by area tabs, and work pages open with derived summaries | the docs site of every generated repository, and kiln's |
| [0014](ADR-0014.md) | A library workspace's CI is planned by rn-forge-devops, and its own members are exempt from the rn-forge dependency contract | `python-lib` repositories, and `rn-forge-deps` everywhere |
| [0015](ADR-0015.md) | `node-lib` renders ngkit's CI: one release group, a dispatched release, and generated CI helpers | `node-lib` repositories |
| [0016](ADR-0016.md) | Every archetype's CI follows one contract, planned by rn-forge-devops | the generated CI of every archetype |
| [0017](ADR-0017.md) | kiln ships the CI planner as `kiln-devops` (proposed) | the generated CI of every archetype, and kiln's distribution |
