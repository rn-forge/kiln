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
