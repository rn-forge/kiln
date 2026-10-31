# kiln simplification

[Back to the ideas](index.md)

An impartial review of kiln on 2026-10-20 asked whether kiln is
over-complicated. It is, but mostly in its process and in the standard it
enforces, not in the generator code. This page records the findings so they can
be refined into work later. Nothing here is agreed.

## The evidence

| Measure | Value (2026-10-20) |
| -- | -- |
| Age | 6 weeks, 148 commits |
| Python under `src/` | ~9.1k lines, plus ~3.8k lines of templates |
| Tests | ~13k lines |
| Docs | ~188k words: 16 ADRs, 14 epics, 40 features, ~150 stories |
| Churn, last 100 commits | 239 file-touches under `docs/` against 119 under `src/` |
| Repositories kiln generates and checks | none; kiln's own `state.json` is hand-seeded, and pykit's adoption trial was reverted |

The last row matters most. Every design choice so far has been judged against
imagined repositories, not real ones.

## Findings

### 1. The docs and work-item model is about 40% of the product

The `docs` module is ~2.9k lines of Python and ~2.1k lines of templates, out of
~12.9k in total. It does more than scaffold MkDocs. It puts an Azure
DevOps-shaped work-item system into every generated repository: ordered metadata
tables, derived boards, release scope tables, area tabs and story summaries.
`work.py` alone is 823 lines. [ADR-0011](../../adr/ADR-0011.md) itself says no
tracker has been chosen.

**Possible simplification:** seed a docs skeleton the repository owns, keep only
the site build and the nav, and take the work-item validation out of the
standard. If kiln and pykit still want it, it becomes an opt-in module or a
separate tool.

### 2. The process costs more than the product

[F6.1](../epics/E6-rebuild-the-repos/F6.1-pykit-skeleton.md) is 14.8k words.
[The standardization plan](../../plans/standardization-plan.md) is 24k words.
Specs written as verbatim build-lists for smaller models turn every story into a
design document that then has to be kept in sync.

**Possible simplification:**

- When a story closes, cut it down to its outcome and the build's settled
  choices. Git keeps the full build list.
- Move `docs/plans/` and `docs/plans/reviews/` out of the site, as archive.
- Finish the ADR slimming that `adr-refactor.md` began, at 150–300 words per
  decision, and remove that stray file from the repository root.

### 3. There are more archetypes than adopters

Five Python archetypes are shipped or in progress, `node-lib` is in release-1,
and the flags multiply them: backend, frontend, lifecycle, docs profile, CI
provider, sonar and release mode. The manifests already need an `untested`
field, and the render matrix and goldens exist to keep the combinations honest.
That is a lot of surface for no adopters among about six repositories in the
workspace.

**Possible simplification:** freeze the archetype and flag count until one real
repository runs `kiln apply` and its CI gate. Then add each dimension only when
a real repository needs it, as was already done for Django
([F5.4](../epics/E5-web-archetypes/F5.4-django-scaffold.md)).

### 4. kiln does not regenerate itself yet

`state.json` is re-seeded by hand after every change to a managed file, so kiln
pays the generator's costs without its benefit. Self-hosting
([S4.8.1](../epics/E4-generator/F4.8-self-hosting.md)) is the cheapest real
proof available. Some docs are already stale:

- `README.md` says "there is no `kiln apply` yet", but the command exists.
- The header of `.rn-forge/kiln/config.toml` still talks about "Phase B" and
  "Phase D".

**Possible simplification:** put S4.8.1 ahead of any new scope.

### 5. Some doctor checks police kiln's own output

Rules 1 and 2 of `task-layout` (`modules/tasks/checks/layout.py`, 465 lines)
apply to the root `Taskfile.yml` and the managed `tasks/*.yml`. Both are
generated and already covered by the drift check, so those rules test kiln's
templates, not the repository. Rule 3 (the `required_validate` tasks stay
reachable from `validate`) could be checked on the config at render time instead
of by parsing YAML afterwards.

**Possible simplification:** move rules 1 and 2 into kiln's own tests, and rule
3 into config validation. Then do the same review for each of the other doctor
checks.

### 6. Coupling with pykit runs both ways

kiln imports pykit's commons, cli and tooling, and plans every archetype's CI
with `rn-forge-devops` ([ADR-0016](../../adr/ADR-0016.md)). It also carries an
upstream-pins table and a pin-flip epic
([E7](../epics/E7-pykit-release-pin-flip/index.md)), and `rn-forge-deps`
enforces which pykit packages a repository may depend on. As a result, kiln's
releases wait on pykit's.

**Questions to settle:**

- Does a single-package `python-tool` need the workspace planner in CI? The
  rendered `ci.yml` for that cell was not checked.
- Is the rn-forge dependency allow-list kiln's policy to enforce, or pykit's?

### 7. Smaller items

- The CLI has 11 commands plus 6 lifecycle verbs. `config-update`,
  `config-upgrade` and `prompt` may fold into fewer commands.
- `commands.py` is a 1.2k-line catch-all.

## What to keep

- **The core model:** each file has exactly one owner, renders read only
  committed config, CI runs kiln read-only, and modules compose through a
  small contract (`modules/base.py`).
- **The test discipline.**
- **One owner for the task vocabulary and CI:** the right answer to the four
  divergent pipelines that prompted kiln.

## A possible reset order

1. Self-host kiln (S4.8.1), then adopt one real repository. Add nothing new
   until both are done.
1. Change the work-item model from managed and enforced to seeded and owned by
   each repository (finding 1).
1. Limit archetypes and flags to what real repositories use today (finding 3).
1. Archive plans and history, and trim closed stories (finding 2).

## Open questions for refinement

- Which findings become epics or features, and which are dropped?
- Does trimming the docs model reopen [ADR-0011](../../adr/ADR-0011.md) and
  [ADR-0013](../../adr/ADR-0013.md), or only the specs that build them?
- Does release-1 wait for any of this, given that other repositories adopt from
  the release-1 tag? A model that is trimmed after adoption has to be migrated
  in every adopter.
