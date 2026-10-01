# Specs

What kiln is made of and what is left to build. Read this before adding an epic,
starting a feature, or cutting a release. **Start here in a new session:** the
board says what is next; the epic says how; its ADRs say why.

## Board

### In progress

| Epic | Release | Next step |
| -- | -- | -- |
| [E4 — The generator](epics/E4-generator/index.md) | [release-1](../releases/release-1/index.md) | F4.1–F4.3 (apart from S4.3.6's Sonar decisions) and S4.5.1–S4.5.6 and S4.5.9 are done, as is E5's S5.3.6. Next are E13, then E11's F11.1–F11.3 and E12's F12.1, then F4.4, and the rest of F4.5–F4.8, including S4.6.5's ownership alignment |
| [E5 — The web archetypes](epics/E5-web-archetypes/index.md) | [release-2](../releases/release-2/index.md) | FastAPI/Angular scaffolding exists; the owner trial's setup and formatting gaps are closed (S5.3.5–S5.3.6). S5.2.4, S4.5.9, S5.3.5 and S5.3.6 are done. Next are the two FastAPI cells, after F4.4; Django is deferred |
| [E11 — Package docs sites](epics/E11-package-docs/index.md) | [release-1](../releases/release-1/index.md), [release-2](../releases/release-2/index.md) | after E13: F11.1's check changes, then the `python-lib` golden (S11.2.1); S11.4.2 after S13.3.1; F11.5 waits on its entry criterion |

### Scheduled

| Epic | Release | Next step |
| -- | -- | -- |
| [E6 — Rebuild the repos](epics/E6-rebuild-the-repos/index.md) | [release-1](../releases/release-1/index.md), [release-2](../releases/release-2/index.md) | prove `python-lib` can host pykit after F11.1–F11.3 |
| [E13 — The docs work model and derived regions](epics/E13-docs-work-model/index.md) | [release-1](../releases/release-1/index.md) | the owner accepting ADR-0003's revision, [ADR-0011](../adr/ADR-0011.md) and [ADR-0012](../adr/ADR-0012.md); then S13.1.1's derived nav, F13.2, F13.3 — before F11.1 |
| [E12 — The architecture baseline](epics/E12-architecture-baseline/index.md) | [release-1](../releases/release-1/index.md), [release-2](../releases/release-2/index.md) | S12.1.1, the owner accepting [ADR-0010](../adr/ADR-0010.md) and the Python records; then S12.1.2–S12.1.4, before F4.4 |

### To elaborate

Nothing agreed without stories.

### Deferred

| Epic | Entry criteria |
| -- | -- |
| [E7 — pykit releases, and the pin flip](epics/E7-pykit-release-pin-flip/index.md) | pykit's release-1 tags exist |
| [E8 — The Azure DevOps CI provider](epics/E8-ado-provider/index.md) | a repo needs `ci.provider = "ado"` |
| [E9 — The node archetypes](epics/E9-node-archetypes/index.md) | a repo in scope needs the node toolchain |
| [E10 — kiln generators](epics/E10-kiln-generators/index.md) | release-1 has shipped; to be elaborated (`kiln generate package` for `python-lib` moved to E11) |

Work outside kiln's releases is a standalone plan, not an epic: agent
configuration and intellibuild — see [plans](../plans/index.md).

### Done

| Epic | Implemented |
| -- | -- |
| [E1 — The canon and the hand-authored golden repos](epics/E1-canon-and-golden-repos/index.md) | 2026-09-09 |
| [E2 — The layer split lands in the goldens](epics/E2-layer-split-and-golden-rename/index.md) | 2026-09-12 |
| [E3 — Realign the goldens and the canon](epics/E3-realign-goldens-and-canon/index.md) | 2026-09-15 |

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
   the list — and flip its **Status** to `done (<date>)`. Leave the feature's
   `## Acceptance` block for the owner.
1. Commit nothing. The owner reviews the diff and the tests, runs the acceptance
   block, and commits.

## Conventions

- **Taxonomy.** Epic `E<n>` → feature `F<n>.<m>` → story `S<n>.<m>.<k>`. The
  prefix chain locates a bare ID without a lookup. IDs are permanent.
- **Status lives on the work.** Epics, features and stories each carry a
  `**Status:**` line — `planned`, `in progress`, `done`. A release page's
  scope table mirrors its features' status, updated in the same commit. This
  board is the index of the epics' status, never a second copy.
- **A story is done when its acceptance holds.** Each story carries an
  `**Acceptance:**` list of observable results. The tests that prove its
  behaviour belong in that list, never in a story of their own, so no story
  can read done before its behaviour is proven. A story is sized so its
  acceptance can be verified on its own.
- **A feature states its dependencies and its acceptance.** `**Depends on:**`
  names features, stories and upstream work. A decision the feature needs is
  its own story, so work can depend on the decision without depending on its
  implementation. A feature with several stories has a `## Acceptance` block
  that exercises every story, each line tagged with the story it proves; what
  cannot be scripted — an approval, a recorded decision — is listed under the
  block.
- **Acceptance blocks fail loudly.** They start with `set -euo pipefail`, and a
  failure is never turned into output (`|| echo`). A negative check uses the
  `absent` or `fails_with` helper defined at the top of the block, never a
  bare `! cmd`: `set -e` ignores a negated command, and `!` also turns an
  error in `cmd` itself — a missing path, say — into a pass. A line that greps
  a command's output never pipes into `grep -q` or `rg -q`: those exit on the
  first match, the writer takes a SIGPIPE, and `pipefail` then fails the line
  although the check passed. Let the grep read to the end and send its own
  output to `/dev/null`.
- **Releases pick features; they link here.** A release page's scope table names
  each feature once, linked to its file, with its status. A feature belongs to
  one release at a time; moving it edits only the two release pages.
- **Done work still has an epic**, marked `done` with its `**Implemented:**`
  date and its acceptance as run. There is no build log.
- **The backlog is a parking lot.** An idea not yet agreed as work is a row in
  `backlog.md`, with no ID and no status, until the owner takes it up as an
  epic or feature. Agreed work that is not ready is a deferred epic with entry
  criteria; promoting one: flip to `elaborating`, write its stories, then
  `planned` with a release.
- **Design lives with the work** — a `## Design` section on the feature, or the
  epic's `design.md`. Current behaviour belongs in
  [architecture](../architecture/index.md), the normative standard in
  [the reference](../reference/standard-repo.md).
- **Decisions are ADRs**, one durable choice per file. Keep delivery history and
  implementation detail in specs; see [the log](../adr/index.md).
- **Open questions live on the feature or epic they block.** Answered, a
  question becomes an [ADR](../adr/index.md), or a rejected option recorded on
  the feature; it is not left open on the page.
- **Why things are the way they are** — the evidence, the harvest, what each
  review changed — is [context](../plans/context.md). The original
  standardization plan is retired at revision 14 and survives only in git
  history; context §2 maps every part of it to its home here.
