# Specs

What this repo is made of and what is left to build. **Start here:** the board
says what is next; the epic says how; its ADRs say why.

## Board

Every epic appears in exactly one group. An empty group stays on the page: an
empty section is an answer, an absent one reads as an oversight.

### In progress

Nothing in flight.

### Scheduled

Nothing scheduled.

### To elaborate

Nothing agreed without stories.

### Deferred

Nothing deferred.

### Shipped

Nothing shipped yet.

## Status legend

| Status | Means | Board group |
| -- | -- | -- |
| `in progress` | someone is working on it now | In progress |
| `planned` | stories written, and in a release | Scheduled |
| `elaborating` | agreed in principle; no stories yet, so no release | To elaborate |
| `deferred` | real but not ready; its entry criteria say what would change that | Deferred |
| `done` | shipped, with its date | Shipped |

## Conventions

- **Taxonomy.** Epic `E<n>` → feature `F<n>.<m>` → story `S<n>.<m>.<k>`. The
  prefix chain locates a bare ID without a lookup. IDs are permanent: a moved
  story keeps its ID, and gaps are fine.
- **Every piece of work is an epic**, shipped work included, marked `done` with
  its ship date and its acceptance as run. There is no build log.
- **Status lives on the story.** A feature file holds its stories, each with a
  `**Status:**` line. The epic index carries the epic's status and ship date;
  this board is the index of those, never a second copy.
- **A story is done when its acceptance holds.** Each story carries an
  `**Acceptance:**` list of observable results, and the tests that prove it
  belong in that list.
- **A feature states its dependencies and its acceptance**: a `**Depends on:**`
  line, and a `## Acceptance` block that exercises every story and fails
  loudly.
- **One home per story; releases link.** A release page names its scope by story
  ID and links here. Moving a story between releases edits only release pages.
- **The backlog is deferred epics**, each with entry criteria. There is no
  `backlog.md`.
- **Design lives with the work** — a `## Design` section on the feature, or the
  epic's `design.md`. Current behaviour belongs in
  [architecture](../architecture/index.md).
- **Decisions are ADRs**, one file per topic, revised in place with a
  `## History` when they change — see [the log](../adr/index.md).
- **Open questions live on the feature or epic they block.** Answered, a
  question becomes an ADR or a rejected option recorded on the feature, and
  leaves the page.
