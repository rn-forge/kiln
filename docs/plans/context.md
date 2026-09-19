# Context — how kiln got here

The prior context behind kiln's specs and decisions: the evidence, what was
harvested from the donor repos, what each review changed, the reasoning threads
that produced the later ADRs, and what was rejected along the way. Historical
review outcomes below are not current policy. Nothing here is a task — work is
in [the spec board](../specs/index.md) and decisions are in
[the ADR log](../adr/index.md).

It replaces two documents. The standardization plan
(`docs/plans/standardization-plan.md`) is retired at **revision 14**, and
`harvest.md` is merged in as §6. The plan remains an archived historical record;
its proposals are not current requirements. §2 maps every section, decision and
open question of the plan to its new home.

______________________________________________________________________

## 1. Scope

The plan covered repo structure, tooling ownership, and pipeline only — not
product code, test strategy, or runtime architecture.

Repos in kiln's scope: `rn-forge/pykit`, `rn-forge/kiln`. Built from their own
standalone plans: `walgreens/intellibuild` ([plan](intellibuild.md)) and agent
configuration ([plan](agent-config-future.md)). Parked: `rn-tools/apollo`,
`ngkit`, `shkit`, `macsetup`. Retired: `rn-forge/taskkit`.

| Repo | Branch | State (2026-09-12) | Note |
| -- | -- | -- | -- |
| `rn-forge/taskkit` | `feature/v1` | 34 staged | retired (D23) — donor for `validator.py` and fixtures |
| `rn-tools/apollo` | `feature/initial` | 13 dirty | parked (D40) |
| `walgreens/intellibench` | `feature/iteration-2` | 13 dirty | superseded by intellibuild (D41) — [plan](intellibuild.md) |

## 2. Where the plan went

### 2.1 Sections

| Plan section | Now |
| -- | -- |
| Header, revision summaries | §10 |
| §0 handoff note | [specs/index.md](../specs/index.md) conventions |
| §0.1 phase board | [specs/index.md](../specs/index.md) board |
| §0.1 on-disk state, repo state | [E3](../specs/epics/E3-realign-goldens-and-canon/index.md) starting state; §1 above |
| §0.2 component map | [architecture/workspace.md](../architecture/workspace.md#components) |
| §0.3 rebuild, not migrate | §3; decision in [Scope and ownership](../specs/epics/E4-generator/design.md#scope-and-ownership) |
| §0.4 name reassignment | §4; [E4 scope](../specs/epics/E4-generator/design.md#scope-and-ownership) |
| §0.5 not covered | §1 |
| §0.6–§0.9 review outcomes | §7 |
| §0.10–§0.11 scope-expansion thread | §8; decisions folded into [the decision log](../adr/index.md) |
| §1 findings | §5 |
| §2.1 dependency graphs | [architecture/workspace.md](../architecture/workspace.md#the-graphs) |
| §2.2 CI model | already covered by [ADR-0006](../adr/ADR-0006.md) and [reference §5](../reference/standard-repo.md#5-what-task-validate-proves) |
| §2.3 ownership rule | [ADR-0003](../adr/ADR-0003.md) |
| §2.4 ownership table | [F3.4 design](../specs/epics/E3-realign-goldens-and-canon/F3.4-canon-catches-up.md#ownership-table-normative-replaces-the-reference-2-table) (replaces the stale reference §2 table) |
| §2.5.1 package layout; §2.5.3 commands; §2.5.4 cycle; §2.5.5 apply sequence; §2.5.6 doctor checks | [E4 design](../specs/epics/E4-generator/design.md) |
| §2.5.2 config schema | already covered by [reference §9](../reference/standard-repo.md#9-configuration) |
| §2.6 archetypes, goldens, docs profile | [archetype catalogue](../reference/standard-repo.md#archetype-catalogue); [F4.4 render matrix](../specs/epics/E4-generator/F4.4-render-matrix.md); template inventory in [E4 design](../specs/epics/E4-generator/design.md#template-inventory) |
| §2.7 no docs migration | [Scope and ownership](../specs/epics/E4-generator/design.md#scope-and-ownership); the doctor note in [E4 design](../specs/epics/E4-generator/design.md#doctor-checks) |
| §2.8 pykit Part D and tooling extraction | pykit handoff (`rn-forge/pykit: docs/plans/kiln-dependencies.md`) |
| §2.9 tool lifecycle surface | [ADR-0005](../adr/ADR-0005.md); mechanism in the pykit handoff |
| §2.10 the canon inside kiln | already covered by [the ADR log's intro](../adr/index.md) and [the reference](../reference/standard-repo.md); its revision-6 ADR numbering table is historical and dropped |
| §2.11 package layout of the three libraries | pykit handoff |
| §3 Phase A, Phase C, Phase C.3 | pykit handoff; summarized on [the board](../specs/index.md#upstream-work-owned-by-pykit) |
| §3 Phase B | [E1](../specs/epics/E1-canon-and-golden-repos/index.md) |
| §3 Phase C.2 | [E2](../specs/epics/E2-layer-split-and-golden-rename/index.md) (kiln half) + pykit handoff |
| §3 Phase C.4 | [E3](../specs/epics/E3-realign-goldens-and-canon/index.md) |
| §3 Phase D (D.1–D.8) | [E4](../specs/epics/E4-generator/index.md), F4.1–F4.8 |
| §3 Phase E | [E5](../specs/epics/E5-web-archetypes/index.md) |
| §3 Phase F | [E6](../specs/epics/E6-rebuild-the-repos/index.md) |
| §3 Phase G | [E4 design, steady state](../specs/epics/E4-generator/design.md#steady-state-after-release-1); triggered items [E7](../specs/epics/E7-pykit-release-pin-flip/index.md), [E8](../specs/epics/E8-ado-provider/index.md) |
| §3 critical path | [specs/index.md](../specs/index.md#order) |
| §4 risks | E1 (goldens reviewed lightly), E4 (god-kit, unreviewed templates, engine first, interactive CLI, drift), ADR-0005, E10 (codegen leak), agent-config plan (agent tool), F6.2 (taskkit sunk work), pykit handoff (C.3 growth) |
| §5 decision log | §2.2 |
| §6 open questions | §2.3 |
| §7 revision history, rejected list | §9, §10 |

### 2.2 Decisions

| # | Decision (short) | Now |
| -- | -- | -- |
| D1 | only pykit libraries are build dependencies; library graph acyclic | [workspace graph](../architecture/workspace.md#the-graphs) |
| D2 | generator scope is repo shape only for v1 | [E4 scope](../specs/epics/E4-generator/design.md#scope-and-ownership) |
| D3 | no kit installs in CI; CI logic generated and committed | [ADR-0006](../adr/ADR-0006.md) |
| D4 | ADO parked | [E8](../specs/epics/E8-ado-provider/index.md) |
| D5 | ~~standards repo separate~~ | superseded by D36 |
| D6 | Nx via `pnpm nx run-many`; shkit and macsetup parked | [archetype catalogue](../reference/standard-repo.md#archetype-catalogue); §1 |
| D7 | ~~three v1 archetypes~~ | superseded by D47, then D53 |
| D8 | interactive CLI in the style of `uv`/`nx` | [E4 design](../specs/epics/E4-generator/design.md#commands) |
| D9 | ~~taskkit local-only~~ | superseded by D23 |
| D10 | forge-ci merged into the generator | [CI specification](../reference/standard-repo.md#8-ci-shape) |
| D11 | `check_ci_entrypoint` tool list from the archetype | [F4.1](../specs/epics/E4-generator/F4.1-checks-by-module.md) |
| D12 | ~~contributions protocol~~ | superseded by D26 |
| D13 | ~~`forge-core` six modules~~ | superseded by D29 |
| D14 | `config.toml` the only durable input; preview, `--yes`, idempotent apply, flag parity | [E4 design](../specs/epics/E4-generator/design.md#commands) |
| D15 | apply sequence | revised by D58; [E4 design](../specs/epics/E4-generator/design.md#apply-sequence) |
| D16 | scaffolding shells out and reconciles | [E4 design](../specs/epics/E4-generator/design.md) |
| D17 | ~~adopt-and-diff migration~~ | superseded by D39 |
| D18 | ~~canon precedes commons and kiln~~ | superseded by D36 |
| D19 | ~~skills authored in kits~~ | superseded by D30 |
| D20 | ~~docskit its own repo~~ | superseded by D24 |
| D21 | Dependabot watches kiln only | [CI specification](../reference/standard-repo.md#8-ci-shape) |
| D22 | one release strategy: tag-exists check | [reference §8](../reference/standard-repo.md#8-ci-shape) |
| D23 | taskkit retired; go-task stays the entrypoint | [ADR-0007](../adr/ADR-0007.md); [agent-config plan](agent-config-future.md) |
| D24 | docskit folded into kiln as the `docs` module | [E4 design](../specs/epics/E4-generator/design.md) |
| D25 | the generator is named kiln; legacy state never overwritten | §4; [E4 scope](../specs/epics/E4-generator/design.md#scope-and-ownership) |
| D26 | no contributions protocol | §9 |
| D27 | ownership per file or per fenced block | [ADR-0003](../adr/ADR-0003.md) |
| D28 | no umbrella manifest; kiln owns only `.rn-forge/kiln/` | [ADR-0004](../adr/ADR-0004.md) |
| D29 | `forge-core` not built | [workspace graph](../architecture/workspace.md#the-graphs) |
| D30 | kiln ships no skills; one-time judgement as kiln prompts | [Scope and ownership](../specs/epics/E4-generator/design.md#scope-and-ownership) |
| D31 | `python-lib` is an archetype | [archetype catalogue](../reference/standard-repo.md#archetype-catalogue) |
| D32 | ~~standards repo named canon~~ | superseded by D36 |
| D33 | ~~canon hand-managed MkDocs~~ | superseded by D36 |
| D34 | intellibench's lints stay repo-local in intellibuild | [intellibuild plan](intellibuild.md) |
| D35 | `rn-forge-tooling` is the development layer | [workspace graph](../architecture/workspace.md#the-graphs) |
| D36 | canon folded into kiln, rendered as `standard.md` | [ADR log intro](../adr/index.md); [reference](../reference/standard-repo.md) |
| D37 | codegen as `[codegen]` extras | [E10](../specs/epics/E10-kiln-generators/index.md) |
| D38 | `kiln adopt` not built | [Scope and ownership](../specs/epics/E4-generator/design.md#scope-and-ownership) |
| D39 | repos rebuilt, not migrated | [E6 rebuild scope](../specs/epics/E6-rebuild-the-repos/index.md) |
| D40 | apollo parked | [E6](../specs/epics/E6-rebuild-the-repos/index.md) out of scope |
| D41 | intellibench superseded by intellibuild | [intellibuild plan](intellibuild.md) |
| D42 | the tool keeps the name kiln, not canon | §4 |
| D43 | golden repos are the source of truth | revised by D63, D69; [F4.4 render matrix](../specs/epics/E4-generator/F4.4-render-matrix.md) |
| D44 | `_areas.yml` and `_structure.md` seeded | [ownership specification](../reference/standard-repo.md#2-one-owner-per-file-or-per-block) |
| D45 | CI generated and committed; no reusable-workflow repo | [ADR-0006](../adr/ADR-0006.md) |
| D46 | rn-forge deps are pinned PEP 508 direct URLs | [E7 pin transition](../specs/epics/E7-pykit-release-pin-flip/index.md) |
| D47 | ~~four `-ng` archetypes~~ | superseded by D53/D54 |
| D48 | ADRs carry decisions; the reference carries specs | [ADR log intro](../adr/index.md) |
| D49 | libraries own the boilerplate (proposed) | [shared CLI design](../specs/epics/E3-realign-goldens-and-canon/index.md#shared-cli-design) |
| D50 | `ruff check --fix` before `ruff format` | [reference §5](../reference/standard-repo.md#5-what-task-validate-proves); §7.2 |
| D51 | checkers become a versioned package | revised to one pinned kiln: [ADR-0006](../adr/ADR-0006.md); [E4 design](../specs/epics/E4-generator/design.md) |
| D52 | three library layers | [workspace graph](../architecture/workspace.md#the-graphs) |
| D53 | seven archetypes | [archetype catalogue](../reference/standard-repo.md#archetype-catalogue) |
| D54 | a flag selects a library only; every shipped value has a golden | [ADR-0005](../adr/ADR-0005.md); [F4.4 render matrix](../specs/epics/E4-generator/F4.4-render-matrix.md) |
| D55 | sub-packages by kind of mechanism | pykit handoff |
| D56 | kiln generates repo structure; frameworks generate code | [ADR-0001](../adr/ADR-0001.md); backlog [E10](../specs/epics/E10-kiln-generators/index.md). **Rescheduled:** D56 put `kiln generate package` in Phase D, but E10 defers it until after release-1. The scope is unchanged and the timing is not. |
| D57 | README is the single prose home | [ADR-0003](../adr/ADR-0003.md) |
| D58 | kiln seeds the instruction files and invokes nothing | [ownership specification](../reference/standard-repo.md#2-one-owner-per-file-or-per-block) |
| D59 | lifecycle surface built in tooling | [shared CLI design](../specs/epics/E3-realign-goldens-and-canon/index.md#shared-cli-design) |
| D60 | historic `pyproject.toml` advisory verification | superseded: repo-owned settings are ignored by doctor; [ownership specification](../reference/standard-repo.md#2-one-owner-per-file-or-per-block) |
| D61 | lifecycle is a capability flag | [ADR-0005](../adr/ADR-0005.md) |
| D62 | knobs are tiered | [E4 design](../specs/epics/E4-generator/design.md) |
| D63 | templates authored; goldens as committed snapshots | revised by D69; [F4.4 render matrix](../specs/epics/E4-generator/F4.4-render-matrix.md) |
| D64 | layered config resolved once and committed | revised by D70; [ADR-0004](../adr/ADR-0004.md) |
| D65 | `cicd`, not `devops` | [E4 design](../specs/epics/E4-generator/design.md) |
| D66 | committed workflows + local composite actions | [ADR-0006](../adr/ADR-0006.md) |
| D67 | modules, not distributions | [ADR-0001](../adr/ADR-0001.md) |
| D68 | `Generator` protocol is the module contract | [E4 design](../specs/epics/E4-generator/design.md) |
| D69 | no rendered golden committed | [F4.4 render matrix](../specs/epics/E4-generator/F4.4-render-matrix.md) |
| D70 | config sources, list replace, committed merged config | [configuration specification](../reference/standard-repo.md#9-configuration) |
| D71 | no internal module published | [ADR-0001](../adr/ADR-0001.md) |
| D72 | modules declare their config; kiln composes | [E4 design](../specs/epics/E4-generator/design.md) |
| D73 | pykit consumed from its branch until stable | [E7 pin transition](../specs/epics/E7-pykit-release-pin-flip/index.md) |
| D74 | checks by module, `core` module (proposed) | checks by module kept in `kiln doctor`; one distribution per [ADR-0006](../adr/ADR-0006.md) |

### 2.3 Open questions

| # | Question | Now |
| -- | -- | -- |
| 1 | Sonar on by default? | parked in the `cicd` story on [F4.3](../specs/epics/E4-generator/F4.3-concern-modules.md) |
| 2 | public or private repos? | parked in the `cicd` story on [F4.3](../specs/epics/E4-generator/F4.3-concern-modules.md) |
| 3 | seeded `_areas.yml` | answered by D44 |
| 4 | `python-web-app --framework django` shipped | answered: deferred until a real repo needs it; [E5](../specs/epics/E5-web-archetypes/index.md) |
| 5 | intellibuild on ADO from day one? | open on the [intellibuild plan](intellibuild.md) |
| 6 | ngkit an archetype or hand-managed? | open on [E9](../specs/epics/E9-node-archetypes/index.md) |
| 7 | the rebuilt agent tool's version line | moot — agent configuration is a standalone plan |
| 8 | ADO provider | parked — [E8](../specs/epics/E8-ado-provider/index.md) |
| 9 | an agent-tool docs command | parked — [agent-config plan](agent-config-future.md) |
| 10 | apollo's return | parked — [E6](../specs/epics/E6-rebuild-the-repos/index.md) out of scope |
| 11 | is lifecycle orthogonal to the archetype? | answered — [ADR-0005](../adr/ADR-0005.md) |
| 12 | which rendered trees are committed? | answered — [F4.4 render matrix](../specs/epics/E4-generator/F4.4-render-matrix.md) |
| 13 | config source format and merge semantics | answered — [ADR-0004](../adr/ADR-0004.md) |
| 14 | is `cicd` published? | answered — [ADR-0001](../adr/ADR-0001.md) |
| 15 | how an archetype declares its modules | answered — [ADR-0001](../adr/ADR-0001.md) |
| 16 | intellibuild's archetype | answered 2026-09-12: `python-web-app` — [intellibuild plan](intellibuild.md) |
| — | confirm D74 | answered 2026-09-13: kiln is a pinned dev dependency — [ADR-0006](../adr/ADR-0006.md) |

## 3. Rebuild, not migrate — the donors

Every repo in scope except pykit is created fresh by `kiln new` and its source
is written against commons and tooling. Nothing is copied file-by-file from an
old repo into a new one. What *is* carried over is **decisions, specs, tests and
fixtures**, read as prior art:

| Donor | Carry | Do not carry |
| -- | -- | -- |
| `agentkit` | **already harvested** — the E17 docs area model, `_areas.yml`/`_structure.md`, the checker behaviours, the verb layout, the CI discipline. ADR-0021 is kiln ADR-0003. Everything still outstanding, including `self_command.py` as prior art for the lifecycle surface, is in [agent-config-future.md](agent-config-future.md) | `core/**` (replaced by tooling); setup skills; `feedback.md`; scripts as files |
| `taskkit` | `core/validator.py` rules and tests; `tests/fixtures/repos/**` for the web archetypes; the `extra_refs` / repository-owned include model; `Envelope` `--json` shape. Retirement record in [agent-config-future.md](agent-config-future.md) | discovery, planner, adapters, install layer |
| `intellibench` | `docs2/**` (already in the area model — it becomes intellibuild's `docs/`); the universal lints in `tools/lint/` as *template inputs* (`check_ci_entrypoint`, `check_layout`, `check_locks`, `check_pins`); `tools/docs/{check,_nav,generate_order,check_mermaid}` behaviour | `docs/` (superseded by `docs2/`); `ADR_REVIEW.md`, `temp.txt`; product code paths |
| `apollo` | ADR-0024 (`.docs-site` output dir); `docs/guides/task-vocabulary.md` as input to kiln ADR-0007 | everything else (parked) |
| `pykit` | **kept as-is** — package source, tests, docs, plans. Only the repo *skeleton* is regenerated ([F6.1](../specs/epics/E6-rebuild-the-repos/F6.1-pykit-skeleton.md)) | `.github/workflows/_package-ci.yml` (replaced by the generated matrix) |

Commons is the one exception to "rebuild": it is 8k lines with a plan that just
landed, at the wrong package boundary. It is **split**, not rebuilt.

## 4. Name reassignment

`kiln` previously named the agent-config installer that became agentkit;
`agentkit/docs/adr/0001-product-name-agentkit.md` retired that name. The plan
intentionally reassigned the repo, distribution, module, binary, and
`.rn-forge/kiln/` namespace to the generator (D25). The retired tool wrote both
global and project-local `.rn-forge/kiln/` trees. The new CLI must detect those
legacy trees and refuse to overwrite them; removal is an explicit user action.

`canon` was considered as the tool's name and rejected (D42): a tool needs a
verb-shaped name (`kiln new`), and canon is the noun for the rules the tool
carries. "Canon" is the name of the docs section inside kiln that holds them.

## 5. Findings (evidence; compressed from revisions 1–3)

| # | Finding | Evidence | Resolved by |
| -- | -- | -- | -- |
| F1 | Three owners for `Taskfile.yml`; apollo broken now | apollo's uncommitted `taskkit adopt` dropped 5 lint gates; `ci.yml` calls `task api:install`, which no longer exists | one owner (kiln); apollo parked, rebuilt later with `kiln new` |
| F2 | Byte-identical scripts copied across repos; `check_ci_entrypoint.py` differs only in a list literal | `diff agentkit/scripts/check_task_layout.py apollo/scripts/check_task_layout.py` | generated, committed scripts with a config header; then one pinned distribution (ADR-0001) |
| F3 | Four forks of the docs link checker | taskkit 171 lines, apollo 156, intellibench 165, agentkit 187 | one template in kiln |
| F4 | `taskkit adopt` replaces rather than reconciles | `extra_refs`, `ownership`, `command_overrides` all empty in apollo | moot — no adopt (D38); `gate.shrunk` doctor rule |
| F5 | CI is unowned; four pipelines share nothing | only agentkit pins SHAs and sets `permissions:` | kiln `cicd` module |
| F6 | intellibench is the richest standards donor and least standardized | 11 lints in `tools/lint/`, docs toolchain in `tools/docs/`, no CI | harvested into kiln templates (E1); intellibuild gets CI first |
| F7 | Docs area model exists in exactly one repo | taskkit has no `adr/`, `releases/`, `_structure.md` | `docs` module, applied to every generated repo |
| F8 | Skill/kit boundary unenforced | `go-task-setup` installs a script that `task lint` runs | no skill installs anything (D30) |
| F9 | Instruction files restate the standard in prose | apollo `CLAUDE.md` spends ~15 lines on docs layout | kiln managed block pointing at the rendered standard |
| F10 | Root-level session residue tracked | `agentkit/feedback.md`, `apollo/epic-design-docs-handoff.md`, `intellibench/ADR_REVIEW.md`, `intellibench/temp.txt` | not carried into rebuilt repos; `hygiene.stray-root-file` |
| F11 | No cross-repo compliance signal | — | `kiln doctor --all` |
| F12 | Kits duplicate runtime-neutral and local-tool mechanisms | both have `core/{state,config,paths,io}.py`; dep floors drifted (`typer>=0.26.8` vs `>=0.12`) | Phase C: commons/tooling boundary |
| F13 | apollo's config shape defeated detection | tool config at root pyproject, tasks emitted with `dir: apps/api` | archetype is asserted, never inferred (D23) |
| F14 | `.rn-forge/` umbrella has no owner | each kit writes its own gitignore block and root discovery | kiln owns the umbrella (D28) |
| F15 | taskkit refuses Nx | `nx.json` in `_UNSUPPORTED_MANIFESTS` (`discovery.py:51`) | moot — templates call `pnpm nx run-many`; no adapter needed |
| F16 | taskkit's detection layer is dead weight once the archetype is asserted | discovery + planner + adapters ≈ 1,950 of 5,248 lines; rendered output for taskkit's own repo ≈ 80 lines of YAML | D23 |
| F17 | pykit already holds most of what `forge-core` specified, but not at the right package boundary | commons correctly owns `PathUtils`, `ContentHash`, atomic writes, documents and entry-point loading; local `StateStore`, templates and Typer wiring landed there too | D29, D35 |
| **F18** | **A third of kiln's revision-6 spec existed only to reconcile pre-existing files** | `adopt`, `ADOPT`/`ADOPT_CONFLICT`, closure capture, gate-shrink preflight, the model-delta harness, `inventory.py`/`apply_mapping.py`, the docs-migration runbook | **D38, D39** — none of it is built |
| **F19** | **A separate canon repo had no reference mechanism** | revision 6 gave no way for an agent in agentkit or pykit to read canon; agentkit ADR-0005 already says rules live in the target repo | **D36** — kiln renders the standard into every repo |

## 6. Harvest inventory

What was carried into the golden repos from the donor repos, what was
deliberately dropped, and where each thing landed. This is the review artifact
for "everything common and worth carrying over" — the counterpart to
[Scope and ownership](../specs/epics/E4-generator/design.md#scope-and-ownership)'s
rule that repos are rebuilt rather than migrated. Behaviour is harvested; files
are not.

Donor paths are relative to their repo root. Target paths are relative to a
golden repo, and therefore to every generated repo. The targets are as of E1;
`scripts/**` leaves generated repos under [ADR-0006](../adr/ADR-0006.md).

### Task layout and the vocabulary

| Donor | Behaviour kept | Behaviour dropped | Target |
| -- | -- | -- | -- |
| `agentkit/Taskfile.yml` | the wrapper-only root, the `includes` set, `UV_CACHE_DIR` in-repo, the ten verbs | `lint:markdown` and the `format:markdown` wrapper — mdformat is repository-owned (agentkit ADR-0005) | `Taskfile.yml` |
| `agentkit/tasks/workspace.yml` | `install`, `version`, `build`, `clean`; the separate packaging cache dir and its rationale | `scripts/check_dist_contents.py` as a build step — a repo-specific lint, wired through `[tasks.extra_refs]` instead | `tasks/workspace.yml` |
| `agentkit/tasks/quality.yml` | every `internal: true` primitive; `lint:docs-structure` and `lint:docs-nav` delegating to `:docs:*` | `lint:markdown`, `format:markdown`, the docformatter step in `format:python` | `tasks/quality.yml` |
| `agentkit/tasks/docs.yml` | `build`, `serve`, `nav`, `structure`; `MKDOCS_SITE_DIR` with a `CLI_ARGS` override so CI can target a temp dir | serve port 8083 (arbitrary; now 8080) | `tasks/docs.yml` |
| `apollo/docs/guides/task-vocabulary.md` | the idea of a written vocabulary, as input to [ADR-0007](../adr/ADR-0007.md) | the generated prose page itself, and apollo's verbs (`format-check`, `dev`, `docs`) | ADR-0006; the rendered `.rn-forge/kiln/standard.md` |
| `taskkit` `extra_refs` / repository-owned include model | both mechanisms, as `[tasks.extra_refs]` and `[tasks.includes]` with `ownership = "repository"` | discovery, planner, adapters, the install layer (F16) | `.rn-forge/kiln/config.toml` schema |

### Checkers

| Donor | Behaviour kept | Behaviour dropped | Target |
| -- | -- | -- | -- |
| `agentkit/scripts/check_task_layout.py` | the wrapper-only rule, the non-empty `desc` rule, the go-task shorthand detection | nothing | `scripts/task/check_task_layout.py` |
| `taskkit/core/validator.py` (`graph.*`) | the reachability idea, as the third rule: `REQUIRED_VALIDATE` ⊆ tasks reachable from `validate` | the full graph validator — cycles, include existence, double-namespace prefixes, aggregate-capability drift — which stays in `kiln doctor` where it can render, not in a CI checker that must not | `scripts/task/check_task_layout.py` (config header); `kiln doctor` `taskgraph.*` |
| `agentkit/scripts/check_ci_entrypoint.py` | the whole implementation: GH Actions and ADO step keys, block scalars, the shell-separator regex, the `./` wrapper-script case | the hard-coded `FORBIDDEN_TOOLS` and `CI_DIRS` literals — the exact fork F2 describes | `scripts/ci/check_ci_entrypoint.py`, lists moved into the `# BEGIN kiln config` header |
| `intellibench/tools/lint/check_ci_entrypoint.py` | nothing it did not share with agentkit's | its own separate implementation of the same rule (F3) | — |
| `agentkit/scripts/check_dist_contents.py` | nothing | all of it — a repo-specific packaging lint, not a standard | repo-owned, via `[tasks.extra_refs]` |
| `intellibench/tools/lint/check_locks.py` | the rule (only `uv.lock` and `pnpm-lock.yaml` may be committed) | the implementation, for now — it is one `.gitignore` line away from unnecessary, and no second repo has needed it | not built; D34 |
| `intellibench/tools/lint/check_pins.py` | the SHA-pinning discipline, applied to workflows rather than to dependencies | the hard-coded Angular package list and the `.python-version`/`.nvmrc` equality check — repo policy, not fleet policy | `kiln doctor` `ci.unpinned`; repo-owned otherwise |
| `intellibench/tools/lint/check_layout.py` + `layout_manifest.txt` | nothing | a literal directory manifest — the docs area model does the same job declaratively, and everything else is the archetype | superseded by `docs/_areas.yml` |
| `intellibench/tools/lint/{check_brand,check_gate_tags,check_endpoints,check_db_url,check_e2e_budget,check_vocabulary}.py` | nothing | all of them; genuinely repo-specific (D34) | intellibuild, repo-owned |
| — (new) | — | — | `scripts/standards/check_generated.py`: the committed-state checker. No donor — this is what replaces "trust that the kit ran" |
| `apollo/pyproject.toml` `[tool.uv.sources]` | the git + `subdirectory` source shape for an rn-forge library, since pykit publishes GitHub Releases rather than to PyPI | `branch = "main"` — an unpinned source changes what a repo builds without changing a tracked byte in it | a pinned PEP 508 direct URL in `dependencies` — an override does not survive into a wheel; `scripts/standards/check_rn_forge_deps.py` rule 3 |
| `agentkit/pyproject.toml` dependencies | nothing | the direct `jinja2`/`pydantic`/`rich`/`ruamel-yaml`/`tomlkit`/`typer` dependencies — a `python-cli` repo takes that surface from `rn-forge-tooling` (F12) | `.importlinter` `frameworks-come-from-rn-forge`; [ADR-0005](../adr/ADR-0005.md) |

### Docs toolchain

| Donor | Behaviour kept | Behaviour dropped | Target |
| -- | -- | -- | -- |
| `agentkit/scripts/docs/setup/_common.py` | the `Area`/`Finding` dataclasses, the pyyaml-optional fallback loader, the MkDocs-compatible slugifier | `ALL_AREA_KEYS` / `CORE_AREA_KEYS` — a fixed area whitelist contradicts a seeded `_areas.yml` (D44); `ChangeLog`, `resolve_asset_path`, `templates_dir`, `default_areas_source`, `dump_yaml` — all skill-installer machinery with no customer once no skill installs anything | `scripts/docs/_common.py` |
| `agentkit/scripts/docs/setup/check_structure.py` | area scaffolding, ADR numbering and status, release and epic/feature naming, link and anchor resolution, the `_*.md` reference rule, the instruction-pointer rule | the specs-board status cross-check (couples an index table's prose to file state; belongs to whoever owns the board, not to the repo standard); `--selftest` and its fixture directory | `scripts/docs/check_structure.py` |
| `agentkit/scripts/docs/site/check_docs.py` | broken links, broken anchors, orphan pages, nav targets, gitignored-generated-subtree detection | module-level `ROOT`/`DOCS_DIR` globals — the checker now takes a repo root, so it can be run against a fixture | `scripts/docs/check_docs.py` |
| `agentkit/scripts/docs/site/gen_nav.py` | the marker-fenced nav block, `--check`, index-link ordering, the acronym title map | its private 30-line `_areas.yml` parser — a third YAML loader in the same script set | `scripts/docs/gen_nav.py` |
| `intellibench/tools/docs/{check,_nav,generate_order,check_mermaid}.py` | nothing they did not share with agentkit's versions (F3: four forks of one link checker) | all four implementations | superseded |
| `agentkit/docs/_areas.yml`, `_structure.md` | both, verbatim in shape: seven areas, nav modes, the "where new material goes" routing rule | their status as generated-and-owned — they are now seeded, so a repo can add an area (D44) | `docs/_areas.yml`, `docs/_structure.md` |
| `agentkit` E17 docs area model | the model itself | agentkit's ownership of it — it moves to kiln's `docs` module | [ADR-0005](../adr/ADR-0005.md) |
| `apollo` ADR-0024 | `.docs-site/` as the rendered-output directory, and the `MKDOCS_SITE_DIR` override | `.apollo/site/` and everything about apollo's app-state root | `tasks/docs.yml`, `.gitignore` |

### CI

| Donor | Behaviour kept | Behaviour dropped | Target |
| -- | -- | -- | -- |
| `agentkit/.github/workflows/ci.yml` | the job shape `validate → sonar → check-version → build → publish`; the tag-exists release check; `repo-token` on setup-task; the strict docs build inside validate | the unpinned `actions/*@v4` uses; the missing per-job `permissions:`; the missing `concurrency:`; the four separate lint/typecheck/test steps, now one `task validate` | `.github/workflows/ci.yml` |
| `agentkit/.github/workflows/docs.yml` | the Pages build/deploy split, the temp-dir site build, the "enable Pages by hand" note | the top-level `pages: write` / `id-token: write` grant — those move to the deploy job, which is the only one that needs them | `.github/workflows/docs.yml` |
| `pykit/.github/workflows/_package-ci.yml` | the per-package matrix and the `<package>-v<version>` tag shape | the `workflow_call` indirection and the direct `uv run` steps (every step now goes through `task`) | `golden/python-lib/.github/workflows/ci.yml` |
| `agentkit/sonar-project.properties` | the key/organization shape, the coverage report path, the idea of excluding template assets | the assets-specific exclusion | `sonar-project.properties`, excluding `scripts/**` |

### Instruction files and hygiene

| Donor | Behaviour kept | Behaviour dropped | Target |
| -- | -- | -- | -- |
| `agentkit` ADR-0001, ADR-0005 (instructions single-sourced, seeded) | both: one body, seeded once, and `CLAUDE.md` == `AGENTS.md` | — | `CLAUDE.md` / `AGENTS.md` body, agentkit-owned (since superseded by [ADR-0003](../adr/ADR-0003.md)) |
| `agentkit` ADR-0005 (structure rules live in the repo) | the rule, generalized: the repo's own `_areas.yml` is what the checkers read | — | [ADR-0003](../adr/ADR-0003.md), D44 |
| `agentkit` ADR-0021 (install only what CI runs) | promoted to [ADR-0006](../adr/ADR-0006.md) and strengthened: committed, hashed, and checked | — | [ADR-0006](../adr/ADR-0006.md) |
| `agentkit/feedback.md`, `apollo/epic-design-docs-handoff.md`, `intellibench/{ADR_REVIEW.md,temp.txt}` | nothing | all of it — tracked session residue (F10) | not carried; `hygiene.stray-root-file` |
| `agentkit` setup skills (`go-task-setup`, `docs-setup`, `mkdocs-site-setup`, `spec-structure-setup`) | their *outputs*, which are now templates | the skills themselves, and the fact that a skill installed a file CI runs (F8) | [Scope and ownership](../specs/epics/E4-generator/design.md#scope-and-ownership) |
| `agentkit` generic skills (`gh-fix`, `python-simplify`, `sonar-cleanup`) | all three, unchanged in scope | — | agentkit, rebuilt (out of scope here) |
| `agentkit/.editorconfig` | the file | `trim_trailing_whitespace = false` and `insert_final_newline = false` globally — both now on, with the Markdown exception where trailing spaces are a hard line break | `.editorconfig` |

### The rule that had no mechanism

The plan said commons and tooling are the only permitted rn-forge peer imports,
"enforced by import-linter". It is not, and cannot be: import-linter rejects
subpackages of external packages, so `rn_forge.kiln` is not a legal forbidden
module — verified empirically, both with `rn_forge` installed and without.
[ADR-0005](../adr/ADR-0005.md) moves that rule to
`scripts/standards/check_rn_forge_deps.py`, where it is decidable, and gives
`.importlinter` the complementary rule it *can* enforce: no direct import of a
framework or CLI toolkit that an rn-forge library already owns.

### Not harvested at all

- `agentkit/core/**` and `taskkit/core/**` — replaced by `rn-forge-tooling`
  (F12, [ADR-0002](../adr/ADR-0002.md)).
- `taskkit`'s discovery, planner, adapters and install layer — 1,950 of 5,248
  lines, dead weight once the archetype is asserted (F16).
- `intellibench/docs/` — superseded by its own `docs2/`, which becomes
  intellibuild's `docs/`.
- Every scaffold-output template: `uv init`, `pnpm create` and `nx g` are
  shelled out to and their output reconciled ([ADR-0005](../adr/ADR-0005.md)).

## 7. Review outcomes

The reviews themselves are in [reviews/](reviews/index.md), kept verbatim. This
is what was done about each item, so a later session does not re-derive it from
the diffs.

### 7.1 What the Phase B review changed

**From the owner's review**

| Comment | Outcome |
| -- | -- |
| The original ADR-0001 and ADR-0002 are redundant | Merged into one ownership ADR. "Everything is kiln-owned" was *not* adopted: agentkit, the repo and seeded files all own paths, which is why three artifact kinds exist. |
| ADR-0006's CI model — reusable templates from a devops repo | Examined and rejected with reasons (D45). Pinned reusable workflows cost the same per-repo churn as generation and add an external CI dependency; floating them means unpinned CI. The reviewability win was bought instead with a committed composite action, `.github/actions/setup`. |
| Former standard and dependency-default proposals read as spec, not decision | Correct. Every enumeration moved to `docs/reference/standard-repo.md`; every ADR gained an **Alternatives considered** section (D48). |
| Archetypes should be `python-cli`, `python-lib`, `python-django-ng`, `python-fastapi-ng`; fold dependency defaults into archetypes | Done (D47). `-ng` means a pnpm-managed Nx workspace; `nx_cloud` is a config key; `backend` and `web_runner` are gone. Dependency defaults folded into the archetypes ADR. |
| `AGENTS.md` should be a static pointer to `CLAUDE.md` | Done in all three repos. `check_structure.py`'s docs-pointer rule was generalized to understand single-sourcing rather than demanding both files carry the links. |
| Add a Markdown formatting task | Done: `lint:markdown`, `format:markdown`, seeded `.mdformat.toml`. The earlier harvest note misread agentkit ADR-0005 — it makes the mdformat *config* repository-owned, not the task. `.rn-forge/kiln/standard.md` is excluded, because a formatter rewriting a kiln-owned file is two owners writing the same bytes. |
| Review `pyproject.toml` tool config against pykit/agentkit | Done: `--import-mode=importlib`, targeted test-file ignores instead of `["ALL"]`, `py.typed` markers, `ruff format --check` in the gate. No repo in the fleet uses mypy, and that fleet choice is recorded in the foundational stack ADR. |
| Is there more standard boilerplate — logging, CLI config, arg parsing? | Yes, and it is the strongest argument for the library set. Written up as **shared cli design (proposed)**: tooling owns the boilerplate and the CLI surface is declared in config, not written. Code lands in Phase C/D; D2 still defers application generators. |

**From the codex review** — all eight, in `docs/plans/reviews/phase-b-codex.md`:
published packages lost their dependency source (fixed by pinned direct URLs,
D46); a failed release could never be retried (the release, not the tag, is now
the record, and the publish step creates the tag); Sonar's gate did not gate
(`qualitygate.wait=true`, and `release` needs `sonar`); CI could rewrite the
lockfile (`UV_LOCKED`); no `py.typed`; coverage bypassed per-package config and
collided on filenames (per-package runs, combined, verified to emit
`packages/*/src/...` paths Sonar can map); no format check and a blanket ruff
exemption for tests; fork pull requests ran a scan whose secret they cannot see.

### 7.2 Second feedback round (after 7.1 landed)

| Comment | Outcome |
| -- | -- |
| `format:python` runs `ruff format` before `ruff check --fix`, so lint fixes land unformatted | **Fixed** in all three repos. `check --fix` now runs first, then `format`; `lint:python` asserts the same pair in the same order. This was a real defect, not a style preference. |
| `lint` calling both `lint:python` and `lint:format` is asymmetric with `format` | **Fixed.** `lint:format` is gone; `lint:python` runs `ruff check` and `ruff format --check`, mirroring `format:python`. `required_validate` drops `quality:lint:format`. |
| Will the golden repo's `ADR-0001` be seeded into every repo? | **No.** Only `docs/adr/index.md` and `docs/adr/_structure.md` are seeded; the golden repo's own ADR is fixture content and is not in `state.json`. A new repo gets an empty, structured `adr/` area and writes its own first decision — the runbook covers that. |
| `scripts/` is a good candidate to package and add as a dev dependency | **Historical response (D51; later superseded by one pinned kiln).** 1,454 lines per repo, four of the seven checkers with no per-repo variation at all, and the remaining three varying only by lists already present in `config.toml`. Splitting `rn-forge-kiln-checks` from `rn-forge-kiln` kept the then-current rule that CI never rendered — while removing the duplication. The docs checkers move into tooling in Phase C; the four policy checkers become `rn-forge-kiln-checks` in Phase D, in the kiln repo alongside the CLI. |

### 7.3 What the Phase C review changed

Nothing here is a failure to follow the plan — the plan said the wrong thing,
and F8/F9 are the separate completion gap.

**The one conclusion both reviews reached.** Codex A1: the workstation/runtime
distinction is too absolute — a business batch has maintenance commands, and
Typer, filesystem access and a console are not inherently unsafe in deployed
software. Owner: `python-cli` is really two archetypes, and *"these apps will
not need install, update, home directory, doctor, state, plugins… those
capabilities are needed by a specific class of apps, which are installable
tools."* Same seam, named from both ends. The resolution is D52 (three library
layers) and D53 (`python-app` / `python-tool`), and the two are the same change:
the archetype split is what gives the package split a consumer.

**Architecture (from codex)**

| Item | Outcome |
| -- | -- |
| A1 — the workstation/runtime line is in the wrong place | **Accepted, and generalized.** Split the development layer into `rn-forge-cli` and `rn-forge-tooling` (D52). `DirectoryLock` and `atomic_symlink` move back to commons; `extract_archive`, `StateStore`, `TemplateEngine` and the generation engine stay in tooling; the residual `utils.py` stays in commons — all four for codex's own reason, which is what the signature contains. |
| A1 — move `ManagedBlock` to tooling | **Rejected.** The argument is "its current examples are gitignore, instructions and MkDocs", but the only current *consumers* are developer tools, so that test returns the same answer for everything. `ManagedBlock` is a byte-preserving fenced-span edit with no generator policy in its signature — the same test that moved the lock and the symlink back to commons keeps it there. F6 fixes it in place. |
| A1 — this revises D29/D35/D51 | **Overstated, and worth being precise about.** Codex's own table leaves generation, templates, state, install, CLI and docs mechanics on the development side. The genuine relocations are the lock and the symlink. D35 is *refined* by D52, not reopened. |
| A2 — docs extraction carried kiln policy into tooling | **Accepted in full; the cleanest finding in the review.** `docs/structure.py` hardcoding ADR numbering, epic/release naming and instruction filenames puts rn-forge policy inside a general-purpose library, contradicting ADR-0002 outright. Tooling keeps link, Markdown and nav *mechanics* and takes an explicit policy object; `rn-forge-kiln-checks` supplies it (Phase D). No generic validation framework. |
| A3 — the package contract bundles every consumer with the whole CLI stack | **Accepted; the eager `__init__` is the real defect.** Under D52 it largely evaporates: a batch importing `rn_forge.cli` cannot reach Jinja2, because it is in another distribution. Codex is right that extras add dependencies rather than excluding modules — which is why the split is packages, not extras. |
| Rename tooling to `devtools` / `automation` / `core` | **Rejected, as codex recommended.** None changes an architectural property. `rn-forge-cli` was rejected as a rename of the *whole* package for being too narrow, and adopted as the name of the application layer specifically, where it is exactly right. |

**Archetypes (from the owner)**

| Comment | Outcome |
| -- | -- |
| `python-cli` conflates business batches with installable tools | **Done (D53).** `python-app` and `python-tool`. Same shape, different library set, different `REQUIRED` list, one golden repo each. |
| `python-lib` is a monorepo publishing several packages; `python-app` may also carry internal packages | **Done, and the axis is corrected.** "Is it a monorepo" does not discriminate — every archetype here can be one. *Publishing* does: per-package release tags and a per-package CI matrix, versus one version. Written into ADR-0005 and the runbook. |
| Web repos are microservice-or-full-app, with django/fastapi and angular/react/svelte as choices | **Done (D53).** `python-web-api` and `python-web-app`, with `framework` and `frontend` flags. This reverses D47's blanket rejection of flags, so D54 restates the rule that makes both positions coherent rather than leaving it as a reversal. |
| An API with no separate frontend may still ship a thin admin UI | **Accepted** — `admin_ui` on `python-web-api`. Django admin and actuator-style pages do not make a repo `python-web-app`; a separately built frontend package does. |
| `ui-lib` and `node-web-app`, angular first | **Named in the catalogue, deferred to post-v1.** They need a second toolchain — pnpm release, node CI, no uv — and nothing in v1 scope uses them. Naming them now fixes the taxonomy so `ui-lib` does not arrive later as a one-off. |
| kiln should generate new library packages, models, api, serializers, UI boilerplate | **Split (D56).** `kiln generate package` emits *repo structure* into a workspace, which is already kiln's job — in scope for Phase D. Framework code generators stay D2/D37: they ship in `rn-forge-django[codegen]`, register under `rn_forge.kiln.generators`, and kiln only supplies the command surface. |
| commons' layout is not intuitive | **Done (D55).** Sub-packages by kind of mechanism, applied to commons, cli and tooling. |

**Implementation defects.** Codex's F1–F14, verified where verification was
cheap. F1 (multi-block staging overwrites, and the repeated backup that breaks
rollback), F2 (`except Exception` lets Ctrl-C skip rollback), F3 (`Severity` is
a `StrEnum` compared with `is`, so a JSON round trip silently demotes an error)
and F4 (artifact paths escape the root and are written *before* any backup
exists) were each confirmed against `4624bfe`. They were scheduled as Phase C.2
([E2](../specs/epics/E2-layer-split-and-golden-rename/index.md)).

Two are worth more than codex's framing:

- **F3 is not a `Finding` bug.** `DataclassMixin` does not reconstruct enums on
  deserialization, so every dataclass in the fleet with an enum field has the
  same latent defect. Fix the mixin and audit the set; patching `Finding`
  alone leaves it.
- **F9 is not a stale sentence.** Under D46 the pinned-direct-URL rule applies
  to tooling's own dependency on commons, not only to consumer repos. The
  installation guide's `uv add rn-forge-tooling` describes a distribution
  model this plan rejected; the fix is the release contract.

**F12** is accepted with a simpler fix than codex proposed and a lower priority:
the anchor checker should stop reimplementing Python-Markdown's slug and
unique-id logic and call it. The reference-link and fenced-code gaps are
separately real.

**What neither review said.** Phase C broke ADR-0005's own rule — *a template
change not first made in a golden repo is a bug*. It invented `rn-forge-tooling`
and shared cli design's declared `[cli]` surface, and no golden repo
demonstrated either: golden-cli still pinned commons `v0.2.2` and did not use
tooling at all (which is F8, read as a plan gap rather than a defect). The
missing acceptance test was that **`golden-app` contains a working CLI with zero
hand-written app construction** — met in E2's F2.10.

### 7.4 What the Phase C.2 review changed

| Comment | Outcome |
| -- | -- |
| Root `README.md` and `CLAUDE.md` only name `python-tool` — example, or stale? | **Neither.** It is kiln's own archetype, read from its `config.toml` and rendered into the block. It *is* scheduled to change: the former checker-package proposal made kiln a two-distribution repo, so it becomes `python-lib` at [F4.8](../specs/epics/E4-generator/F4.8-self-hosting.md). The one genuine example — `cd tests/fixtures/golden/python-tool` in the README — now names all three. |
| Those two files overlap; use README for developer-facing content and refer to it from CLAUDE.md | **Done, and promoted to a rule (D57, [ADR-0003](../adr/ADR-0003.md)).** Both files opened with the same sentence and repeated the same status pointers. The ownership rule already forbids two owners writing the same bytes; D57 is that rule applied to prose. |
| Same in each golden repo | **Same fix.** It is a standard change, so it lands in the golden repos first and reaches generated repos as a template. |
| `scripts/` is repetitive; we discussed a devopskit and it is not in the plan | **It was decided and never scheduled.** The former checker-package proposal was accepted and D51 confirmed — including rejecting the `devopskit` name, because `checks` names a role that excludes rendering while `devops` names a domain that excludes nothing. What was missing was execution; it is now [F4.1](../specs/epics/E4-generator/F4.1-checks-by-module.md), with the golden repos losing 1,454 lines each before any template derives from them. |
| Can the near-identical `pyproject.toml` tool config become a reusable pykit component? | **No mechanism exists, and generating it would not deduplicate anything (D60, [ADR-0005](../adr/ADR-0005.md)).** pyproject stays repo-owned and gains doctor check 8a, which warns on divergence — verification without the apply round trip. |
| taskkit is dead and agentkit will be re-ideated from scratch; take the content out | **Done (D58).** Everything agent-config — the rebuild scope, the prior art worth reading, taskkit's retirement record — is in [agent-config-future.md](agent-config-future.md). The structural consequence is the real change: kiln no longer shells out to agentkit and seeds the instruction files itself, so `.claude/**` is unowned until the rethink happens. |
| Global config management has to rethink its role now kiln exists | **Recorded as the question that comes first**, in [agent-config-future.md](agent-config-future.md) §2. agentkit's *project* scope existed largely because nothing else owned repo files; kiln owns them now. Do not answer it by porting the old shape. |
| `rn-forge-cli` is being refactored in a separate session | **Resolved — the refactor landed (pykit plan Part E).** The goldens are to build against `CliApp.from_config()` with no `main.py` and no `log_options`/`output_options` keys — which is [F3.1](../specs/epics/E3-realign-goldens-and-canon/F3.1-goldens-on-part-e-api.md). |
| `python-app` and `python-tool` look the same; a tool should handle install, uninstall, upgrade, version, doctor — uniformly, via an adapter | **Correct, and measurable: the two `pyproject.toml` files differ by a name and one dependency line, and `install/` contains only `archive.py`.** Built as D59 ([ADR-0005](../adr/ADR-0005.md)) with exactly the adapter shape suggested. It also exposed open question 11 — kiln itself is an installable tool whose repo shape is `python-lib`. |

## 8. The scope-expansion thread (revisions 12–13)

**What changed conceptually.** Through revision 11, kiln was *one opinionated
standard, rendered per archetype*. The owner's target is *a standard generator
parameterized by the team's landscape*: org identity in `pyproject.toml`, Sonar
details that differ by where it is hosted, GitHub vs ADO, and per-org
conventions. Those have different failure modes. The one that threatens the
design is D43 + D54 together — goldens are the source of truth and every shipped
flag value needs a golden — because enough knobs means no golden covers any real
combination, at which point the goldens stop being the source of truth and
become decoration.

The reasoning and the outcomes are recorded where they now live: the tier model
in [ADR-0005](../adr/ADR-0005.md); templates, goldens and the render matrix in
[ADR-0005](../adr/ADR-0005.md); layered config in
[ADR-0004](../adr/ADR-0004.md); modules and their contract in
[ADR-0001](../adr/ADR-0001.md); `cicd` and the GitHub Actions `include:`
constraint in [ADR-0006](../adr/ADR-0006.md). The config lifecycle table and the
`KilnModule` sketch are in [E4's design](../specs/epics/E4-generator/design.md).

### Counters recorded against proposals that were dropped or changed

| Proposal | Outcome |
| -- | -- |
| Make the golden repos themselves Jinja templates | **Changed, not dropped (D63).** Templates are authored in Jinja; goldens stayed committed *rendered* trees, as snapshots — then D69 dropped the commit. |
| `kiln doctor` should render a temp repo and compare, rather than diffing a golden | **Already the design — no change.** `kiln doctor` and `kiln diff` render fresh and compare against disk; doctor never reads a golden. `check_generated.py` deliberately does neither, comparing disk against committed `state.json` hashes, so a cold clone can run it. Goldens appear only in tests. |
| Config discovered at `~/.rn-forge/kiln/` or cwd, absence falling back to kiln defaults | **Reproducibility bug, fixed by D64.** Discovery is kept; it resolves at `kiln new` and the resolved values are committed. |
| Workflows as thin wrappers including templates from inside the cicd package | **Not implementable (D66).** Local composite actions instead. |
| `scripts/` subdirectories owned by kiln and cicd | **Declined — keeps ADR-0006.** Checkers stay console scripts from pinned dev dependencies. |
| kiln "owns its surface" inside `src/` and `tests/` | **Narrowed to verification.** If kiln *generates* files there it has become an application code generator and D56 reopens. |
| `docs`/`tasks`/`cicd` as separately published distributions | **Modules, not distributions (D67).** |
| Move `rn-forge-kiln-checks` into pykit to settle open question 11 | **Declined (D61).** It answers *kiln today* and leaves the underlying question to resurface at the first `python-lib` that ships a command. |

### How the thread closed (revision 13)

| Open item | Answer | Decision |
| -- | -- | -- |
| Which rendered trees are committed (OQ 12) | **None.** Rendered output is regenerable, so it does not belong in git. A task renders every shipped archetype × flag combination into a gitignored directory; the owner reviews and approves the output, optionally with a parallel review agent reading the rendered copies. The same task validates each cell. | D69 |
| Config source and merge rule (OQ 13) | A **local path or a git URL**, never a package. Deep merge, **lists replace**. `kiln new` resolves once and writes the merged config into the repo; every later operation reads only that file. Re-resolution is explicit: `kiln config update` (the source changed) and `kiln config upgrade` (kiln changed). | D70 |
| Is `cicd` published (OQ 14) | **No, and neither is any other internal module.** They are only usable through a kiln-generated repo. | D71 |
| How an archetype declares its modules (OQ 15) | **Each module owns its config section, its `kiln new` options, its artifacts and its checks**; kiln composes them into one schema, one CLI and one generator. `archetype.toml` lists the modules an archetype enables. | D72 |
| Phase sequencing | Revision 14's Phases C.3 → C.4 → D → E, now the [board's order](../specs/index.md#order). | — |

## 9. Rejected along the way — do not revisit without new information

- *A generic `scriptkit` / shared script bag* — recreates F2 one level up.
  Scripts are generated by the module that owns their config.
- *Standalone `devopskit` CI generator* — merged into the generator (D10).
- *Reusable GitHub workflows as the reuse mechanism* — cannot serve ADO; D3
  removed the setup action that justified them.
- *Kits reading each other's config point-to-point, and its replacement, the
  contributions protocol* — both moot with one generator (D26): cross-module
  names are a kiln-ADR contract that kiln's templates reference directly.
- *Plain shell scripts instead of go-task* — loses `task --list`
  discoverability, the wrapper/inner split, and the ci-entrypoint rule all
  four repos already build on.
- *Keeping taskkit as a thin renderer under kiln* — a second CLI for 80 lines of
  templated YAML.
- *A separate `forge-core` package with pydantic schemas* — three kits' worth of
  schema is ~50 lines and lives in the only kit that reads it.
- *`forge` as the binary name* — collides with Foundry's Ethereum `forge`.
- *A separate canon docs repo* (revision 6) — no reference mechanism from other
  repos; eight pages do not justify a repo; kiln renders the standard into
  each repo instead (D36).
- *`canon` as the tool's name* — verb-shaped names for tools; canon is the rules
  (D42).
- *Separate `rn-forge-django-codegen` / `rn-forge-fastapi-codegen` packages*
  (revision 6) — a compatibility matrix for generators that do not exist yet;
  co-versioning with the runtime is the point (D37).
- *`kiln adopt` and adopt-and-diff migration* (revisions 4–6) — every customer
  is rebuilt instead; a third of the spec existed only for adoption (D38, D39,
  F18).
- *Building the tooling generation engine before the golden repos* —
  framework-before-app; the engine's scope is whatever the golden repos
  contain (D43).

## 10. Revision history

**Revision 14** — implementation-ready. §0.1 rewritten as a phase board with
verified on-disk state (goldens behind pykit Part E, `golden-lib` on a pre-split
commons tag, agentkit still in the reference, `rn-forge-web` absent from it);
§0.2 gains web and fastapi; §3 rewritten from Phase C.3 on — C.3 (pykit
lifecycle), new C.4 (kiln realignment), D split into D.1–D.8 against D69–D74, E
gated on `rn-forge-fastapi`, pykit releases moved to a triggered item under G.
D73 (branch/path pins until stable), D74 (checks by module, `core` module;
proposed). Open question 16 raised. **The last revision; the plan is frozen here
and its content moved into specs, ADRs and this file.**

**Revision 13** — the scope-expansion thread closed from the owner's answers: no
committed rendered goldens, a gitignored render matrix and owner approval (D69);
path-or-git config sources, list replacement, committed merged config and
`kiln config update`/`upgrade` (D70); no internal module published (D71);
modules declare their own config and options (D72). Open questions 12–15
answered.

**Revision 12** — the scope-expansion thread: the tier model amending D54 (D62),
Jinja templates as the authored source with goldens as committed snapshots plus
a matrix harness (D63, revising D43), resolved-and-committed layered config
(D64), `cicd` naming and its generate-time model (D65, D66), concerns as modules
rather than distributions (D67), and the promoted `Generator` protocol (D68).

**Revision 11** — open question 11 answered: the lifecycle surface is a
capability flag and `python-tool` is an alias for `python-app` + `lifecycle`
(D61); the kiln repo is cleared to publish further distributions.

**Revision 10** — after the owner's Phase C.2 review. README becomes the single
prose home and the instruction files become pointers plus blocks (D57). agentkit
leaves the plan and kiln seeds the instruction files itself, deleting apply step
6 (D58); the agent-config material moves to
[agent-config-future.md](agent-config-future.md). The tool lifecycle surface is
built behind a defaulted `ToolProduct` adapter, as new Phase C.3, because
`python-app` and `python-tool` were otherwise the same repo (D59).
`pyproject.toml` stays repo-owned and is verified rather than generated (D60).
The former checker-package proposal gets a schedule: `scripts/**` leaves the
ownership table, the template inventory, the apply sequence and the golden
repos, and `rn-forge-kiln-checks` becomes Phase D step 1.

**Revision 9** — after the Phase C review. The development layer is **split in
two** — `rn-forge-cli` for the process and command-line shape,
`rn-forge-tooling` for the file-owning machinery (D52, ADR-0002) · the archetype
catalogue becomes **seven names plus two implementation flags** (D53, ADR-0005),
replacing `python-cli` with `python-app`/`python-tool` and the `-ng` pair with
`python-web-api`/`python-web-app` · a config flag is allowed only when it
changes neither topology nor task graph, and **every shipped flag value has a
golden repo** (D54) · commons, cli and tooling are **re-laid-out into
sub-packages** (D55) · `kiln generate package` is in scope; framework code
generators stay deferred (D56) · fourteen implementation defects from the review
are tracked as **Phase C.2**.

**Revision 8** — after the Phase B review by the owner and by codex. Phases A
and B executed. Archetypes renamed and reduced to four config-key-free names
(D47); an archetype gains a library set, enforced by `check_rn_forge_deps.py`
(D46); CI stays generated, with a composite action (D45); the ADR set
restructured to nine with the specifications moved into
`docs/reference/standard-repo.md` (D48); shared cli design proposed for the
tooling boilerplate target (D49). Eight defects from the codex review fixed in
the golden repos.

**Revision 7** — rebuild not migrate (D39): `adopt`, the ADOPT/ADOPT_CONFLICT
rows, closure capture, gate-shrink preflight, the model-delta harness, the
docs-migration scripts and runbook all removed (F18). Canon folded into kiln
(D36, F19) with the standard rendered into every repo. Codegen as `[codegen]`
extras (D37). apollo parked (D40); intellibench → intellibuild (D41). Golden
repos as template source of truth (D43), reviewed before generator code.
Sequencing: stabilize pykit → canon + golden → tooling → kiln → web → rebuilds.

**Revision 6** — split pykit into runtime-safe `rn-forge-commons` and
development-only `rn-forge-tooling`. CLI/console, local state, templates and
installer mechanics moved to tooling. Framework code generators as separate
tooling providers.

**Revision 5** — generator named kiln everywhere (D25). CI runs committed
checkers without kiln; committed state is the drift/gate baseline; first
adoption preflighted and path-forced; task surface, template extra, JSON
metadata, docs scripts, import contracts, and acceptance checks fully specified.

**Revision 4** — after code review of commons `feature/upgrade`, taskkit, and
agentkit. `forge-core` dropped for Part D (F17); taskkit retired (F16);
contributions protocol, entry-point skills and docskit folded or dropped. Phases
rewritten with acceptance commands.

**Revision 3** — CI model inverted to generate-and-commit (D3); forge-ci
collapsed into devfoundry; taskkit made local-only; `forge-core` specified;
archetypes defined; pykit-first sequencing.

**Revision 2** — F12–F15; `.rn-forge` ownership moved off agentkit;
two-dependency-graph split; contributions protocol; devfoundry accepted.
Corrected: `uv run <kit>` made every repo depend on the kits.

**Revision 1** — review of four repos; F1–F11; proposed five components incl. a
separate `forge-ci` of reusable workflows; repo tasks calling kits via
`uv run <kit>`.
