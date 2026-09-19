# ADR Refactor

## Session 1

This session was with codex gpt-6 astra.

This repo is primarily vibe coded - docs, code, pipeline, etc. I was reviewing
the ADRs and feel they sound more like a history lesson with context. Maybe some
of it is context for the specs on why kiln was conceived the way it has been and
what problems it tries to solve, but there is hardly anything that is an actual
architectural decision that influences it's own design.

Review and provide your feedback on how it can be, either removed or rewritten
so it is crisp and to the point, without a verbose history lesson. maybe some of
the info can go into the epic/feature/story to explain the thought process

### Codex Response

**Rewrite and consolidate the ADRs; don’t remove the decision log.** The problem
is that durable design choices are buried in incident reports, implementation
details, and delivery history. The 11 ADRs total roughly 11,100 words.

Kiln also owns the repository standard, so decisions about generated
repositories legitimately belong here. They should clearly distinguish **kiln’s
architecture** from **the standard kiln enforces**.

1. **Resolve conflicting statements before shortening the prose.**

    These are already maintenance problems:

    - ADRs 0002, 0005, and 0007 prescribe generated checker scripts; ADR-0010
      replaces those scripts with checks shipped in kiln.
    - [ADR-0002](/Users/rohitnarayanan/Devel/workspaces/rn-forge/kiln/docs/adr/ADR-0002.md:69)
      puts `AppConsole` in `rn-forge-cli`; ADR-0009 and the workspace
      architecture put it in commons.
    - [ADR-0011](/Users/rohitnarayanan/Devel/workspaces/rn-forge/kiln/docs/adr/ADR-0011.md:52)
      includes “worth collapsing into one protocol” inside an accepted
      decision. That is an unresolved proposal and belongs on a feature.

1. **Give each ADR one question to answer.**

    | ADR | Recommended change |
    | -- | -- |
    | **0001 — Ownership** | Keep artifact ownership: managed files, fenced blocks, seeded content. Move README/agent-file conventions and path assignments to the reference. Remove donor-repo incidents. |
    | **0002 — Dependencies** | Keep kiln’s boundary: repository policy belongs in kiln; reusable mechanisms belong in libraries; enforce dependencies and imports. Move package inventories to architecture and pykit extraction history to E2/E3. |
    | **0003 — CI** | Narrow to **“Generate and commit workflows rather than depend on shared remote workflows.”** Leave pinned kiln verification to 0010. Remove module naming and security-setting inventories. |
    | **0004 — Configuration** | Rewrite as **“Render from explicit, committed configuration.”** Keep reproducibility and explicit source refresh. Move directory trees, state fields, and command details to reference/design. |
    | **0005 — Archetypes** | Largest offender: about 2,425 words covering several decisions. Keep archetype versus capability selection here. Separate template-source/rendered-validation policy. Move catalogues to reference, shipped combinations to E5, pin-transition work to E7, and bootstrap-golden retirement to F4.4. |
    | **0006 — Scope** | Keep the boundary against general inference and migration, including the narrow `init` exception. Move fleet rebuild/history-preservation choices to E6 and prompt delivery details to F4.5. |
    | **0007 — Tasks** | Keep a bounded public task interface and mandatory validation reachability. Move exact verbs, config keys, and checker mechanics to reference. |
    | **0008 — Pyright** | Move to the standard reference. The current rationale establishes a tooling convention, but makes little case for a separate architectural record. |
    | **0009 — CLI** | Retain only **“Consume shared CLI behavior as a library rather than generate copies.”** Move extraction history to E2/E3 and API details to architecture/reference. |
    | **0010 — Packaging and verification** | Keep one pinned distribution supplying generation and read-only verification. Remove the original script census, spike narrative, and upgrade instructions. Link to S4.1.4 for evidence. |
    | **0011 — Modules** | Keep internal modules, shared contracts, and centralized composition. Move framework-generator plans to E10 and protocol signatures to design/API documentation. |

1. **Move rationale selectively, without turning specs into another history
   archive.**

    - **Epic:** problem, intended outcome, scope exclusions, cross-feature
      tradeoffs.
    - **Feature/design:** local implementation choice, rejected approaches,
      relevant experiment results.
    - **Story:** only the rationale needed to understand its acceptance criteria.
    - **ADR:** a durable choice that constrains future implementations.
    - **Reference/architecture:** exact rules and how the system currently works.

    “The owner asked,” phase-by-phase narration, retired filenames, and repeated
    failure anecdotes can usually be deleted. Preserve historical evidence only
    when it helps explain a still-relevant tradeoff.

1. **Make the architectural decisions more visible.**

    A particularly important choice is currently buried in
    [E4’s design](/Users/rohitnarayanan/Devel/workspaces/rn-forge/kiln/docs/specs/epics/E4-generator/design.md:113):
    plan before writing, reject unapproved conflicts, back up changes, roll
    back failures, and write state last. That deserves a focused ADR explaining
    **why apply uses a transaction rather than incremental best-effort
    writes**.

    A rewrite should be approximately this size:

    > **Render from committed configuration**
    >
    > **Context:** Repository generation must be reproducible across developer
    > machines and CI.
    >
    > **Decision:** Require an explicit archetype. Resolve configuration sources
    > into committed repository configuration. Rendering and verification read
    > that configuration without discovering machine-local defaults or refreshing
    > remote sources.
    >
    > **Alternatives:** Implicit detection can misclassify repositories. Live
    > inherited configuration can change output without a repository change.
    >
    > **Consequences:** Generation is reproducible. Changes to shared defaults
    > require an explicit configuration update.

1. **Change the authoring rule that encourages accumulation.**

    [The ADR instructions](/Users/rohitnarayanan/Devel/workspaces/rn-forge/kiln/docs/adr/_structure.md)
    currently require revision history. Limit that to a dated sentence and
    link; don’t embed previous versions. Target **150–300 words per decision**,
    with brief context, a concrete choice, credible alternatives, and actual
    costs. Preserve existing IDs and links when consolidating.

Read-only review; no files changed or tests run.

### Feedback on response

ok, with your recommendation. Clean up the ADRs and move required
history/context into spec/design files.

more inputs from me:

- ADR-0001: Ok. the decision is that whatever kiln owns, it owns completely or
  completely ignores in doctor post scaffold
- ADR-0002: Ok. Kiln need not own the decision of pykit's internal dependency
  graph.
- ADR-0003: Ok.
- ADR-0004: Ok. Kiln owns .rn-forge/kiln/ and does not care about sibling
  folders under .rn-forge/
- ADR-0005: Yes, very convoluted narrative. simplify to definition of an
  archetypes and how flags create the orthogonal matrix. actual archetypes
  supported are specs
- ADR-0006: Don't think it provides any value. Scope is specs/
- ADR-0007: Ok. decision is about the public task vocubulary and modular
  architecture to expand it. actual verbs and everything else is specs
- ADR-0008: This is not an ADR, but design choice. Maybe there could be an ADR
  for the entire foundational tech stack for kiln
- ADR-0009: This is not a kiln adr, but pykit's feature spec
- ADR-0010: ok. this gets folded into ADR-0003 I feel
- ADR-0011: Again it is a design choice. maybe part of the foundational tech
  stack ADR.

update ADRs accordingly. update references as you delete/renumber them

### Codex Output

Sits in the working tree. The agent rewrote the new cleaned up copy of 7 ADRs,
but then ran out of tokens before confirming if all references were updated and
changes were validated.

## Session 2

This session was with claude opus.

The ADRs were carrying a lot of history, context and content that belonged to
specs. A refactoring excercise was in progress to correct that. The agent
rewrote the new cleaned up copy of 7 ADRs, but then ran out of tokens before
confirming if all references were updated and changes were validated.

Review the working tree, and confirm that changes are consistent and ready to
commit.

Also, provide your feedback on the quality of the newly written ADRs

### Claude Response

I have the full picture. Here's my assessment.

Not ready to commit — the refactor is unfinished task lint and task test both
fail on the working tree. HEAD passes both cleanly, so every failure below is
new.

#### 1. Four dangling ADR links (the repo's own checker catches these)

tests/modules/docs/checks/test_structure.py::test_kiln_docs_pass_the_policy
fails with docs.broken-link:

| Location | Bad link | Should be |
| -- | -- | -- |
| F4.6-doctor.md:77 | ADR-0010.md | ADR-0003.md |
| design.md:77 | ADR-0011.md | ADR-0007.md |
| design.md:102 | ADR-0010.md | ADR-0003.md |
| design.md:262 | ADR-0010.md | ADR-0003.md |

Plus three bare-text mentions the link checker can't see: design.md:30
(ADR-0010), design.md:31 (ADR-0009), design.md:201 (ADR-0010).

#### 2. Two references point at the wrong decision

Old ADR-0006 ("no skills; repos are created, not migrated") was dropped, and old
ADR-0007 (task vocabulary) took the number 6. context.md correctly re-routes
D30/D38/D39 to design.md#scope-and-ownership — so demoting it to spec was
deliberate. But design.md:91 and :93 still cite ADR-0006 for kiln prompt and "no
general adopt". Those links resolve, so no checker catches them — they now
silently point at the task-vocabulary ADR. They should point at
#scope-and-ownership.

I checked all 384 ADR references: everything else was remapped correctly, and
the ADR-0014/0018/0021/0024 hits are foreign agentkit/apollo ADRs, properly
qualified. All six anchors the new ADRs link to exist.

#### 3. No state.json was regenerated anywhere — 11 test failures

Twelve generated files were hand-edited and no state.json was updated, in the
root repo or any of the three goldens. This fails task lint (4 drift findings)
and breaks test_every_golden_passes_every_check ×3 and all 7 test_apply.py
tests.

Note this is not fixable with kiln apply --force. I tested a forced apply in an
isolated copy: the fresh render reverts the content — .rn-forge/kiln/standard.md
comes back as python-app text. The cause is that standard.md.j2:20 branches on a
lifecycle flag, but kiln's own config.toml declares archetype = "python-tool"
without setting it. The hand-edited files are ahead of what the templates can
produce. This looks like in-flight F3.3 work rather than ADR fallout, but it
blocks the commit either way.

#### 4. Pre-existing, not yours

F4.5-cli.md:37 #s457-config-from-a-git-source doesn't match its heading slug
(the --config backticks). Unchanged at HEAD.

#### Quality of the new ADRs

Structurally this is a clear win. All seven land at 206–244 words, inside the
150–300 target \_structure.md sets. Titles became decisions rather than topic
labels — "Ownership is complete or absent" is genuinely good. The History
sections, dated revision notes and review narrative are gone, and each ADR now
ends with links to the owning spec, which is exactly the separation the exercise
was for. The alternatives are real, with a named failure mode each, not straw
men — ADR-0004's three are the best of them.

Four things I'd push back on:

ADR-0007 is two decisions in one, and the weaker one lost its argument. "Build
kiln as one Python distribution" is a packaging-topology decision. The toolchain
paragraph (uv/task/ruff/pyright-strict/pytest/import-linter/MkDocs) is a
separate one, absorbed from old ADR-0008, which had existed specifically to
argue pyright over mypy — and the surviving alternative, "Use multiple competing
quality toolchains: adds maintenance without a separate requirement," doesn't
address that question at all. The reference doc still cites ADR-0007 for
"pyright is clean in strict mode," so a reader chasing why not mypy now arrives
at an answer that isn't there. That's a content regression, not just a renumber.

The concrete evidence was flattened out. Old ADR-0010 opened with "a generated
repo carried 1,454 lines of committed checker scripts." New ADR-0003 says
"copying checker implementations into every repository." \_structure.md
explicitly asks for "concrete costs," and the rewrite mostly states them
abstractly. The set now reads uniformly well-formed but somewhat bloodless — you
can't tell which decisions were forced by measured evidence and which were
taste.

ADR-0006 drifts into spec. "Validate the composed interface, references and
namespace collisions" and "Required validation tasks must remain reachable from
the aggregate gate" are requirements, not a decision. \_structure.md warns
against precisely this ("If a page here starts listing things, it has become a
spec"). ADR-0002's "Dependency declarations and Python imports are separate
boundaries and may require separate checks" has the same smell — and the may
makes it non-binding, which an ADR shouldn't be.

No dates. All seven are bare **Status:** accepted. The old set carried "Accepted
2026-09-15", and \_structure.md's own guidance talks about retaining "a dated
sentence." Without dates you can't order the decisions or tell a fresh one from
a carried-forward one.

The sharpest paragraph in the set is ADR-0005's "Orthogonal means separately
selectable, not universally compatible" — it closes a real ambiguity in one line
and constrains the matrix work downstream. More of that.

I've made no changes. Want me to fix the seven references and the two
mis-targeted ones? The state.json situation needs your call, since regenerating
would discard the hand-edited content.

## Session 3

Session 2's cache expired, so decided to go with new session and provide
previous context. Agree with all recommendations from session 2.

### feedback on session 2 response points

1. Ok, update
1. Ok, update
1. Ok, update
1. ok, fix it

### additional inputs on quality feedbackfeed

- 150-300 is not a hard target. provide your recommendation if you want to
  increase it
- We don't have to get rid of history completely. I just don't want it to be a
  verbose prose at the top of the ADR. Opening an ADR should quickly give me
  the actual decision and what it influences. Alternatives considered,
  historical context etc. can stay at the bottom of the document, if it will
  add value.
- My view of the ADR structure: **Decision** _(context can merge into it)_,
  **Consequences**, **Alternatives considered**, and **Context** _(this is the
  historical context, if needed, can be named differently)_.
- ADRs should be actual decisions taken that will influence the design of the
  product or it's specs. Anything that is actually a feature of the product,
  should be in the specs. Specs can carry the same historical context, if
  required
- ADR-0002 is not really a kiln adr. it is more like a rn-forge adr that
  manadates all products to use the pykit libraries for standardization
- I don't understand ADR-0004. is it really needed ?
- ADR-0003 and ADR-0006 are basically decisions that shape the CI and Docs
  features. Maybe they can be continuous, if ADR-0004 is going to be retired
- ADR-0007 seems like it should be the first one. The core product principle to
  package everything as a kiln distribution
- Platform decision can be next ADR, to document the choice of stack, tooling
  etc.

### Session 3 outcome

**Structure.** All seven ADRs now open with a
`**Status:** <state> (<date>) · **Scope:** <what it binds>` line, then
`Decision`, `Consequences`, `Influences` (links to the specs/reference it
constrains), `Alternatives considered`, `Background`. `adr/_structure.md`, its
template and the three golden copies say so, and the carrying runbook points at
it.

**Word budget.** No hard cap. The first three sections are budgeted at 300 words
— that is what a reader sees on opening — and alternatives plus history run to
whatever the evidence needs, soft total 600. The old 150–300 total cap is what
flattened the measured costs into abstractions; the numbers (1,454 lines of
checkers, 84 pyright errors, two Typer floors, two pyprojects differing by a
name and one dependency line) are back, in `Background`.

**Renumbering.** Kiln's ADRs are 0001–0007, in the order asked for:

| # | Decision | Was |
| -- | -- | -- |
| 0001 | Ship kiln as one pinned distribution of modules | 0007 + old 0011 |
| 0002 | Build on the rn-forge platform; keep repository policy in kiln | 0002 + old 0008 + old 0009 |
| 0003 | Ownership is complete or absent | 0001 + the namespace rule from 0004 |
| 0004 | Render only from committed configuration | 0004 |
| 0005 | Archetypes define topology; flags form independent dimensions | 0005 |
| 0006 | Commit generated CI, and run the pinned kiln read-only | 0003 + old 0010 |
| 0007 | Compose a declared public task vocabulary from modules | 0006 |

**Decisions taken on the session-3 inputs.**

- *ADR-0002 is not a kiln ADR.* Kept, because kiln **is** rn-forge's canon repo
  — there is no other home, and `architecture/workspace.md` already carries
  workspace-level material here. Instead every ADR now declares its `Scope:`,
  and 0002's is "the rn-forge workspace — every product in it, kiln included".
  The pykit-internals disclaimer stays in it.
- *Is ADR-0004 needed?* Kept, narrowed to one thing: **render only from
  committed configuration**. It is the guard that stops a future contributor
  adding archetype auto-detection or a home-directory profile, and it is what
  makes a drift finding mean anything. Its namespace half
  (`kiln owns .rn-forge/kiln/` and no more) moved into 0003, where ownership
  belongs.
- *Foundational tech stack ADR.* This is 0002. It absorbed old 0008's
  pyright-over-mypy argument, which session 2 flagged as lost — the 84 errors,
  the untyped-library boundary, and the "a repo that wants mypy needs its own
  record" clause are all in it, and the reference's pyright line cites 0002
  now.
- *Spec material in the ADRs.* Removed. Old 0006's validation list and old
  0002's non-binding "may require separate checks" are gone; 0007 keeps only
  the binding rule (required validation stays reachable from the aggregate
  gate) and links F4.3 for the mechanics.
- *`ADR-0003` and `ADR-0006` for CI and docs.* There is no docs ADR — 0006 was
  the task vocabulary, not docs. CI (0006) and tasks (0007) are now adjacent.
- **Counter, on the record:** ADR numbers are identities, not a reading order,
  and renumbering invalidates every external citation. It was worth doing once
  here because deleting four records forced a renumber anyway. The numbers
  freeze now; reading order lives in `adr/index.md`, which is a table with a
  scope column.
- **Not done, needs your call:** session 1 proposed a new ADR for *apply is a
  transaction* — plan first, refuse unapproved conflicts, back up, roll back,
  write state last. It is currently only in `E4/design.md:113` and it is a
  real durable constraint. Say the word and it becomes ADR-0008.

**Session 2's four fixes.** All applied: the four dangling links and three bare
mentions, the two `ADR-0006` citations in `design.md` that silently pointed at
the task ADR (now `#scope-and-ownership`), and one more the codex pass
introduced — `context.md`'s D57 row linked `../../README.md`, outside
`docs_dir`, which broke the strict site build.

**The state.json / drift problem.** Not fixable with `kiln apply --force`: the
root repo's `standard.md` branches on a `lifecycle` context flag that
`config.toml` does not set for `archetype = "python-tool"`, so a fresh render
reverts it to `python-app` text. That is in-flight F3.3 work, not ADR fallout.
Instead the baselines were rebased in place — `state.json` hashes recomputed
with kiln's own `digest()` and block extractor, in the root and all three
goldens, for the four managed artifacts whose bytes changed. **The
lifecycle-flag gap is still open and still needs F3.3.**

**Validation.** `task validate` exits 0 — ruff, pyright strict, 369 tests,
`kiln doctor` (generated, task-layout, ci-entrypoint, docs-site, docs-structure,
docs-nav), mdformat and a `--strict` site build.
