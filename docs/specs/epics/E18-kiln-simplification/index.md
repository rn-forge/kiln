# E18 — kiln simplification

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
| [F18.5 — Tests that survive a refactor](F18.5-tests-survive-a-refactor.md) | New | release-1 | 4 New |
| [F18.6 — `commands` is a package, one module per command](F18.6-commands-package.md) | New | release-1 | 3 New |
| [F18.7 — One owner per concept](F18.7-one-owner-per-concept.md) | New | release-1 | 4 New |
| [F18.8 — Modules meet only through composition](F18.8-modules-meet-through-composition.md) | New | release-1 | 2 New |
| [F18.9 — Large files split by job](F18.9-large-files-split.md) | New | release-1 | 4 New |
| [F18.10 — The defects the reviews confirmed](F18.10-review-defects.md) | New | release-2 | 12 New · 3 Removed |
| [F18.11 — Checks police the repository, not kiln's output](F18.11-checks-police-repository-content.md) | New | release-2 | 2 New |
| [F18.12 — The review defects release 1 takes](F18.12-release-1-review-defects.md) | New | release-1 | 3 New |
| [F18.13 — Build briefs outside the record](F18.13-build-briefs-outside-the-record.md) | New | release-1 | 4 New |
| [F18.14 — A kiln pin is a commit](F18.14-a-pin-is-a-commit.md) | New | release-1 | 3 New |

<!-- END derived features -->

Simplifies kiln's code, tests and specs before v1, then lands `feature/v1` on
`main` as a single commit. It acts on
[the kiln-simplification idea](../../ideas/kiln-simplification.md). The epic was
renamed from "The v1 spec rewrite and one commit on main" on 2026-11-10, when
the code review of that date added F18.5 to F18.11.

### The order

```text
F18.5 tests survive a refactor ─→ F18.6 commands package ─→ F18.7 one owner per concept
  ─→ F18.8 composition only ─→ F18.9 large files split
  ─→ F18.12 release-1 review defects ─→ F18.13 briefs outside the record
  ─→ F18.14 a pin is a commit
  ─→ F18.1 test renames ─→ F18.2 IDs out ─→ F18.3 area epics ─→ F18.4 one commit on main
release 2: F18.10 review defects · F18.11 checks police the repository
```

F18.5 to F18.9 change no behaviour. They come before the spec rewrite, so that
F18.3's area epics describe the simplified code, and before F18.1, so that the
renames land in test files already organised by subject. F18.10 and F18.11
change what kiln renders or reports, so they wait for the tag. The owner
confirmed that split on 2026-11-13, and moved three of F18.10's defects to
release 1 as F18.12, built after F18.9. On 2026-11-14 the owner added F18.13,
which comes before the spec rewrite, so that F18.3 cuts the briefs to a rule
that keeps them out, and F18.14, so that repositories following kiln's branch
pin a commit until the tag.

### The spec rewrite (F18.1 to F18.4)

Rewrites the specs to describe kiln as it is at v1, one epic per area of the
product, and lands `feature/v1` on `main` as a single commit. The spec format
stays: metadata tables, headings, derived regions and the ID taxonomy. Only the
prose inside them is cut. Build lists, verbatim code and step-by-step briefs
were needed while smaller models built the stories. Now that the code exists,
they are redundant and only drift.

The rewrite is the last work in release 1, before the tag
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
