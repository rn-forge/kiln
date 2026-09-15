# Carrying specs and decisions into a rebuilt repo

> One-time judgement ships as a kiln prompt ([ADR-0006](../adr/ADR-0006.md)).
> This runbook becomes `kiln prompt port-docs` in
> [S4.5.6](../specs/epics/E4-generator/F4.5-cli.md), and is deleted then.

A pre-v1 repo is rebuilt with `kiln new`, not migrated
([ADR-0006](../adr/ADR-0006.md)): its files are not carried over, but its specs
and decisions are, as prior art. This runbook moves them into the new repo's
`docs/specs/` and `docs/adr/` so that nothing is lost, nothing is said twice,
and a second person doing the same move would produce the same tree.

The target shape is the new repo's own `docs/_structure.md`, each area's
`_structure.md`, and its specs board conventions. This runbook is only the
one-time move, and the judgement calls in it.

## 1. Inventory the source

In the old repo, before writing anything in the new one:

- **Where the spec really lives.** Follow the old repo's agent instructions; do
  not assume `docs/specs/`. Find each monolith — a file past a few hundred
  lines whose top-level headings cover objective *and* decisions *and* stories
  *and* history — and list its headings (`rg -n '^## ' <file>`). That list is
  the mapping's input.
- **Its ID scheme** (`§14`, `E1`, `S2.3`, ticket keys).
- **Every inbound reference, repo-wide**, including deep anchors
  (`spec.md#43-composable-adapters`) from README, CLAUDE.md, AGENTS.md and
  `mkdocs.yml`. A docs linter walks only `docs/`, so these rot silently.
- **What is already stated elsewhere**: the README's opening, the docs home, the
  architecture pages. Anything they already say is linked from the new tree,
  never copied into it — usually the largest deletion of the move.
- **An existing ADR log or `decisions.md`**, and whether releases are tracked
  somewhere else (milestones, a CHANGELOG).

**Decision point — IDs.** If commit messages, pull requests or issues cite the
old IDs, keep them as the new IDs; nothing can rewrite those references. If
nothing outside the file cites them, use `E<n>`/`F<n>.<m>`/`S<n>.<m>.<k>`.

**Decision point — releases.** If releases are already tracked elsewhere, the
new `releases/` pages point at that record instead of competing with it. Ask the
owner before creating a second one.

## 2. Map every section, and agree the mapping first

Write a table of every top-level section to its destination, and get the owner's
agreement before writing anything in the new repo.

| Source section | Destination |
| -- | -- |
| Purpose, objective, stack, non-goals | the README or docs home, not the spec tree |
| A decision with alternatives and rationale | `adr/ADR-<nnnn>.md`, one per topic |
| Models, contracts, layouts, protocols | the owning feature's `## Design`, the epic's `design.md`, or `architecture/` when it is current behaviour |
| Epics and stories | `specs/epics/E<n>-<slug>/` |
| Build history, progress, phase logs | one `done` epic per shipped phase, with its ship date |
| Deferrals, pending work | a `deferred` epic with entry criteria |
| Test strategy, definition of done | the epic it constrains, or the development guide if repo-wide |

## 3. Move, under these rules

- **Every section lands somewhere.** Anything with no home is listed as dropped
  in the report — never silently.
- **Content moves verbatim** apart from heading levels and links. Do not edit
  meaning while moving it; a move that also rewrites is a diff nobody can
  review.
- **Do not create a page the new repo already has.** No `overview.md`; a stack
  table that restates `pyproject.toml` is a liability, not a spec.
- **One epic per unit the source already named** — a phase, a milestone, a
  numbered section, a dated log entry. Do not regroup by theme, however much
  tidier: nobody can reproduce or check that judgement. Merge two only when
  the source says they were one delivery, and say so.
- **Allocate IDs in source order**, top to bottom, so re-running the move
  assigns the same numbers.
- **Shipped work is framed, not reconstructed.** Its headings become features,
  its bullets stories, all `done`, with the log's dates and validation figures
  on the epic. No new acceptance for shipped work, and no reading the code to
  enrich it. A shipped epic is one `index.md`; a planned epic gets a file per
  feature.
- **Design already in `architecture/` is deleted, not moved.** Grep for it
  first; link instead, and record it as "already covered by `<page>`". Current
  behaviour that no page describes gets a new `architecture/` page, not a home
  inside a historical epic.
- **Decisions:**
    - A `decisions.md` row is one ADR, in table order, unless two rows state the
      same decision twice — merge those and say so. A row with no alternative
      considered is design; route it to a feature and count it as routed.
    - Rationale outside the decisions section is still a decision when it names a
      rejected alternative. Sweep for `considered`, `rejected`, `instead of`,
      `the alternative`, `why not` and `deliberately`.
    - Number them in source order: table rows first, then the extracted ones.
    - **A chain of superseding decisions on one topic becomes one ADR.** Its
      Decision is the latest; the earlier ones become dated entries under its
      `## History`, newest first.
- **No redirect stubs.** Delete nothing in the new repo that points back at the
  old one; fix the references instead.

## 4. Wire it into the new repo

- Every epic on the board in exactly one group; every ADR in `adr/index.md`.
- `task docs:nav`.
- `CLAUDE.md` links to the specs board and the ADR log; it describes neither.
- Strip provenance notes ("moved verbatim from §14") before calling it done:
  they point at a file that no longer exists.

## 5. Validate

- `task validate` in the new repo passes.
- Every story ID a release names resolves.
- Every epic has a status, and every `done` one a ship date or an explicit
  "predates dated records" note.
- The epic count equals the number of delivery units the source named.
- No block of moved design prose also appears in `architecture/` (grep a
  distinctive sentence from each).
- Content in ≈ content out, by word count across the moved sections. A large
  shortfall means prose was dropped.

## 6. Report to the owner

The mapping as applied; what was dropped and why; what was deleted because the
README or architecture already carried it; which epics were framed as `done` and
from which sections; the ADRs allocated, with any chains folded into one
History; the ID scheme and why; the references rewritten; and the validation
output.
