# Specs

What kiln is made of and what is left to build. Read this before adding an epic,
starting a feature, or cutting a release. **Start here in a new session:** the
board says what is next; the epic says how; its ADRs say why.

## Board

### In progress

Nothing in flight.

### Scheduled

| Epic | Release | Next step |
| -- | -- | -- |
| [E3 — Realign the goldens and the canon](epics/E3-realign-goldens-and-canon/index.md) | [release-1](../releases/release-1/index.md) | **start here** — F3.2 and S3.4.1 can begin now; F3.1 follows F3.2; F3.3 waits on pykit; S3.4.4 waits on S4.1.4 |
| [E4 — The generator](epics/E4-generator/index.md) | [release-1](../releases/release-1/index.md) | **start here too** — S4.1.4, the checks-shape decision, can begin now; the rest waits on E3 |
| [E6 — Rebuild the repos](epics/E6-rebuild-the-repos/index.md) | F6.1 [release-1](../releases/release-1/index.md); F6.2 [release-2](../releases/release-2/index.md) | after E4 |
| [E5 — The web archetypes](epics/E5-web-archetypes/index.md) | [release-2](../releases/release-2/index.md) | gated on `rn-forge-fastapi` |

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

## Upstream work owned by pykit

pykit owns its own spec. What kiln needs from it is handed off in pykit's
`docs/plans/kiln-dependencies.md`; this table is only what kiln is waiting on.

| Work | pykit status | Blocks in kiln |
| -- | -- | -- |
| Phase A — stabilize commons Part C | done | — |
| Phase C — first tooling extraction (`4624bfe`) | done, revised by C.2 | — |
| Phase C.2, pykit half — defect fixes, the cli/tooling split, re-layout (`f59c40f`) | done | — |
| Phase C.3 — the tool lifecycle surface (`install/` + `[cli.lifecycle]`) | **not started** | [F3.3](epics/E3-realign-goldens-and-canon/F3.3-python-tool-is-a-tool.md), and through it E4 |
| `rn-forge-fastapi` | in progress | [E5](epics/E5-web-archetypes/index.md) |
| Release tags | triggered by the owner | [E7](epics/E7-pykit-release-pin-flip/index.md) |

## Order

```text
done:  E1 ─→ E2                                         (pykit: A ─→ C ─→ C.2)
now:   S4.1.4 checks-shape decision ─→ S3.4.4 ─────┐
       S3.4.1 reference ───────────────────────────┤
       F3.2 pins ─→ F3.1 port ─→ F3.3 tool ────────┴─→ S3.4.2 re-seed ─→ E3 done
                                  ↑ pykit C.3 (lifecycle)
then:  E3 ─→ F4.1 ─→ F4.2 ─→ F4.3 ─┬─→ F4.4 matrix (goldens leave git) ─┐
                                   ├─→ F4.5 CLI ─→ F4.6 doctor ─────────┼─→ F4.8 self-host ─→ F6.1 pykit skeleton
                                   └─→ F4.7 contracts ──────────────────┘
                                       (S4.5.5 also needs pykit C.3)
       E4 + rn-forge-fastapi (pykit) ─→ F5.1 ─→ F5.2 ─┬─→ F5.3 ─→ E5 done
                                                      └─→ F6.2 retire taskkit
triggered: E7 pykit releases (owner) · E8 ADO · backlog: E10 generators
```

F3.2, S3.4.1 and S4.1.4 can start immediately, alongside pykit C.3. The
**Depends on** column on each epic and line on each feature are normative; this
diagram summarizes them. Nothing in E4 waits on a pykit release
([ADR-0005](../adr/0005-archetypes.md)), but every template renders the rn-forge
dependency source from config, so flipping to tags later is a config change, not
a template change.

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
  error in `cmd` itself — a missing path, say — into a pass.
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
- **Open questions live on the feature or epic they block.** Answered, a
  question becomes an [ADR](../adr/index.md), or a rejected option recorded on
  the feature; it is not left open on the page.
- **Why things are the way they are** — the evidence, the harvest, what each
  review changed — is [context](../plans/context.md). The original
  standardization plan is retired at revision 14 and survives only in git
  history; context §2 maps every part of it to its home here.
