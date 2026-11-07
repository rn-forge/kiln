# E18 — The v1 spec rewrite and one commit on main

|  |  |
| -- | -- |
| **State** | New |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F18.1 — Tests named by behaviour](F18.1-tests-named-by-behaviour.md) | New | release-1 | 4 New |
| [F18.2 — Spec IDs out of the code and the docs outside the specs](F18.2-ids-out-of-code-and-docs.md) | New | release-1 | 4 New |
| [F18.3 — One epic per area](F18.3-area-epics.md) | New | release-1 | 10 New |
| [F18.4 — `feature/v1` lands on `main` as one commit](F18.4-one-commit-on-main.md) | New | release-1 | 2 New |

<!-- END derived features -->

Rewrites the specs to describe kiln as it is at v1, one epic per area of the
product, and lands `feature/v1` on `main` as a single commit. The spec format
stays: metadata tables, headings, derived regions and the ID taxonomy. Only the
prose inside them is cut. Build lists, verbatim code and step-by-step briefs
were needed while smaller models built the stories. Now that the code exists,
they are redundant and only drift.

It is the last work in release 1, before the tag
([F7.2](../E7-pykit-release-pin-flip/F7.2-kiln-release-and-config-upgrade.md)),
and it starts once every other release-1 story has closed. Starting earlier
would mean merging the rewrite against every story still closing in the shared
checkout.

Source: the owner's decisions of 2026-11-06, refined from
[the kiln-simplification idea](../../ideas/kiln-simplification.md).

## Context

### Owner decisions (2026-11-06)

- **The spec format stays.** Only the prose inside it is cut.
- **One epic per area of the product.** Each area epic describes the current
  state, in place of the epics that record how kiln got there.
- **Explanations live in the specs.** Release pages summarise scope and status
  only.
- **`docs/plans/` is removed.** It is historical context only.
- **Test names lose their story IDs.** Each test is named after the behaviour it
  proves.
- **`feature/v1` is kept for reference.** `main` takes one squashed commit.

### What the rewrite has to handle (measured 2026-11-06)

| Measure | Value |
| -- | -- |
| Specs | 240,884 words in 89 files. The largest feature is F6.1, at 15.0k words. |
| `plans/` and `releases/` | 44,843 words |
| `feature/v1` ahead of `main` | 312 commits. `main` holds only `initial commit`. |
| Test functions named `test_s<id>_…` | 1,366 |
| Spec-ID references outside `specs/` | `releases/release-1` 296, `plans/context.md` 34, the ADRs about 70, `README.md` 7, `runbooks/cutover.md` 6, `src/` 15 |
| Pages linking into `plans/` | 27, plus `mkdocs.yml` and `docs/_areas.yml` |

### Numbering

The area epics take the next free IDs after E18. The old IDs are not reused,
because `feature/v1`'s commits name them and that branch is kept. Each area epic
carries one plain line under its table, `Replaces: E4, E15`, which leads from an
area back to the old IDs and from there to the branch. There is no separate
mapping table. E18 stays on `main` as the record of the reset.

### Other repositories

pykit's and ngkit's specs cite kiln spec IDs, so the rewrite leaves those
citations dangling. Those pages are theirs to fix: each restates the requirement
in its own words before its cutover adopts from the release-1 tag. Nothing in
this epic edits another repository.

## Open questions

- An area epic is `Closed` once v1 ships. When new work arrives later, does it
  go into that epic as a `New` feature, which reopens the epic to `Active`, or
  into a new epic? It does not block E18, but it should be settled before the
  first post-v1 feature.
