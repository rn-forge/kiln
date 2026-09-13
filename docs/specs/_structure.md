# specs/ — what belongs here

## Belongs here

- Every piece of work as an epic, `epics/E<n>-<slug>/index.md` — shipped work
  included, marked `done` with its ship date, so the tree is the inventory of
  what kiln is made of.
- A planned epic's features as `F<n>.<m>-<slug>.md` beside it, each holding its
  stories inline as `S<n>.<m>.<k>` headings with their own `**Status:**` line
  and `**Acceptance:**` list, plus the feature's `**Depends on:**` line and
  `## Acceptance` block ([conventions](index.md#conventions)).
- Design for work not yet built: a `## Design` section in the feature it belongs
  to, or `design.md` in the epic when it spans features.
- Open questions, as a `## Open questions` section on the epic or feature they
  block.
- Work that is real but not ready, as a `deferred` epic in no release, with
  entry criteria.

## Does not belong here

| Instead of | Put it in |
| -- | -- |
| Behaviour that already exists | `architecture/` |
| A decision | an ADR under `adr/` |
| Which stories ship when | `releases/` — it links here, never restates |
| History, evidence, harvest records | `plans/context.md` |
| A `progress.md`, `backlog.md`, `decisions.md` or `overview.md` | the epic, a deferred epic, an ADR, or the README |

## Naming and shape

- `epics/E<n>-<slug>/` directories; feature files `F<n>.<m>-<slug>.md`.
- IDs are permanent: never renumber; a moved story keeps its ID. Gaps are fine.
- Every epic index carries a `**Status:**` line — `planned`, `elaborating`,
  `in progress`, `done` (with `**Shipped:**`) or `deferred` (with entry
  criteria) — and `index.md`'s board lists each epic in exactly one group.
- A shipped epic is one `index.md`; its features are rows, not files.
- An answered open question becomes an ADR, or a rejected option recorded on the
  feature under *Considered and rejected*; the question is then removed.
