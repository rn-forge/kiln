# rn-forge repo standardization — plan of action

**Date:** 2026-09-10 · **Revision:** 9 **Repos in scope:** `rn-forge/pykit`,
`rn-forge/kiln` (new), `rn-forge/agentkit` (rebuilt), `walgreens/intellibuild`
(new; successor to `intellibench`) **Parked:** `rn-tools/apollo`, `ngkit`,
`shkit` · **Retired:** `rn-forge/taskkit`

**Revision 9 changes (after the Phase C review):** the development layer is
**split in two** — `rn-forge-cli` for the process and command-line shape,
`rn-forge-tooling` for the file-owning machinery (D52, ADR-0002) · the archetype
catalogue becomes **seven names plus two implementation flags** (D53, ADR-0005),
replacing `python-cli` with `python-app`/`python-tool` and the `-ng` pair with
`python-web-api`/`python-web-app` · a config flag is allowed only when it
changes neither topology nor task graph, and **every shipped flag value has a
golden repo** (D54) · commons, cli and tooling are **re-laid-out into
sub-packages** (D55) · `kiln generate package` is in scope; framework code
generators stay deferred (D56) · fourteen implementation defects from the review
are tracked as **Phase C.2** (§0.8).

**Revision 8 changes (after the Phase B review):** Phases A and B are
**executed** — see §0.1 · archetypes are renamed to `python-cli`, `python-lib`,
**`python-django-ng`** and **`python-fastapi-ng`**, dropping the `backend` and
`web_runner` config keys (D47) · an archetype now carries a **library set** as
well as a shape, enforced by a generated checker (D46) · CI stays **generated**,
with a committed composite action rather than reusable workflows from a devops
repo (D45) · kiln's ADRs are **restructured to nine** and the specifications
they produced move to `docs/reference/standard-repo.md` (D48) · a proposed
ADR-0009 targets what `rn-forge-tooling` must expose (D49).

**Revision 7 changes:** repos are **rebuilt from scratch**, not migrated — git
history is irrelevant for pre-v1 repos · **canon is folded into kiln** (kiln's
ADRs and standard-repo spec are the canon; kiln renders the standard into every
repo) · `kiln adopt` and every reconciliation mechanism that existed only for
adoption are **not built** · framework code generators are **`[codegen]`
extras** of the runtime packages, not separate packages · apollo is parked ·
**golden repos** are authored and reviewed before any generator code · pykit
Part C is stabilized first, then golden repos, then tooling extraction, then
kiln.

______________________________________________________________________

## 0. Handoff — read this first

This document is self-contained and is written to be executed phase by phase by
an implementer who has not read the chat history. Read §0 → §2 → §3. §5 is the
decision log; do not re-open a **Confirmed** decision without new information.
§1 is the evidence behind the design; skim it, do not act on it.

### 0.1 Where we are now — 2026-09-09

**Phase A: done.** pykit's Part C is committed on `feature/upgrade`; the working
tree is clean and `commons/__init__.py` carries the `tooling-bound (Phase C)`
classification comment.

**Phase B: done, reviewed, and revised.** `rn-forge/kiln` exists at
`rn-forge/kiln/` as a fresh git repository (`git init`, **nothing committed** —
the tree is left for review). It contains:

- **The canon** — `docs/adr/0001`–`0009` and `docs/reference/standard-repo.md`.
  The ADRs carry decisions and rejected alternatives; the reference carries
  the specifications (verb list, ownership table, dependency sets, config
  schema, doctor codes, CI shape). This document lives at
  `docs/plans/standardization-plan.md`, with a one-line pointer left at
  `rn-forge/STANDARDIZATION-PLAN.md`.
- **Two golden repos** — `tests/fixtures/golden/python-cli` (`golden-cli`) and
  `python-lib` (`golden-lib`, two independent packages). Both are complete and
  runnable: `uv sync && task validate` passes standalone in each, workflows
  pass `actionlint`, and the docs sites build `--strict`. The `-ng` fixtures
  are deferred to Phase E as the plan allows.
- **`docs/plans/harvest.md`** — the donor inventory: what each of agentkit,
  taskkit, intellibench and apollo contributed, and what was deliberately
  dropped.
- **Review outcomes** — `docs/plans/reviews/phase-b-owner.md` and
  `phase-b-codex.md`, and everything in them is addressed. See §0.6.

**Phase C: first pass landed in pykit, reviewed, and revised.** pykit commit
`4624bfe` extracted `rn-forge-tooling`. Both reviews are in
`docs/plans/reviews/phase-c-codex.md` and `phase-c-owner.md`, and both landed on
the same conclusion from opposite directions: the commons/tooling seam is in the
wrong place. §0.8 is the outcome.

**Next: Phase C.2** (§3) — the layer split, the package re-layout, the fourteen
defect fixes, and the consumer wiring Phase C's own addendum required and never
got. **Nothing in Phase D starts until C.2 lands**, because kiln's templates
derive from the golden repos and the golden repo set changes here.

`docs/plans/commons-upgrade-plan.md` in pykit carries the executable form of
C.2, starting at its **"Part D — resume here"** marker.

Repo state; verify with `git status` before acting, these will be stale:

| Repo | Branch | State | Note |
| -- | -- | -- | -- |
| `rn-forge/kiln` | `feature/v1` | canon revised for revision 9 | golden fixtures still carry the **old archetype names**; renamed in C.2 |
| `rn-forge/pykit` | `feature/upgrade` | clean at `4624bfe` | Phase C first pass landed; **Phase C.2 re-splits into commons/cli/tooling here** |
| `rn-forge/agentkit` | `feature/v0.6.0` | clean | the `python-tool` model repo; **rebuilt from scratch in Phase F** |
| `rn-forge/taskkit` | `feature/v1` | 34 staged | **retired (D23)** — donor for `validator.py` and test fixtures only |
| `rn-tools/apollo` | `feature/initial` | 13 dirty | **parked (D40)** — broken working tree left as-is |
| `walgreens/intellibench` | `feature/iteration-2` | 13 dirty | **superseded by intellibuild (D41)** — `docs2/` is the new repo's docs; `tools/` is a donor |

### 0.2 Component map after this plan

| Component | Kind | Owns | Status |
| -- | -- | -- | -- |
| **commons** (`rn-forge-commons` in pykit) | library | runtime-neutral Python/data/filesystem mechanisms and integration protocols | exists; re-laid-out in Phase C.2 |
| **cli** (`rn-forge-cli` in pykit) | app library | the Typer app factory, `AppConsole`, the standard option set, logging wiring, error-to-exit-code, the declared `[cli]` surface | **new; split out in Phase C.2 (D52)** |
| **tooling** (`rn-forge-tooling` in pykit) | dev-tool library | the generation engine, templates, local state, installer mechanics, docs mechanics | extracted in Phase C; **narrowed in Phase C.2** |
| **kiln** (`rn-forge/kiln`, binary `kiln`) | CLI + canon | the **canon** (ADRs, standard-repo spec, runbooks); archetypes and golden repos; `.rn-forge/` umbrella; `Taskfile.yml` + `tasks/**`; docs tree + MkDocs; CI; `doctor` | **new** |
| **agentkit** | CLI | `.claude/**`, `.codex/**`, `CLAUDE.md`/`AGENTS.md` body, generic skills | exists; **rebuilt on tooling in Phase F** |
| `rn-forge-django[codegen]` (later `rn-forge-fastapi[codegen]`) | extra | framework templates, option schemas, generator entry points | later (D2); boundary fixed now (D37) |
| canon repo · taskkit · `go-task-setup` · `docs-setup` · `mkdocs-site-setup` · `spec-structure-setup` · `forge-core` · `forge-ci` · `docskit` | — | — | **not built / retired** |

### 0.3 Rebuild, not migrate (D39)

Every repo in scope except pykit is created fresh by `kiln new` and its source
is written against commons and tooling. Nothing is copied file-by-file from an
old repo into a new one. What *is* carried over is **decisions, specs, tests and
fixtures**, read as prior art:

| Donor | Carry | Do not carry |
| -- | -- | -- |
| `agentkit` | ADRs 0001–0021 (as decisions; renumbered only if the new repo needs it); E17 docs area model; `docs/_areas.yml`, `docs/_structure.md` as the reference shape; the *behaviour* of `scripts/docs/**`, `check_task_layout.py`, `check_ci_entrypoint.py`; `Taskfile.yml` + `tasks/**` verb layout; `.github/workflows/ci.yml` pin/permission discipline; generic skills `gh-fix`, `python-simplify`, `sonar-cleanup` | `core/**` (replaced by tooling); setup skills; `feedback.md`; scripts as files |
| `taskkit` | `core/validator.py` rules and tests; `tests/fixtures/repos/**` for the `-ng` archetypes; the `extra_refs` / repository-owned include model; `Envelope` `--json` shape | discovery, planner, adapters, install layer |
| `intellibench` | `docs2/**` (already in the area model — it becomes intellibuild's `docs/`); the universal lints in `tools/lint/` as *template inputs* (`check_ci_entrypoint`, `check_layout`, `check_locks`, `check_pins`); `tools/docs/{check,_nav,generate_order,check_mermaid}` behaviour | `docs/` (superseded by `docs2/`); `ADR_REVIEW.md`, `temp.txt`; product code paths |
| `apollo` | ADR-0024 (`.docs-site` output dir); `docs/guides/task-vocabulary.md` as input to kiln ADR-0007 | everything else (parked) |
| `pykit` | **kept as-is** — package source, tests, docs, plans. Only the repo *skeleton* is regenerated (Phase F.2) | `.github/workflows/_package-ci.yml` (replaced by the generated matrix) |

Commons is the one exception to "rebuild": it is 8k lines with a plan that just
landed, at the wrong package boundary. It is **split**, not rebuilt.

### 0.4 Name reassignment

`kiln` previously named the agent-config installer that became agentkit;
`agentkit/docs/adr/0001-product-name-agentkit.md` retired that name. This plan
intentionally reassigns the repo, distribution, module, binary, and
`.rn-forge/kiln/` namespace to the generator. The retired tool wrote both global
and project-local `.rn-forge/kiln/` trees. The new CLI must detect those legacy
trees and refuse to overwrite them; removal is an explicit user action.

`canon` was considered as the tool's name and rejected (D42): a tool needs a
verb-shaped name (`kiln new`), and canon is the noun for the rules the tool
carries. "Canon" is the name of the docs section inside kiln that holds them.

### 0.6 What the Phase B review changed

Both reviews are in `docs/plans/reviews/`. Every item is addressed; this is the
list, so a later session does not have to re-derive it from the diffs.

**From the owner's review**

| Comment | Outcome |
| -- | -- |
| ADR-0001 and ADR-0002 are redundant | Merged into one ownership ADR. "Everything is kiln-owned" was *not* adopted: agentkit, the repo and seeded files all own paths, which is why three artifact kinds exist. |
| ADR-0003's CI model — reusable templates from a devops repo | Examined and rejected with reasons (D45). Pinned reusable workflows cost the same per-repo churn as generation and add an external CI dependency; floating them means unpinned CI. The reviewability win was bought instead with a committed composite action, `.github/actions/setup`. |
| ADR-0008 and ADR-0009 read as spec, not decision | Correct. Every enumeration moved to `docs/reference/standard-repo.md`; every ADR gained an **Alternatives considered** section (D48). |
| Archetypes should be `python-cli`, `python-lib`, `python-django-ng`, `python-fastapi-ng`; fold ADR-0009 into ADR-0006 | Done (D47). `-ng` means a pnpm-managed Nx workspace; `nx_cloud` is a config key; `backend` and `web_runner` are gone. Dependency defaults folded into the archetypes ADR. |
| `AGENTS.md` should be a static pointer to `CLAUDE.md` | Done in all three repos. `check_structure.py`'s docs-pointer rule was generalized to understand single-sourcing rather than demanding both files carry the links. |
| Add a Markdown formatting task | Done: `lint:markdown`, `format:markdown`, seeded `.mdformat.toml`. The earlier harvest note misread agentkit ADR-0014 — it makes the mdformat *config* repository-owned, not the task. `.rn-forge/kiln/standard.md` is excluded, because a formatter rewriting a kiln-owned file is two owners writing the same bytes. |
| Review `pyproject.toml` tool config against pykit/agentkit | Done: `--import-mode=importlib`, targeted test-file ignores instead of `["ALL"]`, `py.typed` markers, `ruff format --check` in the gate. No repo in the fleet uses mypy, and that fleet decision is now kiln ADR-0008. |
| Is there more standard boilerplate — logging, CLI config, arg parsing? | Yes, and it is the strongest argument for the library set. Written up as **ADR-0009 (proposed)**: tooling owns the boilerplate and the CLI surface is declared in config, not written. Code lands in Phase C/D; D2 still defers application generators. |

**From the codex review** — all eight, in `docs/plans/reviews/phase-b-codex.md`:
published packages lost their dependency source (fixed by pinned direct URLs,
D46); a failed release could never be retried (the release, not the tag, is now
the record, and the publish step creates the tag); Sonar's gate did not gate
(`qualitygate.wait=true`, and `release` needs `sonar`); CI could rewrite the
lockfile (`UV_LOCKED`); no `py.typed`; coverage bypassed per-package config and
collided on filenames (per-package runs, combined, verified to emit
`packages/*/src/...` paths Sonar can map); no format check and a blanket ruff
exemption for tests; fork pull requests ran a scan whose secret they cannot see.

### 0.7 Second feedback round (after §0.6 landed)

| Comment | Outcome |
| -- | -- |
| `format:python` runs `ruff format` before `ruff check --fix`, so lint fixes land unformatted | **Fixed** in all three repos. `check --fix` now runs first, then `format`; `lint:python` asserts the same pair in the same order. This was a real defect, not a style preference. |
| `lint` calling both `lint:python` and `lint:format` is asymmetric with `format` | **Fixed.** `lint:format` is gone; `lint:python` runs `ruff check` and `ruff format --check`, mirroring `format:python`. `required_validate` drops `quality:lint:format`. |
| Will the golden repo's `ADR-0001` be seeded into every repo? | **No.** Only `docs/adr/index.md` and `docs/adr/_structure.md` are seeded; the golden repo's own ADR is fixture content and is not in `state.json`. A new repo gets an empty, structured `adr/` area and writes its own first decision — the runbook covers that. |
| `scripts/` is a good candidate to package and add as a dev dependency | **Agreed, and settled as kiln ADR-0010 (accepted; D51).** 1,454 lines per repo, four of the seven checkers with no per-repo variation at all, and the remaining three varying only by lists already present in `config.toml`. Splitting `rn-forge-kiln-checks` from `rn-forge-kiln` keeps ADR-0003's real rule — CI never *renders* — while removing the duplication. The docs checkers move into tooling in Phase C; the four policy checkers become `rn-forge-kiln-checks` in Phase D, in the kiln repo alongside the CLI. |

### 0.8 What the Phase C review changed

Both reviews are in `docs/plans/reviews/`. This is the list, so a later session
does not re-derive it. Nothing here is a failure to follow the plan — the plan
said the wrong thing, and F8/F9 are the separate completion gap.

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
| A2 — docs extraction carried kiln policy into tooling | **Accepted in full; the cleanest finding in the review.** `docs/structure.py` hardcoding ADR numbering, epic/release naming and instruction filenames puts rn-forge policy inside a general-purpose library, contradicting ADR-0001 outright. Tooling keeps link, Markdown and nav *mechanics* and takes an explicit policy object; `rn-forge-kiln-checks` supplies it (Phase D). No generic validation framework. |
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
| commons' layout is not intuitive | **Done (D55).** Sub-packages by kind of mechanism, applied to commons, cli and tooling. §2.11. |

**Implementation defects.** Codex's F1–F14, verified where verification was
cheap. F1 (multi-block staging overwrites, and the repeated backup that breaks
rollback), F2 (`except Exception` lets Ctrl-C skip rollback), F3 (`Severity` is
a `StrEnum` compared with `is`, so a JSON round trip silently demotes an error)
and F4 (artifact paths escape the root and are written *before* any backup
exists) were each confirmed against `4624bfe`. They are scheduled as Phase C.2,
in §3.

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
and ADR-0009's declared `[cli]` surface, and no golden repo demonstrates either:
golden-cli still pins commons `v0.2.2` and does not use tooling at all (which is
F8, read as a plan gap rather than a defect). The missing acceptance test is
that **`golden-app` contains a working CLI with zero hand-written app
construction**. If that repo cannot be written, ADR-0009 is not ready to be
accepted, and that is better discovered now than after kiln's templates derive
from it.

### 0.5 Not covered

Product code, test strategy, runtime architecture. This is repo structure,
tooling ownership, and pipeline only.

______________________________________________________________________

## 1. Findings (evidence; compressed from revisions 1–3)

| # | Finding | Evidence | Resolved by |
| -- | -- | -- | -- |
| F1 | Three owners for `Taskfile.yml`; apollo broken now | apollo's uncommitted `taskkit adopt` dropped 5 lint gates; `ci.yml` calls `task api:install`, which no longer exists | one owner (kiln); apollo parked, rebuilt later with `kiln new` |
| F2 | Byte-identical scripts copied across repos; `check_ci_entrypoint.py` differs only in a list literal | `diff agentkit/scripts/check_task_layout.py apollo/scripts/check_task_layout.py` | generated, committed scripts with a config header (§2.2) |
| F3 | Four forks of the docs link checker | taskkit 171 lines, apollo 156, intellibench 165, agentkit 187 | one template in kiln |
| F4 | `taskkit adopt` replaces rather than reconciles | `extra_refs`, `ownership`, `command_overrides` all empty in apollo | moot — no adopt (D38); `gate.shrunk` doctor rule (§2.5.6 #8) |
| F5 | CI is unowned; four pipelines share nothing | only agentkit pins SHAs and sets `permissions:` | kiln `ci` module |
| F6 | intellibench is the richest standards donor and least standardized | 11 lints in `tools/lint/`, docs toolchain in `tools/docs/`, no CI | harvested into kiln templates (Phase B); intellibuild gets CI first |
| F7 | Docs area model exists in exactly one repo | taskkit has no `adr/`, `releases/`, `_structure.md` | `docs` module, applied to every generated repo |
| F8 | Skill/kit boundary unenforced | `go-task-setup` installs a script that `task lint` runs | no skill installs anything (D30) |
| F9 | Instruction files restate the standard in prose | apollo `CLAUDE.md` spends ~15 lines on docs layout | kiln managed block pointing at the rendered standard (§2.10) |
| F10 | Root-level session residue tracked | `agentkit/feedback.md`, `apollo/epic-design-docs-handoff.md`, `intellibench/ADR_REVIEW.md`, `intellibench/temp.txt` | not carried into rebuilt repos; `hygiene.stray-root-file` |
| F11 | No cross-repo compliance signal | — | `kiln doctor --all` |
| F12 | Kits duplicate runtime-neutral and local-tool mechanisms | both have `core/{state,config,paths,io}.py`; dep floors drifted (`typer>=0.26.8` vs `>=0.12`) | Phase C: commons/tooling boundary |
| F13 | apollo's config shape defeated detection | tool config at root pyproject, tasks emitted with `dir: apps/api` | archetype is asserted, never inferred (D23) |
| F14 | `.rn-forge/` umbrella has no owner | each kit writes its own gitignore block and root discovery | kiln owns the umbrella (D28) |
| F15 | taskkit refuses Nx | `nx.json` in `_UNSUPPORTED_MANIFESTS` (`discovery.py:51`) | moot — templates call `pnpm nx run-many`; no adapter needed |
| F16 | taskkit's detection layer is dead weight once the archetype is asserted | discovery + planner + adapters ≈ 1,950 of 5,248 lines; rendered output for taskkit's own repo ≈ 80 lines of YAML | D23 |
| F17 | pykit already holds most of what `forge-core` specified, but not at the right package boundary | commons correctly owns `PathUtils`, `ContentHash`, atomic writes, documents and entry-point loading; local `StateStore`, templates and Typer wiring landed there too | D29, D35 |
| **F18** | **A third of kiln's revision-6 spec existed only to reconcile pre-existing files** | `adopt`, `ADOPT`/`ADOPT_CONFLICT`, closure capture, gate-shrink preflight, the model-delta harness, `inventory.py`/`apply_mapping.py`, the docs-migration runbook | **D38, D39** — none of it is built |
| **F19** | **A separate canon repo had no reference mechanism** | revision 6 gave no way for an agent in agentkit or pykit to read canon; agentkit ADR-0018 already says rules live in the target repo | **D36** — kiln renders the standard into every repo (§2.10) |

______________________________________________________________________

## 2. Target architecture

### 2.1 Components and their dependency graphs

```
commons ──► cli ──► tooling ──► kiln
   │         │         │    └─► agentkit
   │         │         └──────► rn-forge-django[codegen]   (extra; never the runtime surface)
   │         └────────────────► every python-app / python-web-* repo
   └──────────────────────────► rn-forge-django, rn-forge-fastapi

kiln ──subprocess──► agentkit       (kiln may call agentkit; never the reverse)
kiln ──entry points─► *[codegen]    (kiln discovers generators; never imports a framework)
```

> **Library graph acyclic, tooling graph free.** `rn-forge-commons`,
> `rn-forge-cli` and `rn-forge-tooling` are the only rn-forge packages that are
> build dependencies of a kit, and each depends only downward. kiln and agentkit
> never import each other. pykit adopting kiln as dev tooling is not a cycle —
> nothing is imported.
>
> **Three layers, not two (D52).** commons is what a library, a service and a
> batch can all take. `rn-forge-cli` is what any program with a command line
> takes — including business batches and ML jobs, which is the case the first
> two-package split got wrong. `rn-forge-tooling` is what a program that
> installs itself, owns files in someone else's repo, or renders templates
> takes. The placement test is what an API's *signature* contains, not who
> happens to call it today ([ADR-0002](../adr/0002-the-dependency-graphs.md)).

**Codegen boundary (D37).** A framework's generators ship inside its runtime
package as an extra: `rn-forge-django[codegen]` installs `rn-forge-tooling`,
Typer and Jinja; the code lives in `rn_forge.django.codegen`, which the runtime
public surface never imports. Three guards make that a contract, not a habit:

1. `.importlinter` in pykit: `rn_forge.django` minus `rn_forge.django.codegen`
   is forbidden to import `rn_forge.tooling`, `typer`, `jinja2`.
1. `import rn_forge.django` succeeds with no extras installed (existing
   checklist rule).
1. Generators are registered under the entry-point group
   `rn_forge.kiln.generators` and are Python-callable without Typer; kiln
   supplies the command surface (`kiln generate django app billing`) in a
   later release (D2).

Agentkit and kiln each declare an `.importlinter` forbidden-import contract;
`rn_forge.commons` and `rn_forge.tooling` are the only permitted rn-forge peer
imports. `import-linter` is a dev dependency, an internal `quality:lint:imports`
task runs `uv run lint-imports`, root `lint` calls it, and CI reaches it through
`task validate`.

### 2.2 The CI model

> **All repo-specific logic that CI runs is committed. kiln is a developer-only
> generator and freshness checker; CI never installs or invokes it. CI installs
> pinned language toolchains and go-task, then invokes only committed `task`
> entrypoints and generated checkers.**

- A cold clone builds without kiln, agentkit, `$RNF_HOME`, or a custom
  bootstrap.
- Every generated file carries a provenance header:
  `# Generated by kiln <version> from .rn-forge/kiln/config.toml — do not edit; run 'kiln apply'`.
- Scripts that differ per repo by a list (F2) carry that list in a **config
  header block** immediately under the provenance header, rendered from the
  archetype and fenced by `# BEGIN kiln config` / `# END kiln config`. The
  script body after that fence is identical everywhere.
- `.rn-forge/kiln/state.json` is generated and committed. It contains each
  artifact's repo-relative path, kind, SHA-256, and (for blocks) exact fence
  markers, plus `kiln_version` and `config_hash`. It excludes itself from its
  artifact entries so it never hashes itself.
- `scripts/standards/check_generated.py` is a generated, committed, stdlib-only
  CI checker. It verifies whole-file hashes, managed-block body hashes and
  presence of seeded artifacts. The generated
  `scripts/task/check_task_layout.py` parses the task graph and verifies that
  the archetype's required verbs are reachable from `validate` (its header
  carries the list). Neither checker renders templates.
- CI detects disk drift against committed state. `kiln doctor` additionally
  renders current templates to detect whether config or a newer kiln version
  would update an artifact. `kiln apply` refuses unapproved drift.

### 2.3 The ownership rule

> **kiln owns anything deterministic. Config lives in
> `.rn-forge/kiln/config.toml`. Every managed file — or every fenced block
> inside a shared file — has exactly one owner.**

1. All repo-specific logic that CI runs is committed. Standard logic is
   generated by kiln; repo-specific logic remains repository-owned.
1. If a script differs per repo only by a list or a path, that list is config in
   the script's header, not a fork.
1. Two owners never write the same bytes. Shared files (`.gitignore`,
   `CLAUDE.md`, `AGENTS.md`) are partitioned into fenced blocks; each block
   has one owner; the file body belongs to whoever seeded it.
1. kiln may invoke agentkit as a subprocess. agentkit never knows kiln exists.
1. Judgement is not automated. Where a human or agent must decide, kiln's docs
   hold a **runbook**, not a skill.

### 2.4 Ownership table (normative — kiln ADR-0001)

| File / tree | Owner | Artifact kind |
| -- | -- | -- |
| `.rn-forge/kiln/config.toml` | repo (hand-edited input) | input |
| `.rn-forge/kiln/state.json` | kiln | generated, committed CI baseline; never hashes itself |
| `.rn-forge/kiln/standard.md` | kiln | managed — the rendered canon (§2.10) |
| `.rn-forge/kiln/backups/`, `rendered/` | kiln | gitignored derived data |
| `.rn-forge/agentkit/**` | agentkit | as today |
| `.gitignore` | repo body; `# BEGIN rn-forge kiln` block → kiln; `# BEGIN rn-forge agentkit` block → agentkit | block |
| `.editorconfig` | kiln | managed |
| `.importlinter` | kiln | managed import-boundary contracts |
| `Taskfile.yml`, `tasks/workspace.yml`, `tasks/quality.yml`, `tasks/docs.yml`, archetype namespace files (`tasks/api.yml`, `tasks/web.yml`) | kiln | managed |
| `tasks/self.yml` and any include declared `ownership = "repository"` | repo | seeded once, never rewritten |
| `scripts/task/check_task_layout.py`, `scripts/ci/check_ci_entrypoint.py` | kiln | managed (config header) |
| `scripts/standards/check_generated.py` | kiln | managed; stdlib-only CI checker |
| `scripts/docs/_common.py`, `check_docs.py`, `gen_nav.py`, `check_structure.py` | kiln (docs profile `mkdocs`) | managed |
| `docs/_areas.yml`, `docs/_structure.md`, `docs/adr/_structure.md` | kiln | **seeded** — repos may extend areas (D44) |
| `docs/index.md`, `docs/<area>/index.md` | kiln | **seeded** — written if absent, never touched again |
| `mkdocs.yml` | repo body; `# BEGIN generated nav` block → kiln | block |
| `.github/workflows/ci.yml`, `docs.yml`; `sonar-project.properties` | kiln | managed |
| `CLAUDE.md`, `AGENTS.md` | body seeded by agentkit; `<!-- BEGIN rn-forge kiln -->` block → kiln; agentkit's own block → agentkit | block |
| `.claude/**`, `.codex/**`, installed skills | agentkit | as today |
| Repo-specific lints (`check_brand.py`, `check_gate_tags.py`, …) | repo, wired via `[tasks.extra_refs]` | repo |

**D44 — `_areas.yml` and `_structure.md` are seeded, not managed.** intellibuild
needs a `context` area that agentkit's model does not have; the docs scripts
read the repo's copy anyway (agentkit ADR-0018). kiln seeds the reference model
and `doctor` validates the tree against whatever the repo declares.

### 2.5 kiln

#### 2.5.1 Package layout

```
rn-forge/kiln/
  docs/                    # the canon lives here — see §2.10
    adr/                   # 0001–0008 = the standard (from revision-6 U001–U008), then kiln's own
    reference/standard-repo.md
    architecture/workspace.md
    runbooks/creating-a-repo.md
    plans/standardization-plan.md     # this document moves here in Phase B
  src/rn_forge/kiln/
    cli.py                 # tooling build_app + --dry-run/--yes/--json
    config.py              # pydantic schema for config.toml (§2.5.2), load/validate
    umbrella.py            # .rn-forge/ discovery ($RNF_HOME, find_root markers), gitignore block
    artifacts.py           # kiln provider: repo-standardization artifacts and render inputs
    cycle.py               # thin adapter from kiln config to the tooling generation engine
    modules/
      scaffold.py          # archetype base: shell out to `uv init`/`pnpm create`/`nx g`, reconcile, .editorconfig
      tasks.py             # Taskfile + tasks/*.yml + scripts/task/*, scripts/ci/*, scripts/standards/*
      docs.py              # docs tree, _areas.yml, _structure.md, mkdocs.yml nav block, scripts/docs/*
      ci.py                # workflows, sonar-project.properties, pin set
      instructions.py      # CLAUDE.md / AGENTS.md managed block; .rn-forge/kiln/standard.md
    doctor/
      artifacts.py         # drift / stale / missing
      taskgraph.py         # ported from taskkit validator.py (§2.5.6 #5, #6, #8)
      ci_entrypoint.py
      docs.py
    archetypes/
      _shared/pins.toml
      python_app/  python_tool/  python_lib/    # templates + archetype.toml
      python_web_api/  python_web_app/               # (defaults, flags, forbidden_tools, required_validate)
  tests/
    fixtures/golden/       # one complete rendered repo per archetype (§2.6) — the snapshot oracle
      python-app/  python-tool/  python-lib/
      python-web-api/  python-web-app-django/  python-web-app-fastapi/
    fixtures/repos/        # moved from taskkit/tests/fixtures/repos (web archetype inputs)
```

Every module exposes the same two functions:
`artifacts(config) -> list[Artifact]` and
`checks(config, root) -> list[Finding]`. That is the whole internal contract,
and it is what keeps kiln from becoming a god-kit: a module is a template set
plus a doctor check, nothing more.

#### 2.5.2 `.rn-forge/kiln/config.toml` (kiln ADR-0004)

```toml
schema_version = 1

[repository]
name = "agentkit"                 # used in provenance headers, release tags
archetype = "python-tool"         # python-app | python-tool | python-lib
                                  # python-web-api | python-web-app
                                  # node-lib | node-web-app  (deferred)

[docs]
profile = "mkdocs"                # mkdocs | external | none
site_dir = ".docs-site"           # mkdocs only
external_url = ""                 # external only; surfaced in the instructions block

[ci]
provider = "github"               # github only in v1; "ado" reserved (D4)
sonar = true
release = "tag-exists"            # tag-exists | none

[tasks]
# Repo-owned includes kiln wires into the root Taskfile but never writes.
includes = [{ namespace = "self", taskfile = "tasks/self.yml" }]

[tasks.extra_refs]                # appended to the managed wrapper verbs
lint = ["self:check:dist"]
build = ["self:build:check-dist"]

[tasks.command_overrides]         # replace one primitive's shell line
"quality:test:python" = "uv run pytest -q -p no:randomly"

[archetype.python-lib]            # archetype-specific tables; one per archetype
packages = ["packages/rn-forge-commons", "packages/rn-forge-django"]

[archetype.python-app]            # or [archetype.python-tool]
packages = []                     # internal-only; never published

[archetype.python-web-api]
framework = "fastapi"             # fastapi (shipped) | django (untested)
api_dir = "apps/api"
admin_ui = false                  # a thin self-contained management surface

[archetype.python-web-app]
framework = "django"              # django | fastapi   (both shipped)
frontend = "angular"              # angular (shipped) | react | svelte (untested)
api_dir = "apps/api"
web_dir = "apps/web"
nx_cloud = false                  # an account decision, not a repo shape

[cli]                             # ADR-0009; rendered by kiln, read by rn-forge-cli
name = "agentkit"
options = ["json", "dry-run", "yes", "log-level"]
```

`framework` and `frontend` select an implementation library, never a topology
(D54). A value without a golden repo is `untested` and `kiln new` refuses it.

Validation: pydantic strict model; every failure reported with its dotted path
(taskkit's `parse_config` pattern), never just the first.

#### 2.5.3 Commands

| Command | Behaviour |
| -- | -- |
| `kiln new <dir> --archetype A [--docs P] [--framework F] [--frontend W] [--dry-run] [--yes] [--json]` | collect config in memory for a new repo; preview and write nothing unless `--yes`, which writes `config.toml` and runs scaffold + apply. Refuses a non-empty `<dir>`. |
| `kiln apply [--dry-run] [--json] [--force <artifact>]…` | the full sequence (§2.5.5); idempotent and non-interactive; re-run after editing `config.toml` or upgrading kiln; each forced path must name a reported conflict, drift, or missing managed artifact |
| `kiln doctor [--json] [--all <path>…]` | every check in §2.5.6; exit 1 on any error-severity finding |
| `kiln diff [<artifact>]` | unified diff of on-disk vs fresh render |
| `kiln version` | — |

There is no `adopt` (D38). A repo either was created by `kiln new` or is not a
kiln repo. **Flag parity is non-negotiable.** Every prompt has a flag; `--yes`
accepts defaults. Agents are the main callers; CI invokes committed generated
checkers through `task validate`, never this CLI.

#### 2.5.4 Artifact kinds and the cycle

`rn_forge.tooling.generation` owns the runtime-neutral artifact kinds, action
classification and transactional execution. It exposes a Python-callable
generator contract with no Typer types. kiln's `cycle.py` supplies kiln config,
render functions, state metadata and explicitly approved force paths, then
invokes that engine. The engine renders and classifies every artifact before any
write:

```
render(config) → new_hash
disk_hash      = ContentHash.of_file(path) or None
entry          = state.entries.get(key)
last_hash      = entry.content_hash if entry else None

kind=managed:
  absent, no entry                         → CREATE
  absent, entry                            → MISSING
  present, no entry                        → CONFLICT   (a hand-made file at a managed path)
  entry, disk==last==new                   → UNCHANGED
  entry, disk==last, last!=new             → UPDATE
  entry, disk!=last                        → DRIFT
kind=seeded:
  absent                                   → CREATE
  present                                  → SKIP (record presence; never hash content)
kind=block:
  no block, no entry                       → INSERT (file body untouched)
  block, no entry                          → CONFLICT
  entry, body==last==new                   → UNCHANGED
  entry, body==last, last!=new             → UPDATE (file body untouched)
  entry, block missing or body!=last       → DRIFT

state entry no longer rendered:
  managed absent / block missing           → FORGET
  managed, disk==last                      → DELETE (backup first)
  block, body==last                        → REMOVE block (file body untouched)
  seeded                                   → FORGET (never delete repo content)
  managed/block changed since last apply   → DRIFT
```

An unforced `CONFLICT`, `DRIFT` or `MISSING` aborts the entire preflight before
state or artifacts are written. `--force <artifact>` approves only that reported
path; forcing `MISSING` recreates it. `--yes` never implies force. `kiln new`
into an empty directory only ever sees `CREATE`, `INSERT` and `SKIP` (after the
scaffold step has run `uv init` and the like).

Approved writes are staged under `.rn-forge/kiln/rendered/`, backups go to
`.rn-forge/kiln/backups/<UTC timestamp>/<repo-relative path>`, and atomic
replacements begin only after every render and check succeeds. On a write or
post-apply check failure, kiln restores backups and removes newly created
artifacts. The committed `state.json` is excluded from artifact enumeration and
written last; a failed transaction restores its previous bytes. State uses
tooling `StateStore` with commons-owned JSON value types and hashing; metadata
is `kiln_version: str` and `config_hash: str`. Managed entries store `path`,
`kind`, and `content_hash`; block entries also store their exact begin and end
markers; seeded entries store presence but no content hash.

#### 2.5.5 Apply sequence

```
1. umbrella     .rn-forge/kiln/, gitignore block, .editorconfig
2. scaffold     (new only) uv init / pnpm create / nx g, then reconcile to archetype
3. docs         tree, _areas.yml, _structure.md, mkdocs.yml block, scripts/docs/*
4. tasks        Taskfile.yml, tasks/*.yml, scripts/task/*, scripts/ci/*, scripts/standards/*
5. ci           workflows, sonar-project.properties
6. agentkit     subprocess: `agentkit project init` if .rn-forge/agentkit absent, else `agentkit project update`
7. instructions CLAUDE.md / AGENTS.md kiln block (after 6 so the files exist); .rn-forge/kiln/standard.md
8. doctor       run every check; apply exits non-zero if any error remains
```

Step 6 is skipped with a warning if `agentkit` is not on `PATH`.

#### 2.5.6 Doctor checks (each a stable `Finding.code`)

| # | Code prefix | Check |
| -- | -- | -- |
| 1 | `config.*` | `config.toml` parses and validates |
| 2 | `artifact.missing` / `.drift` / `.stale` | every managed artifact present; disk hash == committed last-applied; last-applied == fresh render |
| 3 | `artifact.seed-missing` | every seeded artifact present |
| 4 | `block.missing` / `.stale` | every fenced block present and current |
| 5 | `taskgraph.*` | ported from taskkit `validator.py`: exact public surface (§2.6), root file holds wrappers only, inner tasks are internal except `docs:*`, every task has `desc`, every include exists, every `task:` ref resolves, no cycles, no reserved-namespace collision |
| 6 | `taskgraph.unresolved-ref` | every `task <name>` in `.github/workflows/**`, `CLAUDE.md`, `AGENTS.md` resolves against `task --list-all` |
| 7 | `ci.entrypoint` | no forbidden tool, including `kiln`, invoked directly in any workflow (list from `archetype.toml`) |
| 8 | `gate.shrunk` | the set of tasks reachable from `validate` ⊇ the archetype's `required_validate` list; the generated `check_task_layout.py` enforces the same list in CI |
| 9 | `ci.unpinned` / `ci.permissions` | every `uses:` is SHA-pinned with a version comment; every job has `permissions:` |
| 10 | `docs.structure` / `.nav` / `.links` | tree matches the repo's `_areas.yml`; nav block current; no broken links/anchors/orphans |
| 11 | `hygiene.stray-root-file` (warning) | tracked root-level `*.md` not in the allow-list (`README.md`, `CLAUDE.md`, `AGENTS.md`, `LICENSE`, `CHANGELOG.md`) |
| 12 | `legacy.kiln-state` (error) | a pre-existing `.rn-forge/kiln/` or `$RNF_HOME/kiln/` tree without `schema_version` (§0.4) |

`kiln doctor --all <paths>` runs the same checks over many repos and prints one
table (F11).

### 2.6 Archetypes, golden repos and the docs profile (kiln ADR-0005)

| Archetype | Shape | Model repo (prior art) | Golden fixture | Release tag |
| -- | -- | -- | -- | -- |
| `python-app` | uv single package, src layout, optional internal-only workspace packages | intellibuild batches | `golden/python-app` | `v<version>` |
| `python-tool` | as `python-app` + self-install, `$RNF_HOME`, local state, plugins, doctor | agentkit, kiln | `golden/python-tool` | `v<version>` |
| `python-lib` | uv workspace of published library packages; per-package verify + release | pykit | `golden/python-lib` | `<package>-v<version>` |
| `python-web-api` | uv workspace, one API service, no separate frontend package; optional thin admin UI | — | `golden/python-web-api` (fastapi) | `v<version>` |
| `python-web-app` | uv workspace + API + pnpm-managed Nx frontend, one MkDocs site over both | apollo, intellibench `docs2/` | `golden/python-web-app-django`, `golden/python-web-app-fastapi` | `v<version>` |
| `node-lib` | pnpm/Nx workspace of published UI libraries | ngkit | *deferred* | `<package>-v<version>` |
| `node-web-app` | standalone pnpm-managed Nx frontend against remote APIs | — | *deferred* | `v<version>` |

**Flags, not archetypes, for the implementation library (D54).**
`--framework django|fastapi` on the web archetypes and
`--frontend angular|react|svelte` on `python-web-app` change neither the file
topology nor the task graph, which is the whole rule. Every shipped value has a
golden repo; a value without one is `untested = true` and `kiln new` refuses it.
v1 ships `python-web-app` with `django + angular` and `fastapi + angular`, and
`python-web-api` with `fastapi`. Six golden repos, not the fourteen the matrix
could name.

**Golden repos are the source of truth for templates (D43).** Each golden
fixture is a complete, hand-authored, *runnable* repo: `uv sync` and
`task validate` pass in it standalone, its workflows lint, its docs site builds
`--strict`, and its committed checkers run. They are reviewed as if they were
the finished product *before* any generator code exists (Phase B). The templates
are then the golden output parameterized, and kiln's snapshot tests assert
`render(golden config) == golden bytes` (provenance version rendered as the
literal `golden`). A template change that is not first made in the golden repo
is a bug.

**Docs profile** is orthogonal to archetype: `mkdocs` seeds the full area model
(from agentkit's `_areas.yml`: architecture, guides, runbooks, reference,
releases, specs, adr); `external` generates nothing but records `external_url`
in the instructions block; `none` generates nothing. Repos extend the seeded
`_areas.yml` themselves (D44).

**Template inventory** (✔ = generated for that archetype; d = only when
`docs.profile = mkdocs`; s = only when `ci.sonar`):

| Artifact | app | tool | lib | web |
| -- | -- | -- | -- | -- |
| `.editorconfig`, `.gitignore` block, instructions block, `.rn-forge/kiln/standard.md` | ✔ | ✔ | ✔ | ✔ |
| `Taskfile.yml` (10 root wrappers: `setup validate lint format typecheck test test:coverage build clean version`; public `docs:build docs:serve docs:nav docs:structure` only for `mkdocs`) | ✔ | ✔ | ✔ | ✔ |
| `tasks/workspace.yml` (`install`, `build`, `version`, `clean`) | ✔ | ✔ | ✔ | ✔ |
| `tasks/quality.yml` (internal `lint:python lint:generated lint:imports lint:task-layout lint:ci-entrypoint lint:docs* format:python typecheck:python test:python test:coverage`) | ✔ | ✔ | ✔ (per-package `uv run --package`) | ✔ (api side) |
| `tasks/web.yml` (`lint test build dev` via `pnpm nx run-many -t …` or `pnpm run …`) |  |  |  | ✔ |
| `tasks/docs.yml` (`build serve nav structure`) | d | d | d | d |
| `.importlinter` contracts; `scripts/standards/check_generated.py` | ✔ | ✔ | ✔ | ✔ |
| `scripts/task/check_task_layout.py` — header list: the archetype's `required_validate` | ✔ | ✔ | ✔ | ✔ |
| `scripts/ci/check_ci_entrypoint.py` — header list: app/tool/lib `uv pytest ruff pyright mkdocs lint-imports kiln`; web adds `pnpm npx nx` | ✔ | ✔ | ✔ | ✔ |
| `scripts/docs/{_common,check_docs,gen_nav,check_structure}.py` | d | d | d | d |
| `docs/_areas.yml`, `docs/_structure.md`, `docs/adr/_structure.md`, seeded index pages, `mkdocs.yml` nav block | d | d | d | d |
| `.github/workflows/ci.yml` (validate → sonar → check-version → build → publish) | ✔ | ✔ | ✔ (matrix over `packages`) | ✔ (+ pnpm/node setup) |
| `.github/workflows/docs.yml` (Pages deploy on main) | d | d | d | d |
| `sonar-project.properties` | s | s | s | s |

CI templates bake in the F5 fixes: SHA-pinned actions with version comments,
least-privilege `permissions:` per job, `concurrency:` per ref, tag-exists
release check (D22). The pin set lives in `archetypes/_shared/pins.toml`;
Dependabot watches kiln, not the generated workflows (D21).

**Scaffolding shells out.** `kiln new` runs `uv init`, `pnpm create`, `nx g` and
then reconciles the result (move files, fix pyproject sections). It never
templates another tool's scaffold output (D16).

### 2.7 No docs migration

Revision 6 specified an inventory script, a mapping-apply script and a migration
runbook. With D39 none of them has a customer: intellibuild's docs are `docs2/`
landing as `docs/` (already in the area model), agentkit's docs are carried by
hand into the rebuilt repo, pykit's docs stay where they are.
`docs.unclassified` is not a doctor check; `docs.structure` failing on an
unknown directory is the whole signal.

### 2.8 pykit Part D and tooling extraction

The commons upgrade implemented several local-development APIs before their
runtime boundary was reviewed. Phase C first separates those APIs, then adds the
small shared capabilities below to their correct owners:

| Item | Owner/module | Replaces |
| -- | -- | -- |
| `ManagedBlock(name, *, comment="#")` with `render(text, body) -> str`, `remove(text) -> str`, `extract(text) -> str \| None`; supports `#` and `<!-- -->` fences | commons `blocks.py` | agentkit `project_command._scaffold_gitignore`, taskkit `io.update_gitignore_block`, `gen_nav.py` marker logic |
| `Finding(code, severity, message, path=None, line=None, details=field(default_factory=dict))` + `Severity` StrEnum; `DataclassMixin` for `--json` | commons `findings.py` | taskkit `validator.Finding`, agentkit `doctor.CheckResult` |
| Recursive `JsonValue` alias | commons `_typing.py` | duplicated JSON metadata annotations |
| `DryRunOption`, `YesOption`; `CliOptions.dry_run`, `.yes` | tooling `cli.py` | both kits' per-command flags |
| `StateStore(..., metadata: Mapping[str, JsonValue] \| None)` written beside `schema_version`/`entries`; `metadata` property on load; canonical JSON output with sorted mapping keys | tooling `state.py` | taskkit's `taskkit_version`/`config_hash` envelope fields |
| `generation.py` — artifact kinds, the §2.5.4 classification, staged/backed-up/atomic transactional execution, Typer-free generator protocol | tooling `generation.py` | agentkit `project_command` apply loop, taskkit `planner` write path |

**The boundary, as corrected by the Phase C review (D52).** The first pass moved
one set out of commons; C.2 moves it into two packages and moves two things
back:

| API | Home | Reason |
| -- | -- | -- |
| Typer helpers, `AppConsole`, standard options, logging wiring, error-to-exit-code, the `[cli]` surface | **`rn-forge-cli`** | the process and command-line shape; every CLI wants it, including batches |
| `generation`, `TemplateEngine`, `StateStore`, `install`, `extract_archive`, docs *mechanics* | **`rn-forge-tooling`** | owns files, installs, or renders; only `python-tool` and kiln/agentkit need it |
| `DirectoryLock`, `atomic_symlink` | **back to commons** (`fs/locks.py`) | no installer policy in the signature; a local worker can serialize filesystem work or publish a snapshot atomically |
| `ManagedBlock` | **stays in commons** (`fs/blocks.py`) | a byte-preserving fenced-span edit; the current callers are all dev tools because they are the only current callers |
| `Finding`, `Severity`, `JsonValue`, `utils.py`, `EntryPointLoader`, `PathUtils`, `ContentHash`, documents, integration protocols, resilience | **commons** | unchanged; generalize `Finding`'s wording so paths need not be repo-relative and severity need not dictate exit policy |
| ADR numbering, epic/feature/release naming, instruction filenames in `docs/structure.py` | **`rn-forge-kiln-checks`** (Phase D) | rn-forge policy, which ADR-0001 says is kiln's; tooling takes an explicit policy object instead (A2) |

Do not leave compatibility re-exports in either direction: commons must never
import cli or tooling, and cli must never import tooling. `.importlinter` holds
all three contracts.

**Kiln-owned:** `$RNF_HOME`, the `.rn-forge/` layout, `config.toml` schemas,
archetypes, golden repos and product policy. The generic template and generator
engines are tooling-owned; kiln owns their repo-standardization inputs and
command surface.

**Codegen (D37, replaces revision 6's separate provider packages):**
`rn-forge-tooling` owns the generator engine; `rn-forge-django[codegen]` owns
Django templates and option schemas under `rn_forge.django.codegen`, registered
in the `rn_forge.kiln.generators` entry-point group; kiln discovers them and
supplies Typer commands. The runtime surface of `rn_forge.django` never imports
`codegen`, tooling, Typer or Jinja — enforced by import-linter in pykit (§2.1).
A FastAPI runtime package, when it exists, follows the same shape. Nothing in
this plan builds a generator (D2); it only fixes where one will live.

### 2.9 agentkit after this plan

Rebuilt from scratch in Phase F.3 by
`kiln new agentkit --archetype python-tool`, with its source rewritten on
commons and tooling. Unchanged in *scope*: global and project agent
configuration, hooks, adapters, instruction-file seeding, generic skills
(`gh-fix`, `python-simplify`, `sonar-cleanup`). Carried: ADRs 0001–0021 as
decisions, E17's area model (now owned by kiln's `docs` module), its tests as
the behavioural spec. Not carried: `core/**` (tooling), the four setup skills
and their assets, `scripts/**` (generated), `feedback.md`. The skill entry-point
distribution mechanism (revision 3 §2.9) is **not built**.

### 2.10 The canon inside kiln (D36)

The standard has three forms, all owned by kiln, and one rendering mechanism:

| Form | Where | Audience |
| -- | -- | -- |
| **Decisions** — ADR-0001…0008 (revision-6 U001–U008) | `kiln/docs/adr/` | kiln's maintainers; anyone asking *why* |
| **Spec** — `standard-repo.md`: public task surface, import boundary, committed state/checker contract, what `task validate` proves without kiln, what `kiln doctor` adds | `kiln/docs/reference/standard-repo.md` | the normative text; source for the rendered copy |
| **Rendered standard** — the spec rendered with the repo's archetype, docs profile and task surface filled in | `.rn-forge/kiln/standard.md` in **every** kiln repo | agents and humans working *in that repo*; linked from the kiln block in `CLAUDE.md`/`AGENTS.md` |

The ADRs, in the numbering the kiln repo uses:

| ADR | Decision |
| -- | -- |
| 0001 | the ownership rule (§2.3) — promotes agentkit ADR-0021 and revises it to per-file-or-block |
| 0002 | the ownership table (§2.4), normative |
| 0003 | the dependency graphs, the codegen boundary and executable `.importlinter` contracts (§2.1) |
| 0004 | the CI model — generated, committed checkers and state baseline; kiln absent from CI (§2.2) |
| 0005 | the `.rn-forge/` umbrella layout, config schema (§2.5.2), committed state schema |
| 0006 | the archetype catalogue, golden repos as template source of truth, docs profile (§2.6) |
| 0007 | judgement is a runbook, not a skill; no skill installs anything (D30); no adopt — repos are created, never migrated (D38, D39) |
| 0008 | the task vocabulary: ten root wrappers (`setup`, `validate`, `lint`, `format`, `typecheck`, `test`, `test:coverage`, `build`, `clean`, `version`), plus public `docs:build`, `docs:serve`, `docs:nav`, `docs:structure` for the `mkdocs` profile. Every other inner task is internal. `validate` calls `lint`, `typecheck`, `test`, and, only for `mkdocs`, `docs:build` |

Workspace-level material that is not a kiln decision — the pykit design
principles, the component map (§0.2), the two dependency graphs — lives in
`kiln/docs/architecture/workspace.md` and is referenced, not repeated, from
pykit and agentkit. Runbook: `docs/runbooks/creating-a-repo.md` (`kiln new`,
choosing an archetype for an odd repo, wiring `extra_refs`).

### 2.11 Package layout inside the three libraries (D55)

Commons is 7,274 lines across 23 flat modules, and the flatness is the problem:
`utils.py`, `objects.py`, `tasks.py` and `collections.py` sit at the same level
and mean four unrelated things. Grouping by *kind of mechanism* makes the answer
to "where does this go" readable off the tree.

**Rule: modules are grouped; public class names do not move.** `PathUtils`,
`DictUtils`, `AppLogger`, `Finding` and the rest keep their names and stay
re-exported from the package facade, so `from rn_forge.commons import PathUtils`
is unaffected. What changes is the submodule path. There are no compatibility
shims — pre-v1, three consumers, and D39 already says rebuild rather than
migrate.

```text
rn_forge/commons/
  __init__.py        facade — the cheap, always-available symbols
  exceptions.py      AppException
  findings.py        Finding, Severity
  config.py          Config
  testing.py         assert_that, soft_assertions, output_path
  lang/              collections.py  dataclasses.py  reflection.py
                     types.py (was _typing)  utils.py (AppUtils, Base64)
  fs/                paths.py (PathUtils)  hashing.py (ContentHash)
                     locks.py (DirectoryLock, atomic_symlink)  ← back from tooling
                     blocks.py (ManagedBlock)  documents.py
  data/              pandas.py  excel.py
  logging/           __init__.py (AppLogger, LoggingConfig, TRACE)  structlog.py
  runtime/           environment.py  subprocess.py (Process)  tasks.py (Task, TaskPool)
                     plugins.py (EntryPointLoader)
  integration/       messaging.py  objects.py  secrets.py  resilience.py

rn_forge/cli/
  __init__.py        facade
  app.py             build_app — the Typer application factory
  options.py         --json --dry-run --yes --log-level; command_options
  console.py         AppConsole
  errors.py          error → exit code
  declare.py         reads the [cli] surface (ADR-0009)

rn_forge/tooling/
  __init__.py        lazy facade — no eager import of jinja2
  generation/        artifacts.py  plan.py  apply.py
  templates.py       TemplateEngine
  state.py           StateStore
  install/           archive.py (extract_archive)  home.py ($RNF_HOME)  install.py
  docs/              markdown.py  links.py  nav.py  areas.py  site.py
                     policy.py    ← the injected policy protocol (A2)
                     structure.py ← mechanics only
  cli/               tooling's own command surfaces (rn-forge-docs)
```

Two things this layout does not pretend to fix. `AppUtils` remains a genuine
grab bag (`parse_bool`, `is_empty`, `get_or_default`, `import_string`,
`null_safe_attrgetter`, `join_string`, `unified_diff`); splitting it would break
a public class name for little gain, so it stays whole in `lang/utils.py` and
new helpers must justify not going into a named module instead. And several
submodule names shadow stdlib ones — `collections`, `dataclasses`, `logging`,
`subprocess`, `pandas` — which the flat layout already did; Python 3's absolute
imports handle it, and the intuitive name is worth more than the shadow costs.

______________________________________________________________________

## 3. Plan of action

Each phase lists: repo/branch, steps, and an **acceptance** block that is a
command plus its expected result. A phase is done when its acceptance passes.
Nothing is committed or pushed by an implementer without being asked; each phase
leaves the working tree for review.

### Phase A — stabilize pykit Part C *(hours; do first)*

Repo `rn-forge/pykit`, branch `feature/upgrade`. Sixty-four uncommitted files is
context rot waiting to happen; this phase makes them reviewable. **No release,
no boundary change.**

1. `uv sync --all-extras && uv run pytest packages/rn-forge-commons -q`; fix
   failures.
1. `uv run ruff check . && uv run ruff format --check . && uv run pyright`; fix.
1. Classify every Part C public symbol with a one-line comment block at the top
   of `commons/__init__.py`:
   `# tooling-bound (Phase C): cli, console, state, templates` so the
   temporary commons locations are visibly not a published API.
1. Update `CLAUDE.md`'s commons bullet to match reality (it still says
   `verboselogs`/`coloredlogs`).
1. Stage the result as one reviewable commit on `feature/upgrade`.

**Acceptance**

```bash
cd rn-forge/pykit
uv run pytest packages/rn-forge-commons -q
uv run ruff check . && uv run ruff format --check . && uv run pyright
grep -q 'tooling-bound' packages/rn-forge-commons/src/rn_forge/commons/__init__.py
git status --porcelain | wc -l        # 0 after the commit
```

### Phase B — kiln repo: canon and golden repos, no generator code *(1 week)* — **done**

> Executed. The archetype names below are the revision-8 ones;
> `golden/python-cli` is renamed to `golden/python-tool` and joined by
> `golden/python-app` in Phase C.2 (D53). Left as written, as the record of what
> was built.

New repo `rn-forge/kiln`. Bootstrap its own skeleton by **hand-copying the
`python-cli` golden repo** once it exists (step 3); kiln regenerates itself in
Phase D. Two deliverables, both reviewed by the owner before Phase C starts.

1. **Docs — the canon (§2.10).** `docs/adr/0001…0008.md`, each ≤ 1 page, Context
   / Decision / Consequences, harvested from §0.3's donors (cite the donor ADR
   in Context). `docs/reference/standard-repo.md`.
   `docs/architecture/workspace.md`. `docs/runbooks/creating-a-repo.md`. Move
   this document to `docs/plans/standardization-plan.md` and leave a one-line
   pointer at `rn-forge/STANDARDIZATION-PLAN.md`.
1. **Harvest inventory.** Before writing golden files, produce
   `docs/plans/harvest.md`: for each donor script or lint in §0.3, one row —
   donor path, behaviour kept, behaviour dropped, target golden path. This is
   the review artifact for "everything common and worth carrying over".
1. **Golden repos** under `tests/fixtures/golden/`: `python-cli/` (name
   `golden-cli`), `python-lib/` (`golden-lib`, two trivial packages),
   `python-django-ng/` and `python-fastapi-ng/` (`golden-web`; the web
   fixtures may ship in Phase E if they slow this phase). Each is a complete
   repo per the §2.6 inventory with `docs.profile = mkdocs` and
   `ci.sonar = true`, hand-written provenance headers reading `kiln golden`, a
   hand-written `state.json`, a one-function package with one test, and a
   `.rn-forge/kiln/standard.md` rendered by hand from the spec. Scripts are
   written **once**, in `python-cli`, and copied byte-identical (below the
   config header) into the others — `assert_generated_bodies.py` (step 4)
   proves it.
1. `tests/support/assert_generated_bodies.py` — strips provenance and the
   `# BEGIN kiln config` … `# END kiln config` header, prints each body's
   SHA-256, fails unless all supplied files share one body.
1. Review loop with the owner: read every golden file as if it were the finished
   repo. Changes go into the golden repo, never "later in the template".

**Acceptance**

```bash
cd rn-forge/kiln
uv run --group docs mkdocs build --strict
test -f docs/adr/0007-task-vocabulary.md && test -f docs/reference/standard-repo.md && test -f docs/plans/harvest.md
for g in tests/fixtures/golden/python-cli tests/fixtures/golden/python-lib; do
  (cd "$g" && uv sync && task validate && uv run python scripts/standards/check_generated.py . \
     && python scripts/ci/check_ci_entrypoint.py . && python scripts/task/check_task_layout.py . \
     && uv run --group docs mkdocs build --strict) || echo "FAIL $g"
done
uv run python tests/support/assert_generated_bodies.py --relative-path scripts/ci/check_ci_entrypoint.py tests/fixtures/golden/*
uv run python tests/support/assert_generated_bodies.py --relative-path scripts/standards/check_generated.py tests/fixtures/golden/*
actionlint tests/fixtures/golden/*/.github/workflows/*.yml
```

### Phase C — tooling extraction, Part D, generation engine *(1 week)* — **first pass landed, revised**

> pykit `4624bfe`. Reviewed; §0.8 is the outcome. The boundary this section
> describes is corrected by D52 and the addendum below is completed by **Phase
> C.2**, which follows. Left as written, as the record of what was attempted.

Repo `rn-forge/pykit`, branch `feature/upgrade`. Follows
`commons-upgrade-plan.md` → "Final package boundary" and Phase 18.4. Scope the
engine to what the golden repos need — every artifact kind and action in §2.5.4
has a golden example by now, and nothing else exists.

**kiln ADR-0010 is settled (D51).** The four docs checkers (`check_docs`,
`check_structure`, `gen_nav`, `_common` — 775 lines with no per-repo variation)
**are** part of what this phase extracts into tooling; the four policy checkers
go to `rn-forge-kiln-checks` in Phase D. Extract the docs checkers here, not
later, or they get moved twice.

**Added after the Phase B review.** The golden repos depend on
`rn-forge-commons` at a pinned tag and use it; `rn-forge-tooling` could not be
wired because it does not exist yet. This phase must therefore also:

1. **Split commons against ADR-0009's target**, not symbol by symbol. The Typer
   helpers, `AppConsole`, `StateStore` and `TemplateEngine` move to tooling as
   one coherent surface, because the point of tooling is that a repo takes its
   whole CLI/console/state layer from it rather than assembling one.
1. Add `rn-forge-tooling` to `tests/fixtures/golden/python-cli` and to kiln's
   own `pyproject.toml`, as a pinned direct URL in `dependencies` (D46), and
   make golden-cli *use* it — a dependency the fixture does not exercise
   proves nothing.
1. Add it to `REQUIRED` in each affected
   `scripts/standards/check_rn_forge_deps.py` config header, and re-seed
   `.rn-forge/kiln/state.json` in every repo it touches.
1. Re-point the golden repos' commons pin at the first release cut *after* the
   Part C/D boundary split. The golden repos deliberately use only
   commons-owned APIs today (`DictUtils`, `ListUtils`), so this should be a
   version bump and nothing else — if it is not, the boundary moved something
   it said it would keep.
1. Set kiln's own `REQUIRED` to `["rn-forge-commons", "rn-forge-tooling"]` once
   kiln has source that imports them (Phase D).
1. Cut the first `rn-forge-tooling` release tag before any of the above, since
   every consumer pins to a tag.

### Phase C.2 — the layer split, the re-layout, and the defect fixes *(1 week)*

Repos `rn-forge/pykit` (`feature/upgrade`) and `rn-forge/kiln` (`feature/v1`).
This is what the Phase C review produced (§0.8). The executable form lives in
pykit's `docs/plans/commons-upgrade-plan.md`, at the **"Part D — resume here"**
marker; that document is the one an implementer follows. This section is the
scope and the acceptance.

**Order matters.** Correctness first, because the defects are in the code that
is about to be moved and a move makes them harder to attribute; then the split;
then the re-layout; then the consumers.

1. **Defect fixes, in pykit, before anything moves.**
    - **F1 + F6 together** — group staged changes by destination, compose block
      edits against one evolving buffer, back up and write each file once,
      reject incompatible whole-file and block ownership of one path, and
      preserve the unowned prefix, suffix and newline sequences. They share an
      implementation; fixing one without the other is rework.
    - **F2** — roll back on `BaseException`, then re-raise interruption without
      converting it to an application failure.
    - **F3** — fix `DataclassMixin` so deserialization reconstructs and validates
      enum fields, then audit every dataclass with an enum field. Not a
      `Finding` patch.
    - **F4** — normalize and validate artifact and stale-state paths under the
      repo, staging and backup roots *before* any mutation, using the existing
      path guards.
    - **F5** — keep the intended deletion separate from the blocking drift
      classification, and execute it once approved.
    - Tests for each: two inserts, two updates, removal-plus-update, CRLF and
      absent terminal newline, interruption after a replacement, JSON round
      trip with an unknown severity, absolute and `..` and symlink artifact
      paths.
1. **Split the development layer (D52).** New package `rn-forge-cli`, module
   `rn_forge.cli`: `build_app`, `AppConsole`, the standard options, logging
   wiring, error-to-exit-code, `declare.py`. `rn-forge-tooling` keeps
   generation, templates, state, install and docs mechanics and gains a
   dependency on `rn-forge-cli`. `DirectoryLock` and `atomic_symlink` go back
   to commons. `ManagedBlock` stays. Three `.importlinter` contracts hold the
   layering.
1. **Extract the docs policy (A2).** `docs/structure.py` keeps link, Markdown
   and nav mechanics and takes a policy object; the ADR numbering, epic /
   feature / release naming and instruction filenames become the caller's.
   kiln supplies them from `rn-forge-kiln-checks` in Phase D; until then a
   default policy lives in kiln's fixtures, not in tooling.
1. **Re-layout all three packages (§2.11, D55).** Modules move; public class
   names do not; no compatibility re-exports.
1. **F10, F11, F12, F13 while the code is open.** Diagnostic logging to stderr
   from initialization so `--json` is parseable wherever the flag sits; nav
   values serialized with the YAML library; the anchor checker calling
   Python-Markdown's own slug and unique-id logic instead of reimplementing
   it, plus reference links and fenced-code awareness; `docs nav --json`
   emitting a result.
1. **F7 — CI.** Add `rn-forge-cli` and `rn-forge-tooling` to package
   verification, build, release and coverage in pykit's `main.yml`, and run
   `lint-imports` as a required gate. Necessary now even though Phase F
   regenerates the skeleton: an unenforced import contract is not a contract.
1. **F9 + F14 — the release contract and the instructions.** `rn-forge-cli` and
   `rn-forge-tooling` declare their commons dependency as a pinned direct URL
   under D46, and the installation guides describe that model rather than
   `uv add`. Smoke-test an install outside the workspace. Reconcile pykit's
   `AGENTS.md` to be a pointer to `CLAUDE.md`, per §0.6.
1. **Rename the golden repos and add the missing ones (D53).**
   `golden/python-cli` → `golden/python-tool`; a new `golden/python-app`.
   `golden/python-lib` is unchanged. Update kiln's own
   `.rn-forge/kiln/config.toml` to `python-tool`, re-render
   `.rn-forge/kiln/standard.md`, and **re-seed `state.json`**.
1. **Close Phase C's addendum (F8).** Cut the first `rn-forge-cli` and
   `rn-forge-tooling` releases; point `golden/python-app` at `rn-forge-cli`
   and `golden/python-tool` at both; re-point every commons pin at the release
   cut after the boundary change; update each `check_rn_forge_deps.py`
   `REQUIRED` header; re-seed every `state.json`.
1. **The acceptance test ADR-0009 never had.** `golden/python-app` contains a
   working CLI with **zero hand-written app construction** — a `main()`, its
   commands, its tests, and nothing else. If that repo cannot be written,
   ADR-0009 is not ready and D49 stays proposed.

**Acceptance**

```bash
cd rn-forge/pykit
uv sync --all-extras
uv run pytest -q                      # including the new tests for F1–F6
uv run ruff check . && uv run ruff format --check . && uv run pyright
uv run lint-imports                   # commons ⊅ cli ⊅ tooling, + the codegen fence
! rg -q 'rn_forge\.(cli|tooling)' packages/rn-forge-commons/src
! rg -q 'rn_forge\.tooling' packages/rn-forge-cli/src
! rg -q "'adr'|'releases'|specs/epics" packages/rn-forge-tooling/src/rn_forge/tooling/docs/structure.py

cd ../kiln
for g in tests/fixtures/golden/python-app tests/fixtures/golden/python-tool tests/fixtures/golden/python-lib; do
  (cd "$g" && uv sync && task validate) || echo "FAIL $g"
done
rg -q 'rn-forge-cli' tests/fixtures/golden/python-app/pyproject.toml
rg -q 'rn-forge-tooling' tests/fixtures/golden/python-tool/pyproject.toml
task lint                             # state baseline agrees after the re-seed
```

### Phase D — kiln: config, engine adapter, CLI, doctor, self-hosting *(2 weeks)*

Repo `rn-forge/kiln`. Package `rn-forge-kiln`, module `rn_forge.kiln`, depends
on `rn-forge-commons>=0.4.0`, `rn-forge-tooling>=0.1.0`, `pydantic`, `typer`;
`import-linter` in the dev group.

1. `config.py` — the §2.5.2 schema; tests for every validation failure with its
   dotted path.
1. `umbrella.py` — `find_root` with markers `.rn-forge/kiln/config.toml`,
   `.git`; `rnf_home()`; gitignore block via `ManagedBlock`;
   `legacy.kiln-state` detection (§0.4).
1. `archetypes/python_app/`, `python_tool/`, `python_lib/` — templates derived
   from the golden repos; `archetype.toml` with `forbidden_tools` and
   `required_validate`.
1. `artifacts.py`, `cycle.py` — kiln provider and thin adapter over tooling
   `generation`. **Snapshot tests:** for each golden fixture, load its
   `config.toml`, render with `kiln_version="golden"`, assert every artifact
   equals the golden bytes and the classification of a fresh directory is all
   `CREATE`/`INSERT`/`SKIP`; applying twice yields all `UNCHANGED`.
1. `modules/{scaffold,tasks,docs,ci,instructions}.py` and `cli.py` — `new`,
   `apply`, `doctor`, `diff`, `version` with the §2.5.3 flags. Test `new` with
   stdin closed and every flag given.
1. Doctor checks 1–12. `doctor/taskgraph.py` ported from taskkit `validator.py`
   with its tests; `doctor/docs.py` reads the repo's `_areas.yml`.
1. `.importlinter` for `rn_forge.kiln` forbidding `rn_forge.agentkit`,
   `rn_forge.django`, `rn_forge.taskkit`.
1. **Self-hosting.** Write `.rn-forge/kiln/config.toml` for kiln itself
   (`python-tool`, `mkdocs`), run `kiln apply --force` over the hand-copied
   skeleton from Phase B, then a second apply reports all `UNCHANGED`.

**Acceptance**

```bash
cd rn-forge/kiln
uv run pytest -q && uv run lint-imports && uv run pyright && uv run ruff check .
kiln_root=$PWD
scratch=$(mktemp -d)
kiln new "$scratch/demo" --archetype python-tool --docs mkdocs --yes --json </dev/null | jq -e '.artifacts | length > 0'
cd "$scratch/demo"
diff -r --exclude=.git --exclude=.venv --exclude=uv.lock . "$kiln_root/tests/fixtures/golden/python-tool" | grep -v 'kiln golden\|kiln [0-9]' ; true   # only name and version lines differ
uv run --project "$kiln_root" kiln apply --dry-run --json | jq -e 'all(.artifacts[]; .action == "unchanged")'
uv sync && task validate
printf '\n# edit\n' >> Taskfile.yml
! uv run python scripts/standards/check_generated.py .
! uv run --project "$kiln_root" kiln apply
uv run --project "$kiln_root" kiln apply --force Taskfile.yml
uv run --project "$kiln_root" kiln doctor
cd "$kiln_root" && kiln doctor && kiln apply --dry-run --json | jq -e 'all(.artifacts[]; .action == "unchanged")'
```

### Phase E — the `-ng` archetypes *(2 weeks)*

Repo `rn-forge/kiln`.

1. Golden repos `python-web-api` (fastapi) and `python-web-app` in both shipped
   flag combinations — `django + angular` and `fastapi + angular` (deferred
   from Phase B); review loop. `react`, `svelte` and
   `python-web-api --framework django` stay `untested = true` (D54).
1. `archetypes/python_web_api/`, `python_web_app/` — `tasks/api.yml`,
   `tasks/web.yml` (`pnpm nx run-many -t lint|test|build`), CI with pnpm/node
   setup, `forbidden_tools` adds `pnpm npx nx`. `python-web-api` generates no
   `tasks/web.yml`; its optional `admin_ui` is served by the API itself.
1. `--framework fastapi|django` affects only `tasks/api.yml` primitives
   (`fastapi dev` vs `manage.py runserver`, `pytest` markers) and the
   `uv init` reconcile step — never the topology or the task graph, which is
   the rule that makes it a flag rather than an archetype (D54). Django is
   templated from `rn-forge-django`'s conventions and, for `python-web-app`,
   is a shipped value with its own golden repo.
1. `kiln new` end-to-end with `nx g` for the frontend; reconcile moves output to
   `web_dir`.
1. Move taskkit's
   `tests/fixtures/repos/{python-pnpm-monorepo,python-django,python-fastapi*,python-angular-pnpm}`
   into `tests/fixtures/repos/` as scaffold-reconcile inputs.

**Acceptance**

```bash
cd rn-forge/kiln && uv run pytest -q tests/test_snapshot.py -k web
scratch=$(mktemp -d)
kiln new "$scratch/web-fastapi" --archetype python-web-app --framework fastapi --frontend angular --docs mkdocs --yes </dev/null
(cd "$scratch/web-nx" && uv sync && pnpm install && kiln doctor && uv run python scripts/standards/check_generated.py . && task validate && kiln apply --dry-run --json | jq -e 'all(.artifacts[]; .action == "unchanged")')
kiln new "$scratch/web-django" --archetype python-web-app --framework django --frontend angular --docs mkdocs --yes </dev/null
(cd "$scratch/web-pnpm" && uv sync && pnpm install && kiln doctor && task validate)
```

### Phase F — rebuild the repos, retire the old *(3 weeks)*

Per repo: `kiln new` into a fresh directory, port source and docs by hand,
`kiln doctor` and `task validate` green, then the fresh tree replaces the repo's
working tree on a branch. History before the replacement commit is not preserved
in any meaningful way and that is accepted (D39).

1. **pykit skeleton** (`python-lib`).
   `kiln new pykit-fresh --archetype python-lib --docs mkdocs`; set
   `[archetype.python-lib] packages`; move `packages/`, `docs/`, `mkdocs.yml`
   body and the root `pyproject.toml` workspace tables in; `extra_refs` for
   anything the generated matrix does not cover. `_package-ci.yml` is deleted.
   pykit's package source is untouched.
1. **kiln** is already self-hosted (Phase D.8).
1. **agentkit** from scratch (`python-tool`).
   `kiln new agentkit-fresh --archetype python-tool --docs mkdocs`; rewrite
   `src/rn_forge/agentkit` on commons and tooling following the donor mapping
   in `commons-upgrade-plan.md` → "Not in this plan" → agentkit bullet
   (`AppConsole`, `DocumentUtils`, `DictUtils.merge_layers`, `TemplateEngine`,
   `StateStore`, `PathUtils.find_root`, `EntryPointLoader`, `ManagedBlock`,
   `Finding`); carry ADRs, E17 spec (updated to say the docs scripts are
   kiln's), tests, and the three generic skills; do not carry the four setup
   skills, `scripts/**`, `feedback.md`. Supersede ADR-0001's claim that `kiln`
   is retired while keeping the product-name decision. `.importlinter` forbids
   `rn_forge.kiln` and `rn_forge.taskkit`.
1. **intellibuild** (`python-web-app`, `fastapi + angular`). Gated on
   `docs2/REFACTOR_PLAN.md` reporting complete. `kiln new intellibuild …`;
   `docs2/` lands as `docs/` and `_areas.yml` gains `context`; universal lints
   come from kiln; `check_brand`, `check_vocabulary`, `check_endpoints`,
   `check_e2e_budget`, `check_gate_tags`, `check_db_url` are repo-local via
   `extra_refs` (D34). First CI the product has ever had. `ci.provider = ado`
   is open question 4.
1. **taskkit** — archive: README banner pointing at kiln and this document, tag
   `archived/v0.2.0`, GitHub repo archived. Not deleted; `validator.py`
   history is referenced from kiln.
1. **intellibench** — archived once intellibuild's first release ships.
   **apollo** — stays parked; when unparked it is
   `kiln new … --archetype python-web-app` plus a port, never an adoption.

**Acceptance**

```bash
kiln doctor --all rn-forge/pykit rn-forge/kiln rn-forge/agentkit walgreens/intellibuild --json | jq -e '.summary.errors == 0'
for r in rn-forge/pykit rn-forge/kiln rn-forge/agentkit walgreens/intellibuild; do (cd "$r" && task validate && uv run lint-imports); done
uv run --project rn-forge/kiln python rn-forge/kiln/tests/support/assert_generated_bodies.py --relative-path scripts/ci/check_ci_entrypoint.py rn-forge/pykit rn-forge/kiln rn-forge/agentkit walgreens/intellibuild
cd rn-forge/agentkit && ! rg -q 'rn_forge\.agentkit\.core\.(io|state|render|paths)' src && rg -q 'rn_forge\.tooling' src
```

### Phase G — ongoing

The generated `scripts/standards/check_generated.py` and import-boundary task
are wired into each repo's `task lint`; CI runs `task validate` and never
installs or invokes kiln. Developers run `kiln doctor`; `kiln doctor --all` is
the cross-repo freshness and compliance signal. A kiln upgrade is
`kiln apply --dry-run`, review, `kiln apply`. Unpark ADO (D4) by adding
`ci.provider = "ado"` templates when intellibuild needs it.

### Critical path

```
Phase A (hours) ─→ Phase B (canon + golden) ─→ Phase C (tooling) ─→ Phase D (kiln) ─→ Phase E (web) ─→ Phase F ─→ G
                        │                                                                   ├─ F.1 pykit skeleton
                        └─ owner review gate: golden repos approved before C starts         ├─ F.3 agentkit rebuild
                                                                                            └─ F.4 intellibuild (gated on docs2 complete)
```

F.1 and F.3 need only Phase D; F.4 needs Phase E and the intellibench docs
refactor. Phase C cannot start before the golden repos are approved, because the
engine's artifact kinds are scoped to what they contain.

______________________________________________________________________

## 4. Risks

- **kiln becoming a god-kit.** Guard: every module is `artifacts()` +
  `checks()`, nothing else; no detection code anywhere; the archetype is
  always asserted by config; no adopt.
- **Templates drifting from the golden repos.** Guard: snapshot tests are
  byte-exact; a template edit without a golden edit fails CI.
- **Golden repos reviewed too lightly** because they look like fixtures. Guard:
  Phase B's acceptance runs them as real repos, and the owner review gate is
  explicit on the critical path.
- **Engine built before kiln needs it** (the framework-before-app trap). Guard:
  Phase C is scoped to artifact kinds that have a golden example;
  `generation.py` tests are written from kiln's `cycle.py` needs.
- **Interactive-only CLI.** Guard: Phase D acceptance runs `new` with stdin
  closed.
- **Generated-file drift accumulating in repos.** Guard: the committed-state
  checker runs in `task lint`; local `doctor` also detects fresh-render
  staleness; `apply` refuses unapproved paths.
- **agentkit rebuild stalls** because it is the biggest port. Guard: it is last,
  nothing depends on it except F.4's apply step 6, and the current agentkit
  keeps working meanwhile.
- **Codegen extra leaks into the runtime surface.** Guard: the import-linter
  contract exists before the first codegen module (Phase C.3);
  `import rn_forge.django` with no extras is a checklist item.
- **Sunk work in taskkit `feature/v1`.** Not carried forward beyond fixtures and
  `validator.py`. Accepted by D23.

______________________________________________________________________

## 5. Decision log

**Confirmed** = the owner decided it. **Superseded** entries are kept so later
sessions do not re-litigate.

| # | Decision | Status |
| -- | -- | -- |
| D1 | Only pykit libraries are build dependencies; kits are CLI/subprocess-only. Library graph acyclic, tooling graph free. | Confirmed |
| D2 | Generator scope is repo shape only for v1; application generators later. | Confirmed |
| D3 | No kit installs in CI. All repo-specific CI logic is generated and committed; CI invokes it through `task validate`. | Confirmed |
| D4 | ADO parked; generator design leaves room for a second provider. | Confirmed |
| D5 | ~~Standards repo lives in `rn-forge`, separate from the generator.~~ | Superseded by D36 |
| D6 | Nx handled by the `-ng` templates calling `pnpm nx run-many`; no adapter. shkit and macsetup stay parked. | Confirmed |
| D7 | ~~Archetypes for v1: `python-cli`, `python-web`, `python-lib`.~~ | **Superseded by D47** |
| D8 | The generator has an interactive CLI in the style of `uv`/`nx`. | Confirmed |
| D9 | ~~taskkit is local-only.~~ | Superseded by D23 |
| D10 | forge-ci merged into the generator. | Confirmed (generator is kiln) |
| D11 | `check_ci_entrypoint` is generated by kiln; its tool list comes from `archetype.toml`, not from another kit. | Confirmed |
| D12 | ~~Contributions protocol.~~ | Superseded by D26 |
| D13 | ~~`forge-core` six modules.~~ | Superseded by D29 |
| D14 | `config.toml` is the interactive flow's only durable hand-authored input; preview writes nothing, `--yes` executes the plan, `apply` is non-interactive and idempotent, and every prompt has a flag. | Confirmed |
| D15 | Apply sequence is umbrella → scaffold → docs → tasks → ci → agentkit → instructions → doctor (§2.5.5). | Confirmed |
| D16 | Scaffolding shells out to native tools and reconciles. | Confirmed |
| D17 | ~~Migration is adopt-and-diff, not rebuild.~~ | **Superseded by D39** |
| D18 | ~~canon precedes commons and kiln because its ADRs are the schemas.~~ Intent kept: kiln's ADRs are written in Phase B before any kiln code. | Superseded by D36 |
| D19 | ~~Skills authored in kits, distributed via entry points.~~ | Superseded by D30 |
| D20 | ~~docskit is its own repo.~~ | Superseded by D24 |
| D21 | Dependabot watches kiln only, not generated workflows. | Confirmed |
| D22 | One release strategy: tag-exists check. | Confirmed |
| D23 | **taskkit is retired.** Detection is dead weight once the archetype is asserted (F16). Its validator, fixtures, and `extra_refs`/repository-owned-include model move into kiln. go-task stays as the single entrypoint. | Confirmed |
| D24 | docskit is folded into kiln as the `docs` module with profile `mkdocs \| external \| none`. | Confirmed |
| D25 | The generator is named `kiln`: repo `rn-forge/kiln`, package `rn-forge-kiln`, module `rn_forge.kiln`, binary `kiln`, config `.rn-forge/kiln/config.toml`. Reassigns the retired predecessor's name; legacy state is never overwritten implicitly. | Confirmed |
| D26 | No contributions protocol. Cross-module names are a kiln-ADR contract; kiln's templates reference them directly. | Confirmed |
| D27 | Ownership is per managed file **or per fenced block** within a shared file. `ManagedBlock` in commons is the mechanism. | Confirmed |
| D28 | No umbrella-level manifest file. `.rn-forge/kiln/config.toml` follows the existing `.rn-forge/<kit>/config.toml` convention; kiln owns the umbrella itself. | Confirmed |
| D29 | `forge-core` is not built. Runtime-neutral mechanisms live in commons, shared local-development mechanisms live in tooling, rn-forge policy lives in kiln. | Revised by D35, Confirmed |
| D30 | kiln ships no skills. Judgement lives in kiln runbooks. The four setup skills in agentkit are not carried into the rebuilt repo. | Confirmed |
| D31 | `python-lib` is a third archetype, modelled on pykit; adding an archetype is a template set, so the cost is low. | Confirmed |
| D32 | ~~Standards repo name is **canon**.~~ "Canon" names the docs section inside kiln. | Superseded by D36 |
| D33 | ~~canon itself is hand-managed MkDocs in v1.~~ | Superseded by D36 |
| D34 | intellibench's parameterizable lints stay repo-local in intellibuild; promote to kiln only when a second repo needs one. | Confirmed |
| D35 | `rn-forge-tooling` is the development-layer package: console/Typer conventions, local state, templates, generator execution and installer mechanics. Django/FastAPI runtime packages never depend on it or Typer. ~~Framework generators are separate provider packages.~~ | Revised by D37, Confirmed |
| **D36** | **Canon is folded into kiln.** Kiln's ADRs 0001–0008 and `docs/reference/standard-repo.md` are the standard; kiln renders it into every repo as `.rn-forge/kiln/standard.md`. No separate docs repo; split one off only if a non-kiln consumer appears. | **Confirmed** |
| **D37** | **Framework code generators are `[codegen]` extras of their runtime package** (`rn-forge-django[codegen]`), in a subpackage the runtime surface never imports, guarded by import-linter and the no-extras import check. The engine stays in tooling. Co-versioning with the runtime is the reason. | **Confirmed** |
| **D38** | **`kiln adopt` is not built.** No ADOPT/ADOPT_CONFLICT classification, no closure capture, no gate-shrink preflight, no model-delta harness. `gate.shrunk` compares against the archetype's `required_validate` list. | **Confirmed** |
| **D39** | **Repos are rebuilt from scratch, not migrated.** Git history of pre-v1 repos is not preserved. Decisions, specs, tests and fixtures are harvested; files are not. pykit's package source is the one exception (split, not rebuilt). | **Confirmed** |
| **D40** | **apollo is parked.** Its broken working tree is not repaired; when it returns it is `kiln new` + port. | **Confirmed** |
| **D41** | **intellibench is superseded by intellibuild**, a fresh `python-web-app` repo (`fastapi + angular`) whose docs are intellibench's `docs2/`. intellibench is a donor, never an adopt target. | **Confirmed** |
| **D42** | The tool keeps the name **kiln**; `canon` was considered and rejected because a tool needs a verb-shaped name and canon is the noun for the rules it carries. | **Confirmed** |
| **D43** | **Golden repos are the source of truth for templates.** Hand-authored, runnable, reviewed before generator code exists; templates are derived from them; snapshot tests are byte-exact. | **Confirmed** |
| D44 | `docs/_areas.yml` and `_structure.md` are seeded, not managed, so a repo can extend its areas (intellibuild's `context`). Doctor validates against the repo's copy. | **Confirmed** — the generated docs scripts now depend on it: `_common.load_areas` has no fixed key list, and kiln's own tree adds a `plans` area |
| **D45** | **CI stays generated and committed; no reusable-workflow devops repo.** Pinned reusable workflows cost the same per-repo commit to propagate a fix as `kiln apply` does, and add an external repo dependency at CI time; floating the ref removes that churn but makes CI unpinned — apollo's `branch = "main"` failure in another form. The reviewability win is taken instead via a committed composite action, `.github/actions/setup`. Revisit only if per-repo churn measurably hurts. | **Confirmed** |
| **D46** | **rn-forge dependencies are pinned PEP 508 direct URLs in `dependencies`**, never `[tool.uv.sources]` — a source override does not survive into a built wheel, so a consumer of a published package could not resolve commons at all. Accepted: such a distribution cannot be uploaded to PyPI, and the tag *is* the version. Publishing to PyPI later relaxes this rule rather than breaking it. | **Confirmed** |
| **D47** | ~~**Four archetypes: `python-cli`, `python-lib`, `python-django-ng`, `python-fastapi-ng`.**~~ `-ng` means a pnpm-managed Nx workspace (Nx's own documented shape); `nx_cloud` is a config key, being an account decision rather than a repo shape. The `backend` and `web_runner` keys are removed: the archetype name says what the repo is. Supersedes D7. | **Superseded by D53/D54** — the catalogue and the flag rule both changed; the underlying principle (the name states the topology) survives |
| **D48** | **ADRs carry decisions; the reference carries specifications.** kiln's ADRs are restructured to nine, each with an *Alternatives considered* section; the verb list, ownership table, dependency sets, doctor codes, CI shape and config schema all live in `docs/reference/standard-repo.md`. An ADR that starts enumerating has become a spec. | **Confirmed** |
| **D50** | **`ruff check --fix` runs before `ruff format`, and `lint:python` mirrors `format:python`.** The linter's fixes are edits; running the formatter first leaves them unformatted. `lint:format` is removed as a separate task. | **Confirmed** |
| **D51** | **The checkers become a versioned package** (`rn-forge-kiln-checks`), split from the kiln CLI, with the docs checkers going to tooling; only `state.json`, `config.toml` and `standard.md` stay committed (kiln ADR-0010). Preserves ADR-0003's actual rule — CI never renders — while removing 1,454 duplicated lines per repo. Both distributions live in the kiln repo, which becomes a `python-lib` workspace in Phase D. The name is `checks`, not `devops`: `checks` names a role that excludes rendering, `devops` names a domain that excludes nothing. | **Confirmed** |
| **D49** | **The libraries own the CLI, logging and state boilerplate, and a repo declares its CLI surface rather than writing it** (kiln ADR-0009). Not an application generator — D2 is unchanged. Phase C's package split is made against this target. | **Proposed** — revised by D52: the CLI boilerplate is `rn-forge-cli`, not tooling. Stays proposed until `golden/python-app` demonstrates a CLI with zero hand-written app construction |
| **D52** | **Three library layers, not two: `rn-forge-commons` → `rn-forge-cli` → `rn-forge-tooling`** (kiln ADR-0002). The seam is not workstation-versus-runtime but *every CLI* versus *tools that install, generate and own files*. A business batch or ML job takes `rn-forge-cli` and gets ADR-0009's zero-boilerplate `main()` without Jinja2, a generation engine, or a package whose contract tells deployed code not to depend on it. Placement is decided by what an API's **signature** contains, not by who calls it today: `DirectoryLock` and `atomic_symlink` return to commons, `extract_archive`/`StateStore`/`TemplateEngine` stay in tooling, `ManagedBlock` stays in commons. Rejected: a `[gen]` extra (an extra adds dependencies, it does not exclude modules or stop an eager initializer) and renaming tooling to `devtools`/`automation`/`core` (no architectural property changes). Refines D29/D35. | **Confirmed** |
| **D53** | **Seven archetypes: `python-app`, `python-tool`, `python-lib`, `python-web-api`, `python-web-app`, `node-lib`, `node-web-app`** (kiln ADR-0005). `python-cli` was two repos under one name — a batch behind a command line, and an installable tool that owns `$RNF_HOME`, state and plugins — with different library sets, which is what forced tooling to be a package most of the fleet was told not to use. The `-ng` pair collapses into `python-web-api`/`python-web-app`: the framework does not change the topology, a separate frontend package does. The two node archetypes are named and deferred to post-v1 — a second toolchain, and nothing in v1 scope uses them. "Is it a monorepo" is not the axis; **publishing** is. Supersedes D47. | **Confirmed** |
| **D54** | **A config flag may select an implementation library only when it changes neither the file topology nor the task graph, and every shipped value has a golden repo.** `framework = django\|fastapi` and `frontend = angular\|react\|svelte` pass; the rejected `backend` + `web_runner` pair failed because together they selected four topologies. The golden-repo rule is what stops flag freedom from reintroducing the combinatorial explosion D47 avoided: v1 ships six golden repos, not the fourteen the matrix could name. A value without one is `untested = true` and `kiln new` refuses it. | **Confirmed** |
| **D55** | **commons, cli and tooling are laid out as sub-packages by kind of mechanism** (§2.11): `lang/`, `fs/`, `data/`, `logging/`, `runtime/`, `integration/` in commons, and equivalents in the other two. **Public class names do not move** and the package facade keeps re-exporting them, so only submodule paths change; no compatibility shims, because D39 already says rebuild rather than migrate. `AppUtils` stays an acknowledged grab bag rather than breaking a public name for tidiness. | **Confirmed** |
| **D56** | **kiln generates repo structure; frameworks generate their own code.** `kiln generate package <name>` — adding a package to a workspace — is in scope for Phase D, because it emits the same repo structure kiln already owns. Application code generators (django model/serializer/api, UI wrappers) stay D2/D37: they ship in `rn-forge-django[codegen]`, register under `rn_forge.kiln.generators`, and kiln supplies only the command surface. The line is whether the output is repo shape or application logic. | **Confirmed** |

______________________________________________________________________

## 6. Open questions

Ordered by when an answer is needed. Nothing blocks Phase A or B.

**Answered by the Phase B review (§0.6):** 3. D44 is confirmed — the docs
scripts now depend on a seeded `_areas.yml`. 4.
~~`python-web --backend django`~~ is its own archetype (D47).

**Before Phase B is committed:** 1. Is Sonar on by default (`ci.sonar = true`)
for every archetype, or opt-in? The golden repos assume default on. 2. Are these
repos public or private? SHA-pinning and `permissions:` are generated
regardless; confirm there is no reason to relax. 3. D44 — seeded `_areas.yml`:
confirm, or keep it managed and add a `[docs] extra_areas` config key instead.

**Before Phase E:** 4. ~~`python-web --backend django`~~ — answered by D47 and
then by D53/D54: it is `python-web-app --framework django`, a shipped flag value
with its own golden repo. Templated from `rn-forge-django`'s conventions and
marked untested until a repo uses it — confirm. 5. Does intellibuild need
`ci.provider = ado` from day one, or does it start on GitHub Actions and move?
This decides whether Phase E or Phase G unparks D4.

**Before Phase F:** 6. `ngkit` (Nx + Angular library monorepo): a fourth
archetype `ng-lib`, or hand-managed? 7. Does the rebuilt agentkit keep its
version line (`0.6.x` → `0.7.0`) or restart at `0.1.0`? Affects the tag-exists
release check on first publish.

**Parked:** 8. ADO provider (D4). 9. An `agentkit docs …` command (out of scope,
E17). 10. apollo's return (D40).

______________________________________________________________________

## 7. Revision history

**Revision 1** — review of four repos; F1–F11; proposed five components incl. a
separate `forge-ci` of reusable workflows; repo tasks calling kits via
`uv run <kit>`.

**Revision 2** — F12–F15; `.rn-forge` ownership moved off agentkit;
two-dependency-graph split; contributions protocol; devfoundry accepted.
Corrected: `uv run <kit>` made every repo depend on the kits.

**Revision 3** — CI model inverted to generate-and-commit (D3); forge-ci
collapsed into devfoundry; taskkit made local-only; `forge-core` specified;
archetypes defined; pykit-first sequencing.

**Revision 8** — after the Phase B review by the owner and by codex. Phases A
and B executed. Archetypes renamed and reduced to four config-key-free names
(D47); an archetype gains a library set, enforced by `check_rn_forge_deps.py`
(D46); CI stays generated, with a composite action (D45); the ADR set
restructured to nine with the specifications moved into
`docs/reference/standard-repo.md` (D48); ADR-0009 proposed for the tooling
boilerplate target (D49). Eight defects from the codex review fixed in the
golden repos — see §0.6.

**Revision 4** — after code review of commons `feature/upgrade`, taskkit, and
agentkit. `forge-core` dropped for Part D (F17); taskkit retired (F16);
contributions protocol, entry-point skills and docskit folded or dropped. Phases
rewritten with acceptance commands.

**Revision 5** — generator named kiln everywhere (D25). CI runs committed
checkers without kiln; committed state is the drift/gate baseline; first
adoption preflighted and path-forced; task surface, template extra, JSON
metadata, docs scripts, import contracts, and acceptance checks fully specified.

**Revision 6** — split pykit into runtime-safe `rn-forge-commons` and
development-only `rn-forge-tooling`. CLI/console, local state, templates and
installer mechanics moved to tooling. Framework code generators as separate
tooling providers.

**Revision 7** — rebuild not migrate (D39): `adopt`, the ADOPT/ADOPT_CONFLICT
rows, closure capture, gate-shrink preflight, the model-delta harness, the
docs-migration scripts and runbook all removed (F18). Canon folded into kiln
(D36, F19) with the standard rendered into every repo. Codegen as `[codegen]`
extras (D37). apollo parked (D40); intellibench → intellibuild (D41). Golden
repos as template source of truth (D43), reviewed before generator code.
Sequencing: stabilize pykit → canon + golden → tooling → kiln → web → rebuilds.

**Rejected along the way — do not revisit without new information:**

- *A generic `scriptkit` / shared script bag* — recreates F2 one level up.
  Scripts are generated by the module that owns their config.
- *Standalone `devopskit` CI generator* — merged into the generator (D10).
- *Reusable GitHub workflows as the reuse mechanism* — cannot serve ADO; D3
  removed the setup action that justified them.
- *Kits reading each other's config point-to-point, and its replacement, the
  contributions protocol* — both moot with one generator (D26).
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
