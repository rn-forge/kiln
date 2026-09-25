# Specs

What kiln is made of and what is left to build. Read this before adding an epic,
starting a feature, or cutting a release. **Start here in a new session:** the
board says what is next; the epic says how; its ADRs say why.

## Board

### In progress

| Epic | Release | Next step |
| -- | -- | -- |
| [E4 — The generator](epics/E4-generator/index.md) | [release-1](../releases/release-1/index.md) | F4.1–F4.3 and the thin CLI needed by E5 are done. Build S4.5.9 after S5.2.4, then resume at F4.4 and finish F4.5–F4.8, including S4.6.5 ownership alignment |
| [E5 — The web archetypes](epics/E5-web-archetypes/index.md) | [release-2](../releases/release-2/index.md) | FastAPI/Angular scaffolding exists; the owner trial exposed remaining setup and formatting gaps (S5.3.5–S5.3.6). Next is S5.2.4's frontend-module split, staged generation and those fixes before the two FastAPI cells; Django is deferred |

### Scheduled

| Epic | Release | Next step |
| -- | -- | -- |
| [E6 — Rebuild the repos](epics/E6-rebuild-the-repos/index.md) | F6.1 [release-1](../releases/release-1/index.md); F6.2 [release-2](../releases/release-2/index.md) | build the pykit candidate after S5.3.1; cut over after F4.8 |

### To elaborate

Nothing agreed without stories.

### Deferred

| Epic | Entry criteria |
| -- | -- |
| [E7 — pykit releases, and the pin flip](epics/E7-pykit-release-pin-flip/index.md) | the owner declares pykit stable |
| [E8 — The Azure DevOps CI provider](epics/E8-ado-provider/index.md) | a repo needs `ci.provider = "ado"` |
| [E9 — The node archetypes](epics/E9-node-archetypes/index.md) | a repo in scope needs the node toolchain |
| [E10 — kiln generators](epics/E10-kiln-generators/index.md) | release-1 has shipped; to be elaborated |

Work outside kiln's releases is a standalone plan, not an epic: agent
configuration and intellibuild — see [plans](../plans/index.md).

### Shipped

| Epic | Shipped |
| -- | -- |
| [E1 — The canon and the hand-authored golden repos](epics/E1-canon-and-golden-repos/index.md) | 2026-09-09 |
| [E2 — The layer split lands in the goldens](epics/E2-layer-split-and-golden-rename/index.md) | 2026-09-12 |
| [E3 — Realign the goldens and the canon](epics/E3-realign-goldens-and-canon/index.md) | 2026-09-15 |

## Upstream work owned by pykit

pykit owns its own spec. What kiln needs from it is handed off in pykit's
`docs/plans/kiln-dependencies.md`; this table is only what kiln is waiting on.

| Work | pykit status | Blocks in kiln |
| -- | -- | -- |
| Phase A — stabilize commons Part C | done | — |
| Phase C — first tooling extraction (`4624bfe`) | done, revised by C.2 | — |
| Phase C.2, pykit half — defect fixes, the cli/tooling split, re-layout (`f59c40f`) | done | — |
| Phase C.3 — the tool lifecycle surface (`install/` + `[cli.lifecycle]`, `757908e`) | done | — |
| commons Part G — strict pydantic models as the `pydantic` extra | done | — |
| `rn-forge-fastapi` | implemented (`3e80dbd`); its Phase 8 is a wired app, repo-owned | — |
| Resolvable web pins: tags `rn-forge-commons-v0.5.0` and `rn-forge-web-v0.1.0`, or `feature/upgrade` pins on web, django and fastapi | not done (2026-09-16) | [E5](epics/E5-web-archetypes/index.md): `uv sync` of any web cell |
| `rn-forge-cli` — optional `namespace` on `[cli.lifecycle]` (`docs/plans/cli-lifecycle-namespace-plan.md`) | planned (2026-09-21); the owner confirms when it lands | [S4.5.5](epics/E4-generator/F4.5-cli.md#s455-lifecycle-wiring): mount the verbs as `kiln self …` |
| Release tags | triggered by the owner | [E7](epics/E7-pykit-release-pin-flip/index.md) |

## Order

```text
done:  E1 ─→ E2 ─→ E3 ─→ F4.1 ─→ F4.2 ─→ S4.3.1–S4.3.5        (pykit: A ─→ C ─→ C.2 ─→ C.3)
done:  F5.1 ─→ F5.2 fastapi ─→ S5.3.1 fresh-repo gate fixes
       (Django S5.2.3 deferred; live sync still needs resolvable pykit pins)
now:   S5.2.4 frontend module ─→ S4.5.9 staged `new`
then:  S5.3.5–S5.3.6 owner-trial fixes (before shipped-cell proofs)
       F4.4 matrix (goldens leave git) ─┬─→ S5.3.2–S5.3.4 ─→ E5 done
       S5.3.1 ─→ S6.1.1 pykit candidate │
       S4.5.3–S4.5.7 ─→ F4.6 doctor ────┼─→ F4.8 self-host ─→ S6.1.2 pykit cutover
       F4.7 contracts ──────────────────┘   F6.2 retire taskkit (after S4.6.2, S5.2.2)
       (S4.5.5 also needs pykit C.3)
triggered: E7 pykit releases (owner) · E8 ADO · backlog: E10 generators
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
- **Status lives on the story.** A feature file holds its stories, each with a
  `**Status:**` line — `planned`, `in progress`, `done`. The epic index
  carries the epic's status and ship date; this board is the index of those,
  never a second copy.
- **A story is done when its acceptance holds.** Each story carries an
  `**Acceptance:**` list of observable results. The tests that prove its
  behaviour belong in that list, never in a story of their own, so no story
  can read done before its behaviour is proven. A story is sized so its
  acceptance can be verified on its own.
- **A feature states its dependencies and its acceptance.** `**Depends on:**`
  names features, stories and upstream work. A decision the feature needs is
  its own story, so work can depend on the decision without depending on its
  implementation. A `## Acceptance` block exercises every story, each line
  tagged with the story it proves; what cannot be scripted — an approval, a
  recorded decision — is listed under the block.
- **Acceptance blocks fail loudly.** They start with `set -euo pipefail`, and a
  failure is never turned into output (`|| echo`). A negative check uses the
  `absent` or `fails_with` helper defined at the top of the block, never a
  bare `! cmd`: `set -e` ignores a negated command, and `!` also turns an
  error in `cmd` itself — a missing path, say — into a pass. A line that greps
  a command's output never pipes into `grep -q` or `rg -q`: those exit on the
  first match, the writer takes a SIGPIPE, and `pipefail` then fails the line
  although the check passed. Let the grep read to the end and send its own
  output to `/dev/null`.
- **One home per story; releases link.** A release page names its scope by story
  ID and links here. Moving a story between releases edits only release pages.
- **Shipped work still has an epic**, marked `done` with its ship date and its
  acceptance as run. There is no build log.
- **The backlog is deferred epics**, each with entry criteria. Promoting one:
  flip to `elaborating`, write its stories, then `planned` with a release.
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
