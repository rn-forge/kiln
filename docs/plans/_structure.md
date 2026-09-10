# plans/ — what belongs here

This area is kiln's own extension to the seeded model (D44). It exists because
this repo's work arrives as multi-phase plans with acceptance commands, which
are neither epics nor decisions.

## Belongs here

- A plan: phases, each with steps and an acceptance block that is a command plus
  its expected result. Written to be executed by someone who has not read the
  conversation it came out of.
- A harvest inventory: what was carried over from a donor repo, and what was
  deliberately dropped.

## Does not belong here

| Instead of | Put it in |
| -- | -- |
| A choice between real alternatives | an ADR under `adr/` |
| The standard itself | `reference/` |
| How something already works | `architecture/` |

## Naming and shape

- One kebab-case `.md` per plan; `index.md` lists them, newest first.
- A plan states its revision and its decision log, and is superseded rather than
  edited in place once a phase has been executed against it.
