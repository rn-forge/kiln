# plans/ — what belongs here

This area is kiln's own extension to the seeded model (D44). It holds the record
kiln's work grew out of — not the work itself, which is epics under `specs/`.

## Belongs here

- `context.md`: the evidence, the harvest inventory, what each review changed,
  the reasoning behind the later ADRs, what was rejected, and the map from the
  frozen plan to its new homes.
- A frozen plan, kept unedited as the baseline for checking the move out of it
  for drift.
- A standalone plan for work kiln's releases do not carry — agent configuration,
  intellibuild — built on its own schedule.
- `reviews/`: review passes over a phase's output, kept verbatim.

## Does not belong here

| Instead of | Put it in |
| -- | -- |
| Work to do, steps, acceptance commands | an epic under `specs/` |
| A choice between real alternatives | an ADR under `adr/` |
| The standard itself | `reference/` |
| How something already works | `architecture/` |

## Naming and shape

- One kebab-case `.md` per document; `index.md` lists them.
- A frozen plan is never edited — not even its links. Corrections go in
  `context.md`.
