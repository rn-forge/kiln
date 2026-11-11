# kiln simplification

[Back to the ideas](index.md)

An impartial review of kiln on 2026-10-20 asked whether kiln is
over-complicated. It is, but mostly in its process and in the standard it
enforces, not in the generator code. This page records the findings so they can
be refined into work later. Nothing here is agreed, except the v1 spec rewrite,
which is now [E18](../epics/E18-kiln-simplification/index.md).

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

### 8. The design has no home once an epic closes

Added 2026-11-05, after the archetype catalogue proved hard to find. kiln's
major designs (archetypes, config and apply, modules, tasks, docs, doctor) have
no architecture page. [architecture/](../../architecture/index.md) holds two
pages, and only [ci.md](../../architecture/ci.md) was promoted from an epic's
design (E15). The rest of the design is scattered:

- [reference/standard-repo.md](../../reference/standard-repo.md), at 636 lines,
  is meant for exact rules but carries the explanation too: the archetype
  catalogue, the docs layout and the dependency rationale.
- Epic `design.md` files hold the real design for
  [E4](../epics/E4-generator/design.md),
  [E12](../epics/E12-architecture-baseline/design.md),
  [E13](../epics/E13-docs-work-model/design.md) and E15 (its `design.md`,
  deleted when the epic closed). They are frozen at implementation time, and
  after that the code is the source of truth.
- ADRs carry explanation in their Consequences and Influences, but nobody looks
  for a design in the decision log.

The docs rules already ask for this. `docs/_structure.md` sends "behaviour as it
is now" to `architecture/`, and `architecture/_structure.md` admits "the
reasoning that survived a decision". The gap is the migration, and the absence
of a step that makes it happen.

**Possible simplification:** give each kind of document one job.

| Document | Holds |
| -- | -- |
| ADR | The decision, its consequences and alternatives, and a link to the architecture page. Short. |
| `architecture/<subject>.md` | The model, its principles, how the parts fit, and why. The main read. |
| `reference/standard-repo.md` | Exact rules, tables and checks, linking to architecture for the why. |
| Epic `design.md` | Working design while the epic is in flight. At close, its durable content moves to architecture, and it is left as history that links there. |

Candidate pages and their sources:

- `archetypes.md`: [ADR-0005](../../adr/ADR-0005.md), the catalogue and
  dependency-set sections of the standard, and E9's one node scaffold.
- `config-and-apply.md`: config, render, ownership, drift and backups, from
  [ADR-0003](../../adr/ADR-0003.md), [ADR-0004](../../adr/ADR-0004.md) and
  E16.
- `modules.md`: the generator's composition, from E4's design and
  [ADR-0001](../../adr/ADR-0001.md).
- `tasks.md`: the task vocabulary, namespaces and `required_validate`, from
  [ADR-0007](../../adr/ADR-0007.md).
- `docs-model.md`: areas, nav and the work model, from
  [ADR-0012](../../adr/ADR-0012.md), [ADR-0013](../../adr/ADR-0013.md) and
  E13's design.
- `doctor.md`: the checks, what each one enforces, and `doctor` versus `--full`.

Cautions:

- The routing rule ("an ADR links to architecture; an epic's design is promoted
  when the epic closes") belongs to the standard. `docs/_structure.md` and
  `architecture/_structure.md` are generated, so changing the rule is a kiln
  template change that every repository picks up. The pages themselves are
  kiln's own.
- Keep architecture pages at the level of principles and mechanisms. Leave the
  lists of flags, task names and check IDs to the reference or to generated
  output, or each page becomes a second copy of the code, with nothing to
  catch it going stale.
- Make the promotion a closing step in an epic's last story, so the gap does not
  reopen. A doctor check, such as "every accepted ADR links to an architecture
  page", can wait until the pages exist.

This finding works alongside finding 2. Trimming closed stories and ADRs is safe
only once their durable content has a home.

### 9. The same rule is implemented more than once, and the copies drift

Added 2026-11-05 from a code review by Codex against `8855021`, which reproduced
each case below. Five claims were checked again against the code, and all five
held: the registry gap, the reserved job names, the suites gate, the wildcard
floor and the dropped conflict. Several of kiln's defects come from one concept
having two or three implementations:

- **Check registration.** `checks.py` keeps a central registry, and each module
  also declares `checks()`. Doctor dispatches the registry, which lacks
  `kiln-pin`, so the pin check never runs. Its tests call it directly, so they
  pass anyway.
- **Reserved names.** The cicd schema's `GENERATED_JOBS` omits node-lib's
  `ci-cloud`, `ci-local` and `package` jobs, so a custom job may take those
  names and render as a duplicate key. Task includes have no reserved-name
  check at all, and `task-layout` catches a collision only after rendering.
- **Docs.** `structure.py` and `site.py` each validate links, and they disagree
  about gitignored generated pages. `site.py` reads `.gitignore` lines as
  literal paths, while the code next to it uses `GitIgnoreSpec`.
- **Distribution names.** The `rn-forge-deps` check, the CI planner and the
  range checker each normalise names differently. `rn.forge.commons` is
  governed in one and not in another.
- **State identity.** The state schema version and path are declared separately
  by the cycle, the baseline checker and the provenance reader.
- **Command entry points.** `config` preview selects artifacts without the
  starter policy that apply uses. Apply skips the docs finalisation that `new`
  and `init` run, so a switch from `none` to `mkdocs` fails on the first
  apply. `generate package` writes config, workspace and source before its
  drift preflight, and leaves a half-added package when that preflight fails.

Semantic validation is spread out in the same way. Archetype defaults differ
between direct load and layered resolve (the web-app backend and frontend dirs).
A noncanonical archetype name such as `python_tool` loads the manifest but
behaves as a different archetype. `ci.release = "pypi"` on `python-app` passes
validation and then raises a raw `ValueError`. `_areas.yml` and
`[tool.workspace-ci]` are parsed without a strict model.

**Possible simplification:**

- Declare each concept once and derive the others from it: checks through the
  module contract alone, reserved names from the job and include definitions,
  one link resolver, one name canonicaliser (`packaging`), and one state
  module.
- Run every cross-section rule at one render-free boundary after the schema is
  composed, with dotted config paths in the errors.
- Make `new`, `init`, `apply`, `config` and `generate` phases of one pipeline
  (plan, preflight, write, finalise), rather than each command composing its
  own. This would also break up `commands.py` (finding 7).
- Test through doctor and the commands, not by calling a check directly.

### 10. Module independence is held by a growing allow-list

From the same review. The `.importlinter` comment allows four grandfathered
sibling imports and says not to add a fifth, but the allow-list now has nine.
`tasks` reaches into cicd, docs and python, and `instructions` and the docs
generator reach into siblings too. That weakens the small module contract listed
under [What to keep](#what-to-keep).

**Possible simplification:** have composition pass the shared resolved values,
and move render-free helpers to their owner, instead of importing through
sibling artifact modules. The same review notes that live Nx-generator tests sit
in the offline module-test tree and pick themselves by whether `pnpm` is
present. They need an explicit integration marker.

## Defects from the code review

The 2026-11-05 review also found defects that are not about simplification. They
are listed here so they are not lost, and each is to be triaged into a story. P1
is release correctness, P2 a functional defect, and P3 a standards gap.

| # | P | Defect | Where |
| -- | -- | -- | -- |
| 1 | P1 | Workspace `suites` gate neither `sonar` nor `release`. Only `ci-ok` waits on them, after publishing. | `cicd/templates/ci.yml.j2` |
| 2 | P2 | Full doctor drops a plan `CONFLICT`, which has no entry in the action-to-finding map. | `doctor.py` |
| 3 | P2 | `Source.parse` does not split a ref containing `/`, such as `@feature/profile`. | `core/config/sources.py` |
| 4 | P2 | `==0.3.*` has no recognised floor, contradicting F15.4. Also undecided: must the sibling version satisfy the whole specifier? | `devops/requirements.py` |
| 5 | P2 | Provenance records raw values and compares normalised ones, so a whitespace-trimmed audit reason later reads as a repository override. | `core/config/manager.py`, `tasks/config.py` |
| 6 | P2 | Command overrides are interpolated into task YAML unserialised, so `echo "a: b"` parses as a mapping. | `tasks/templates/tasks/*.yml.j2` |
| 7 | P2 | `PYTEST_ARGS` and `SUITE_ARGS` are built with `shlex.join` and then expanded unquoted, so `-m 'not slow'` splits into three arguments. | `devops/ci.py`, `tasks/templates/tasks/ci.yml.j2` |
| 8 | P2 | A custom `web_dir` changes the Nx project name the tasks assume, while `project.json` keeps `web`. | `node/scaffold.py`, `tasks/artifacts.py` |
| 9 | P2 | Fencing an unfenced `.importlinter` leaves its contracts outside the fence, so apply duplicates them. | `core/cycle.py` |
| 10 | P2 | Publish recovery treats any index hit for a version as complete, so a lost sdist upload is never retried. | `devops/github.py`, `devops/cli.py` |
| 11 | P3 | `commands.py` docstrings carry ADR references and design rationale, against the README's rule that docstrings hold only the contract. | `commands.py` |

## The v1 spec rewrite

Promoted on 2026-11-07 to [E18](../epics/E18-kiln-simplification/index.md), with
the owner's decisions of 2026-11-06. It acts on findings 2 and 8 for the specs,
and leaves the work-item model of finding 1 as it is.

## The 2026-11-10 code review

A second review, of `6b3549b`, re-checked findings 5, 7, 9 and 10 and the
defects above, and turned them into work in
[E18](../epics/E18-kiln-simplification/index.md):

- F18.5 to F18.9 are the behaviour-preserving half.
- F18.10 and F18.11 change behaviour.

Defects 1 and 9 are already fixed. Every other row still holds. The review also
found that `kiln-pin` is never run by doctor, and that `ci.yml` renders
`test-cloud`, `test-local` and `umbrella` jobs which `GENERATED_JOBS` does not
reserve.

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
1. Promote each major design into an architecture page (finding 8), then archive
   plans and history and trim closed stories and ADRs (finding 2). For v1, the
   specs and plans part is [E18](../epics/E18-kiln-simplification/index.md).

## Open questions for refinement

- Does the P1 suites-gate defect go into E15 now, given that it breaks
  ADR-0016's release-after-checks contract?

- Which findings become epics or features, and which are dropped?

- Does trimming the docs model reopen [ADR-0011](../../adr/ADR-0011.md) and
  [ADR-0013](../../adr/ADR-0013.md), or only the specs that build them?

- Does release-1 wait for any of this, given that other repositories adopt from
  the release-1 tag? A model that is trimmed after adoption has to be migrated
  in every adopter.
