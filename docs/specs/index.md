# Specs

What kiln is made of and what is left to build. Read this before adding an epic,
starting a feature, or cutting a release. **Start here in a new session:** the
board says what is next; the epic says how; its ADRs say why. The Releases and
Backlog sections below are derived from the epic, feature and release pages by
`task docs:generate`; never edit inside their fence.

<!-- BEGIN derived board -->

## Releases

| Release | Status | Features |
| -- | -- | -- |
| [Release 2 — the web archetypes](../releases/release-2/index.md) | in progress | 1 Active · 3 New · 2 Closed |
| [Release 1 — kiln generates and self-hosts the Python archetypes](../releases/release-1/index.md) | in progress | 3 Active · 7 New · 11 Closed |
| [Release 0 — the canon and the hand-authored goldens](../releases/release-0/index.md) | shipped (2026-09-12) | — |

## Backlog

Features with no Iteration, by State and epic.

### New

| Epic | Features |
| -- | -- |
| [E2 — The layer split lands in the goldens](epics/E2-layer-split-and-golden-rename/index.md) | F2.9 |

### Deferred

| Epic | Features | Entry criteria |
| -- | -- | -- |
| [E7 — pykit releases, and the pin flip](epics/E7-pykit-release-pin-flip/index.md) | — | pykit's release-1 tags exist. Cutting them, and their order, is pykit's work (ADR-0009) |
| [E8 — The Azure DevOps CI provider](epics/E8-ado-provider/index.md) | — | a repo needs `ci.provider = "ado"`. The intellibuild plan holds the question of whether intellibuild is that repo |
| [E9 — The node archetypes](epics/E9-node-archetypes/index.md) | — | a repo in scope needs a second toolchain — pnpm release, node CI, no uv |
| [E10 — kiln generators](epics/E10-kiln-generators/index.md) | — | release-1 has shipped and the owner picks this up for elaboration |

<!-- END derived board -->

Ideas not yet agreed as work are parked in the [ideas list](ideas.md).

## Upstream pins

What kiln needs from other repositories, stated as what kiln can observe from
outside them ([ADR-0009](../adr/ADR-0009.md)). Their own plans and status are
theirs.

| Pin | Needed by | Observed |
| -- | -- | -- |
| Every pykit package kiln renders resolves from `feature/upgrade` outside the pykit workspace | [E5](epics/E5-web-archetypes/index.md): `uv sync` of any web cell | not yet (2026-09-26): a web cell's `uv sync` does not resolve |
| pykit's release-1 tags exist | [E7](epics/E7-pykit-release-pin-flip/index.md) | not yet |
| pykit's default branch publishes versioned package sites under `https://rn-forge.github.io/pykit/packages/` | [S11.5.1](epics/E11-package-docs/F11.5-deploy-package-sites.md#s1151-ci-deploys-versioned-package-sites) | not yet |

## Order

```text
done:  E1 ─→ E2 ─→ E3 ─→ F4.1 ─→ F4.2 ─→ S4.3.1–S4.3.5 ─→ S4.5.1–S4.5.6
done:  F5.1 ─→ F5.2 fastapi ─→ S5.2.4 frontend module ─→ S4.5.9 staged `new` ─→ S5.3.1 fresh-repo gate fixes ─→ S5.3.5 quality commands ─→ S5.3.6 setup experience
       (Django S5.2.3 deferred; live sync still needs resolvable pykit pins)
now:   ADRs accepted ─→ S13.1.1 derived nav ─→ F13.2 board/scope ─→ F13.3 adopt the model
       F11.1 checks ─→ F11.2 python-lib package sites ─→ F11.3 generate package   (S11.4.2 after S13.3.1)
       S12.1.1 accept ─→ S12.1.2–S12.1.4 baseline ─→ F4.4 · F12.1 ─→ F12.2 web records (release-2)
       F4.4 matrix (goldens leave git; python-lib cell needs S11.3.1) ─┬─→ S5.3.2–S5.3.4 ─→ E5 done
       S5.3.1 + F11.1–F11.3 ─→ S6.1.1 python-lib hosts pykit          │
       S4.5.3–S4.5.7 ─→ F4.6 doctor ──────────────────────────────────┼─→ F4.8 self-host
       F4.7 contracts ────────────────────────────────────────────────┘   F6.2 retire taskkit (after S4.6.2, S5.2.2)
triggered: E7 pykit tags · E8 ADO · F11.5 package-site deploy · backlog: E10 generators
```

E3 shipped on 2026-09-15: every feature's acceptance block passes, S3.3.2's
normalized golden diff was reviewed, and the epic block re-proves the whole. E4
is under way. **Build order is not release order:** E5's first two features and
S5.3.1 are built before F4.4, because the owner's next repositories are web
repositories and those stories need neither the render matrix, the full doctor
nor self-hosting; release-1 still ships before release-2. The **Depends on**
column on each epic and line on each feature are normative; this diagram
summarizes them. Nothing in E4 waits on a pykit release
([E7](epics/E7-pykit-release-pin-flip/index.md)): the rn-forge dependency source
is one constant
([S4.3.7](epics/E4-generator/F4.3-concern-modules.md#s437-the-scaffold-completes-pyprojecttoml)),
so flipping to tags later is a one-line change, not a template change.

## Building a story

One story per session, from a fresh context. The story is the whole brief;
nothing outside it and the files it names is assumed. This is written for
whoever builds the story — a person, or an agent of any size.

1. Read `README.md`, then this page's conventions, then the feature page top to
   bottom. Read every file the story's **Build** list names, and every golden
   file it says to diff — with `diff`, never by eye. Read the tests of the
   nearest `done` story in the same feature: they are the shape to copy.
1. Write the tests first, in the file the story names, named
   `test_<story id with underscores>_<what>` — `test_s4_3_3_property1_…` for
   the shared properties, `test_s4_3_3_2_…` for the story's second acceptance
   bullet. Every acceptance bullet has at least one test, or is listed as not
   scriptable.
1. Build exactly what the **Build** list says. Where it names a file, a
   function, a constant, a code, a template or a context key, use that name
   verbatim. Where it is silent, do the simplest thing that makes the tests
   pass, and write the choice down.
1. Do not: edit a golden repo unless the story says so; add a dependency; change
   another module; change the module contract; shell out from anything but a
   `scaffold` function; add a check, a flag, an option or a config key the
   story does not list; skip a test the story does not allow to skip.
1. Run `task validate`. It passes, with no failure and no skip the story did not
   allow. If a golden had to change, re-seed its `state.json` as `README.md`
   says.
1. Record under the story, as *What the build settled that the story did not
   say*, every choice from step 3 and every place the build had to depart from
   the list — and flip its **State** to `Closed (<date>)`. Leave the feature's
   `## Acceptance` block for the owner.
1. Commit nothing. The owner reviews the diff and the tests, runs the acceptance
   block, and commits.

## Conventions

- **Taxonomy.** Epic `E<n>` → feature `F<n>.<m>` → story `S<n>.<m>.<k>`. The
  prefix chain locates a bare ID without a lookup. IDs are permanent: a moved
  story keeps its ID, and gaps are fine.
- **Every piece of work is an epic**, closed work included. There is no build
  log.
- **State lives on the work.** Epics and features carry `State` in a metadata
  table, stories on a `**State:**` line: `New`, `Active`, `Closed` or
  `Removed`. The board above is derived from them, never a second copy.
- **A feature's `Iteration` is its release.** A release page's Scope table is
  derived from it, so moving a feature edits only the feature.
- **A story is closed when its acceptance holds.** Each story carries an
  `**Acceptance:**` list of observable results, and the tests that prove it
  belong in that list.
- **A feature states its predecessors and its acceptance**: a `Predecessors`
  row, and, when it has several stories, a `## Acceptance` block that
  exercises every story and fails loudly.
- **Ideas are a parking lot.** An idea not yet agreed as work is a row in
  `ideas.md`, with no ID and no state. Agreed work that is not ready is tagged
  `deferred`, with entry criteria.
- **Design lives with the work** — a `## Design` section on the feature, or the
  epic's `design.md`. Current behaviour belongs in
  [architecture](../architecture/index.md).
- **Decisions are ADRs**, one file per topic, revised in place with a dated line
  under `## Background` when they change — see [the log](../adr/index.md).
- **Open questions live on the feature or epic they block.** Answered, a
  question becomes an ADR or a rejected option recorded on the feature, and
  leaves the page.
- **Why things are the way they are** — the evidence, the harvest, what each
  review changed — is [context](../plans/context.md). The original
  standardization plan is retired at revision 14 and survives only in git
  history; context §2 maps every part of it to its home here.
