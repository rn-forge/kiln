# specs/ — what belongs here

## Belongs here

- Every piece of work as an epic, `epics/E<n>-<slug>/index.md` — shipped work
  included, marked `done` with its ship date, so the tree is the inventory of
  what this repo is made of.
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

## Changing this area

**Adding an epic or a feature:**

1. Take the next free ID. Never renumber a sibling.
1. Create `epics/E<n>-<slug>/index.md` with its status: `elaborating` while it
   has no stories, `planned` once it has stories and a release, or `deferred`
   with entry criteria.
1. For a planned epic, write one feature file per feature, stories inline. Give
   a story its own file only when its acceptance runs past about a screen.
1. Put design at the lowest level that fits: the feature's `## Design`; the
   epic's `design.md` when it spans features; a link to `architecture/` when
   it describes current behaviour.
1. Add the epic's row to the board in `index.md`, in exactly one group, and run
   `task docs:nav`.

**Writing acceptance:**

- Each line is an observable result, and the tests that prove a story belong in
  its acceptance, not in a story of their own.
- A decision the work needs is its own story, so other work can depend on the
  decision without depending on its implementation.
- The feature's `## Acceptance` block exercises every story, each line tagged
  with the story it proves; what cannot be scripted is listed under the block.
- The block fails loudly: `set -euo pipefail`, never `|| echo`, and negative
  checks through these helpers rather than a bare `! cmd`, which `set -e`
  ignores:

```bash
absent() { local rc=0; rg -q --hidden --glob '!.git' "$@" || rc=$?; [ "$rc" -eq 1 ]; }
fails_with() { local out rc=0; out=$("${@:2}" 2>&1) || rc=$?; [ "$rc" -ne 0 ] && grep -qF -- "$1" <<<"$out"; }
```

**Working on and closing out an epic:**

1. Starting: flip the epic to `in progress` and move its board row.
1. A story is `done` when its acceptance holds; run the feature's acceptance
   block, then flip the story's status.
1. When every story is done: `**Status:** done`, a `**Shipped:**` date, the
   acceptance as run recorded on the epic, and the row moved to Shipped. Done
   work is never deleted.

**Promoting a deferred epic:** when its entry criteria come true, `elaborating`,
write its stories, then `planned` with a release. Nothing renumbers.
