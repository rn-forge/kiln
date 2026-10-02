# Specs

What this repo is made of and what is left to build. **Start here:** the board
says what is next; the epic says how; its ADRs say why. The Releases and Backlog
sections below are derived from the epic, feature and release pages by
`task docs:generate`; never edit inside their fence.

<!-- BEGIN derived board -->

## Releases

| Release | Status | Features |
| -- | -- | -- |

## Backlog

Every feature is on a release or Removed.

<!-- END derived board -->

Ideas not yet agreed as work are parked in the [ideas list](ideas.md).

## Conventions

- **Taxonomy.** Epic `E<n>` → feature `F<n>.<m>` → story `S<n>.<m>.<k>`. The
  prefix chain locates a bare ID without a lookup. IDs are permanent: a moved
  story keeps its ID, and gaps are fine.
- **Every piece of work is an epic**, closed work included. There is no build
  log.
- **State lives on the work.** Epics and features carry `State` in a metadata
  table, stories on a `**State:**` line: `New`, `Active`, `Closed` or
  `Removed`. The board above is derived from them, never a second copy.
- **A feature's `Iteration` is its release.** A release page's Scope table is
  derived from it, so moving a feature edits only the feature.
- **A story is closed when its acceptance holds.** Each story carries an
  `**Acceptance:**` list of observable results, and the tests that prove it
  belong in that list.
- **A feature states its predecessors and its acceptance**: a `Predecessors`
  row, and, when it has several stories, a `## Acceptance` block that
  exercises every story and fails loudly.
- **Ideas are a parking lot.** An idea not yet agreed as work is a row in
  `ideas.md`, with no ID and no state. Agreed work that is not ready is tagged
  `deferred`, with entry criteria.
- **Design lives with the work** — a `## Design` section on the feature, or the
  epic's `design.md`. Current behaviour belongs in
  [architecture](../architecture/index.md).
- **Decisions are ADRs**, one file per topic, revised in place with a dated line
  under `## Background` when they change — see [the log](../adr/index.md).
- **Open questions live on the feature or epic they block.** Answered, a
  question becomes an ADR or a rejected option recorded on the feature, and
  leaves the page.
