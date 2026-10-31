# rn-forge repo standardization — plan of action

**Historical record:** proposals and numbered decisions below describe the
review at that time, not current policy. ADR references use current
destinations; retired references use topic names. Current scope and decisions
are in [the spec board](../specs/index.md) and
[the decision log](../adr/index.md).

**Date:** 2026-09-12 · **Revision:** 14 **Repos in scope:** `rn-forge/pykit`,
`rn-forge/kiln` (new), `walgreens/intellibuild` (new; successor to
`intellibench`) **Parked:** `rn-tools/apollo`, `ngkit`, `shkit`,
`rn-forge/agentkit` (re-ideated from scratch, out of v1 —
[agent-config-future.md](agent-config-future.md)) · **Retired:**
`rn-forge/taskkit`

**Revision 14 changes (implementation-ready — §0.1 and §3):** §0.1 is rewritten
as a phase board with verified on-disk state, and §3 carries every remaining
phase with steps, status and acceptance · **pykit stays consumed from its branch
or a local path until the owner declares it stable**, so the release pin gates
nothing (D73) · **`rn-forge-kiln-checks` is the render-free half of each
module's checks, organized by module**, and a **`core`** module owns the
umbrella, config, state and shared checks, with `scaffold` becoming `python`
(D74) · new **Phase C.4** realigns the goldens with pykit Part E (they still
call the deleted `declare()`) and brings the canon up to D57–D74 · Phase E is
gated on `rn-forge-fastapi` and builds over the new `rn-forge-web`.

**Revision 13 changes (the §0.10 thread closed — §0.11):** **no rendered golden
is committed** — a task renders every archetype × flag combination into a
gitignored directory, the owner reviews and approves the output, and the
hand-authored goldens leave git once the templates reproduce them (D69, revises
D63) · config sources are a **local path or a git URL**, **lists replace** on
deep merge, `kiln new` writes the merged config into the repo and everything
after reads only that, and `kiln config update` / `kiln config upgrade`
re-resolve from the recorded source (D70, revises D64) · **no internal module is
ever published** — open question 14 is closed and D67's asymmetry with it (D71)
· **each module declares its own config section, `kiln new` flags, artifacts and
checks**, and kiln composes the schema, CLI and generator from them; the
archetype lists its modules (D72, extends D68) · **§0.11 is the sequence to
execute next.**

**Revision 12 changes (the scope-expansion thread — §0.10, closed by revision
13):** kiln grows from *one standard rendered per archetype* to *a standard
parameterized by organization*, governed by a **four-tier knob model** amending
D54 (D62) · **Jinja templates become the authored source and goldens become
committed snapshots**, with a matrix harness rendering every shipped combination
and running `task validate` in it (D63, revises D43) · **layered external
config** resolved-then-committed, so rendering stays a pure function of the
checkout (D64) · the CI concern is named **`cicd`, not `devops`**, and generates
committed workflows plus local composite actions rather than reusable workflows
(D65, D66, upholding D45 and verification packaging proposal's naming rule) ·
docs/tasks/cicd become **modules inside the kiln distribution**, not separate
libraries, behind a promoted `Generator` protocol that `kiln doctor`
orchestrates (D67, D68). **§0.10 carries the unfinished thread; resume there.**

**Revision 11 changes:** **open question 11 is answered** — the tool lifecycle
surface is a **capability flag** any Python archetype may set, and `python-tool`
becomes a `kiln new` alias for `python-app` + `lifecycle = true` (D61). D53's
seven names survive as names, D54's rule is what decided it,
`golden/python-tool` is unchanged on disk and is now that flag value's golden
repo, and kiln self-hosts as `python-lib` + `lifecycle` with no special case.
**The kiln repo may publish further distributions** beyond `rn-forge-kiln` and
`rn-forge-kiln-checks` — which D61 is the precondition for, since a
multi-distribution kiln is a `python-lib`.

**Revision 10 changes (after the Phase C.2 review):** **README.md is the single
prose home** and `CLAUDE.md`/`AGENTS.md` are pointers plus fenced blocks (D57) ·
**agentkit leaves the plan** — kiln seeds the instruction files itself, apply
loses its subprocess step, and everything agent-config lands in
[agent-config-future.md](agent-config-future.md) (D58) · the **tool lifecycle
surface** is built, in a new Phase C.3, because `python-tool` and `python-app`
are otherwise the same repo and D53 is unproven (D59) · `pyproject.toml` stays
repo-owned and gains a doctor check instead of a generator (D60) ·
**verification packaging proposal becomes executable** — `scripts/**` leaves the
ownership table, the template inventory and the golden repos, and
`rn-forge-kiln-checks` is a numbered Phase D step rather than a decision with no
schedule.

**Revision 9 changes (after the Phase C review):** the development layer is
**split in two** — `rn-forge-cli` for the process and command-line shape,
`rn-forge-tooling` for the file-owning machinery (D52, dependency boundary) ·
the archetype catalogue becomes **seven names plus two implementation flags**
(D53, archetype design), replacing `python-cli` with `python-app`/`python-tool`
and the `-ng` pair with `python-web-api`/`python-web-app` · a config flag is
allowed only when it changes neither topology nor task graph, and **every
shipped flag value has a golden repo** (D54) · commons, cli and tooling are
**re-laid-out into sub-packages** (D55) · `kiln generate package` is in scope;
framework code generators stay deferred (D56) · fourteen implementation defects
from the review are tracked as **Phase C.2** (§0.8).

**Revision 8 changes (after the Phase B review):** Phases A and B are
**executed** — see §0.1 · archetypes are renamed to `python-cli`, `python-lib`,
**`python-django-ng`** and **`python-fastapi-ng`**, dropping the `backend` and
`web_runner` config keys (D47) · an archetype now carries a **library set** as
well as a shape, enforced by a generated checker (D46) · CI stays **generated**,
with a committed composite action rather than reusable workflows from a devops
repo (D45) · kiln's ADRs are **restructured to nine** and the specifications
they produced move to `docs/reference/standard-repo.md` (D48) · a proposed
shared CLI design targets what `rn-forge-tooling` must expose (D49).

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

### 0.1 Where we are now — 2026-09-12 (revision 14)

**Start here.** The design is settled through D74. Nothing below Phase C.2 is
implemented. The next session starts **Phase C.3 (pykit) and Phase C.4 (kiln) in
parallel** — §3 has the steps and acceptance for each. Verify the repo state
table with `git status` before acting; it goes stale.

#### Phase board

| Phase | Repo | What | Status |
| -- | -- | -- | -- |
| A | pykit | stabilize commons Part C | **done** |
| B | kiln | canon + hand-authored golden repos | **done**, reviewed (§0.6, §0.7) |
| C | pykit | first tooling extraction | **done**, reviewed and revised (§0.8) |
| C.2 | pykit + kiln | commons → cli → tooling split, re-layout, defect fixes, golden rename | **done** (steps 1–8, 10); pykit plan Parts D and E committed at `f59c40f`. Step 9 (release tags) is **deferred by D73** — pykit is consumed from its branch or a local path until the owner declares it stable |
| **C.3** | pykit | the tool lifecycle surface: `install/` + `[cli.lifecycle]` (D59, D61) | **not started** — `rn_forge/tooling/install/` holds only `archive.py` |
| **C.4** | kiln | realign the goldens and the canon with pykit as it is today: Part E CLI API, branch pins everywhere, lifecycle in `golden/python-tool`, D57–D74 into the canon | **not started**; the instruction-file split (old C.3 step 4) is the one piece already done |
| D | kiln | the generator: checks package, `core` + modules, render matrix, CLI, doctor, self-hosting (D69–D74) | not started |
| E | kiln | web archetypes, over `rn-forge-web` + `rn-forge-django`/`rn-forge-fastapi` | not started; gated on `rn-forge-fastapi` (in progress in pykit) |
| F | all | rebuild pykit's skeleton and intellibuild with `kiln new` | not started |
| G | all | ongoing; pykit releases when the owner declares it stable (D73) | — |

#### What is true on disk that the older sections do not say

- **The goldens are behind pykit.** `golden/python-app` and `golden/python-tool`
  still import `rn_forge.cli.declare` (deleted in pykit Part E) and
  `from rn_forge.cli import console` (moved to `rn_forge.commons`), and still
  define `main()`. Their `uv.lock` pins an older `feature/upgrade` commit,
  which is the only reason they still pass. The same stale names appear in
  their `README.md`, `docs/architecture/repository-shape.md`,
  `docs/adr/ADR-0001.md` and `config.toml` comments.
- **`golden/python-lib`'s two packages pin `rn-forge-commons-v0.2.2`**, a tag
  from before the layer split; the other goldens pin `@feature/upgrade`.
- **`docs/reference/standard-repo.md` still names agentkit** as an owner
  (`.rn-forge/agentkit/**`, the `CLAUDE.md` body, `AGENTS.md`, `.claude/**`) —
  D57/D58 never reached the canon — and its dependency-set table omits
  `rn-forge-web` beneath django and fastapi.
- **pykit gained `rn-forge-web`** (framework-free inbound HTTP primitives,
  depends on commons only) and is building **`rn-forge-fastapi`** over it.
  `rn-forge-django` does not depend on web yet; pykit's django plan aligns it.
- kiln itself has no generator source (`src/rn_forge/kiln/` is an empty package)
  and still carries a hand-copied `scripts/**`.

#### Repo state

| Repo | Branch | State | Note |
| -- | -- | -- | -- |
| `rn-forge/kiln` | `feature/v1` | plan revisions 12–14, shared CLI design edit and `agent-config-future.md` uncommitted | three hand-authored goldens; kiln's own config is `python-tool` |
| `rn-forge/pykit` | `feature/upgrade` | clean at `f59c40f` | commons, cli, tooling, web, django; fastapi in progress. Executable form: `docs/plans/commons-upgrade-plan.md`, `web-library-plan.md`, `fastapi-library-plan.md`, indexed by `docs/plans/README.md` |
| `rn-forge/agentkit` | `feature/v0.6.0` | clean | **out of the plan (D58)** — [agent-config-future.md](agent-config-future.md) |
| `rn-forge/taskkit` | `feature/v1` | 34 staged | **retired (D23)** — donor for `validator.py` and fixtures |
| `rn-tools/apollo` | `feature/initial` | 13 dirty | **parked (D40)** |
| `walgreens/intellibench` | `feature/iteration-2` | 13 dirty | **superseded by intellibuild (D41)** |

#### Where the history is

§0.6–§0.9 record what each review changed; §0.10 is the scope-expansion
reasoning (revision 12); §0.11 records the owner's answers that closed it
(revision 13). None of them needs re-reading to execute §3 — they exist so a
decision is not re-derived.

### 0.2 Component map after this plan

| Component | Kind | Owns | Status |
| -- | -- | -- | -- |
| **commons** (`rn-forge-commons` in pykit) | library | runtime-neutral Python/data/filesystem mechanisms, integration protocols, `AppConsole` (moved here in pykit Part E) | exists; re-laid-out (C.2) |
| **cli** (`rn-forge-cli` in pykit) | app library | the Typer layer only: `CliApp` (`from_config`, exit codes via `__call__`), `CliOptions`, the declared `[cli]` surface records | exists (C.2, reshaped in pykit Part E) |
| **tooling** (`rn-forge-tooling` in pykit) | dev-tool library | generation engine, templates, local state, docs mechanics, **the lifecycle surface** | exists; lifecycle surface is Phase C.3 |
| **web** (`rn-forge-web` in pykit) | library | framework-free inbound HTTP wire semantics; depends on commons only | **exists** |
| **django** / **fastapi** (`rn-forge-django`, `rn-forge-fastapi` in pykit) | framework libraries | adapters over web; `[codegen]` extras later (D37) | django exists; fastapi **in progress** |
| **kiln** (`rn-forge/kiln`, binary `kiln`) | CLI + canon | the canon; archetypes; the `core` module and the concern modules `python`, `docs`, `tasks`, `cicd`, `instructions` (D72, D74); `doctor` | Phase D |
| **checks** (`rn-forge-kiln-checks` in kiln) | dev-dependency library | the **render-free half of each module's checks**, organized by module, as console scripts; what CI runs (D74, verification packaging proposal) | Phase D.1 |
| **agentkit** | — | — | **out of the plan (D58)** — [agent-config-future.md](agent-config-future.md) |
| canon repo · taskkit · `go-task-setup` · `docs-setup` · `mkdocs-site-setup` · `spec-structure-setup` · `forge-core` · `forge-ci` · `docskit` | — | — | **not built / retired** |

### 0.3 Rebuild, not migrate (D39)

Every repo in scope except pykit is created fresh by `kiln new` and its source
is written against commons and tooling. Nothing is copied file-by-file from an
old repo into a new one. What *is* carried over is **decisions, specs, tests and
fixtures**, read as prior art:

| Donor | Carry | Do not carry |
| -- | -- | -- |
| `agentkit` | **already harvested** — the E17 docs area model, `_areas.yml`/`_structure.md`, the checker behaviours, the verb layout, the CI discipline. ADR-0021 is kiln ownership policy. Everything still outstanding, including `self_command.py` as prior art for D59, is in [agent-config-future.md](agent-config-future.md) | `core/**` (replaced by tooling); setup skills; `feedback.md`; scripts as files |
| `taskkit` | `core/validator.py` rules and tests; `tests/fixtures/repos/**` for the `-ng` archetypes; the `extra_refs` / repository-owned include model; `Envelope` `--json` shape. Retirement record in [agent-config-future.md](agent-config-future.md) | discovery, planner, adapters, install layer |
| `intellibench` | `docs2/**` (already in the area model — it becomes intellibuild's `docs/`); the universal lints in `tools/lint/` as *template inputs* (`check_ci_entrypoint`, `check_layout`, `check_locks`, `check_pins`); `tools/docs/{check,_nav,generate_order,check_mermaid}` behaviour | `docs/` (superseded by `docs2/`); `ADR_REVIEW.md`, `temp.txt`; product code paths |
| `apollo` | ADR-0024 (`.docs-site` output dir); `docs/guides/task-vocabulary.md` as input to kiln task vocabulary | everything else (parked) |
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
| ownership policy and dependency boundary are redundant | Merged into one ownership ADR. "Everything is kiln-owned" was *not* adopted: agentkit, the repo and seeded files all own paths, which is why three artifact kinds exist. |
| CI policy's CI model — reusable templates from a devops repo | Examined and rejected with reasons (D45). Pinned reusable workflows cost the same per-repo churn as generation and add an external CI dependency; floating them means unpinned CI. The reviewability win was bought instead with a committed composite action, `.github/actions/setup`. |
| type-checking choice and shared CLI design read as spec, not decision | Correct. Every enumeration moved to `docs/reference/standard-repo.md`; every ADR gained an **Alternatives considered** section (D48). |
| Archetypes should be `python-cli`, `python-lib`, `python-django-ng`, `python-fastapi-ng`; fold shared CLI design into scope policy | Done (D47). `-ng` means a pnpm-managed Nx workspace; `nx_cloud` is a config key; `backend` and `web_runner` are gone. Dependency defaults folded into the archetypes ADR. |
| `AGENTS.md` should be a static pointer to `CLAUDE.md` | Done in all three repos. `check_structure.py`'s docs-pointer rule was generalized to understand single-sourcing rather than demanding both files carry the links. |
| Add a Markdown formatting task | Done: `lint:markdown`, `format:markdown`, seeded `.mdformat.toml`. The earlier harvest note misread agentkit ADR-0014 — it makes the mdformat *config* repository-owned, not the task. `.rn-forge/kiln/standard.md` is excluded, because a formatter rewriting a kiln-owned file is two owners writing the same bytes. |
| Review `pyproject.toml` tool config against pykit/agentkit | Done: `--import-mode=importlib`, targeted test-file ignores instead of `["ALL"]`, `py.typed` markers, `ruff format --check` in the gate. No repo in the fleet uses mypy, and that fleet decision is now kiln type-checking choice. |
| Is there more standard boilerplate — logging, CLI config, arg parsing? | Yes, and it is the strongest argument for the library set. Written up as **shared CLI design (proposed)**: tooling owns the boilerplate and the CLI surface is declared in config, not written. Code lands in Phase C/D; D2 still defers application generators. |

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
| Will the golden repo's `ownership policy` be seeded into every repo? | **No.** Only `docs/adr/index.md` and `docs/adr/_structure.md` are seeded; the golden repo's own ADR is fixture content and is not in `state.json`. A new repo gets an empty, structured `adr/` area and writes its own first decision — the runbook covers that. |
| `scripts/` is a good candidate to package and add as a dev dependency | **Agreed, and settled as kiln verification packaging proposal (accepted; D51).** 1,454 lines per repo, four of the seven checkers with no per-repo variation at all, and the remaining three varying only by lists already present in `config.toml`. Splitting `rn-forge-kiln-checks` from `rn-forge-kiln` keeps CI policy's real rule — CI never *renders* — while removing the duplication. The docs checkers move into tooling in Phase C; the four policy checkers become `rn-forge-kiln-checks` in Phase D, in the kiln repo alongside the CLI. |

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
| A2 — docs extraction carried kiln policy into tooling | **Accepted in full; the cleanest finding in the review.** `docs/structure.py` hardcoding ADR numbering, epic/release naming and instruction filenames puts rn-forge policy inside a general-purpose library, contradicting ownership policy outright. Tooling keeps link, Markdown and nav *mechanics* and takes an explicit policy object; `rn-forge-kiln-checks` supplies it (Phase D). No generic validation framework. |
| A3 — the package contract bundles every consumer with the whole CLI stack | **Accepted; the eager `__init__` is the real defect.** Under D52 it largely evaporates: a batch importing `rn_forge.cli` cannot reach Jinja2, because it is in another distribution. Codex is right that extras add dependencies rather than excluding modules — which is why the split is packages, not extras. |
| Rename tooling to `devtools` / `automation` / `core` | **Rejected, as codex recommended.** None changes an architectural property. `rn-forge-cli` was rejected as a rename of the *whole* package for being too narrow, and adopted as the name of the application layer specifically, where it is exactly right. |

**Archetypes (from the owner)**

| Comment | Outcome |
| -- | -- |
| `python-cli` conflates business batches with installable tools | **Done (D53).** `python-app` and `python-tool`. Same shape, different library set, different `REQUIRED` list, one golden repo each. |
| `python-lib` is a monorepo publishing several packages; `python-app` may also carry internal packages | **Done, and the axis is corrected.** "Is it a monorepo" does not discriminate — every archetype here can be one. *Publishing* does: per-package release tags and a per-package CI matrix, versus one version. Written into archetype design and the runbook. |
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

**What neither review said.** Phase C broke archetype design's own rule — *a
template change not first made in a golden repo is a bug*. It invented
`rn-forge-tooling` and shared CLI design's declared `[cli]` surface, and no
golden repo demonstrates either: golden-cli still pins commons `v0.2.2` and does
not use tooling at all (which is F8, read as a plan gap rather than a defect).
The missing acceptance test is that **`golden-app` contains a working CLI with
zero hand-written app construction**. If that repo cannot be written, shared CLI
design is not ready to be accepted, and that is better discovered now than after
kiln's templates derive from it.

### 0.9 What the Phase C.2 review changed

The owner's review of the executed Phase C.2. Every item is addressed; this is
the list, so a later session does not re-derive it.

| Comment | Outcome |
| -- | -- |
| Root `README.md` and `CLAUDE.md` only name `python-tool` — example, or stale? | **Neither.** It is kiln's own archetype, read from its `config.toml` and rendered into the block. It *is* scheduled to change: verification packaging proposal makes kiln a two-distribution repo, so it becomes `python-lib` at Phase D.8. The one genuine example — `cd tests/fixtures/golden/python-tool` in the README — now names all three. |
| Those two files overlap; use README for developer-facing content and refer to it from CLAUDE.md | **Done, and promoted to a rule (D57).** Both files opened with the same sentence and repeated the same status pointers. §2.3 already forbids two owners writing the same bytes; D57 is that rule applied to prose. Applied to kiln and all three golden repos in Phase C.3. |
| Same in each golden repo | **Same fix, same phase.** It is a standard change, so it lands in the golden repos first (archetype design) and reaches generated repos as a template. |
| `scripts/` is repetitive; we discussed a devopskit and it is not in the plan | **It was decided and never scheduled.** The former separate-checker proposal was accepted and D51 confirmed — including rejecting the `devopskit` name, because `checks` names a role that excludes rendering while `devops` names a domain that excludes nothing. What was missing is execution: §2.4, §2.5.5, §2.6 and Phase D all still generated `scripts/**`. Now a numbered Phase D step, with the golden repos losing 1,454 lines each before any template derives from them. |
| Can the near-identical `pyproject.toml` tool config become a reusable pykit component? | **No mechanism exists, and generating it would not deduplicate anything (D60).** pytest and coverage have no config inheritance; pyright's `extends` is not available in the `[tool.pyright]` form; ruff's `extend` is a filesystem path that would have to reach into `.venv`. The bytes are duplicated either way. So pyproject stays repo-owned and gains doctor check 8a, which warns on divergence — verification without the apply round trip. |
| taskkit is dead and agentkit will be re-ideated from scratch; take the content out | **Done (D58).** Everything agent-config — the rebuild scope, the prior art worth reading, taskkit's retirement record — is in [agent-config-future.md](agent-config-future.md). The structural consequence is the real change: kiln no longer shells out to agentkit and seeds the instruction files itself, so `.claude/**` is unowned until the rethink happens. |
| Global config management has to rethink its role now kiln exists | **Recorded as the question that comes first**, in [agent-config-future.md](agent-config-future.md) §2. agentkit's *project* scope existed largely because nothing else owned repo files; kiln owns them now. Do not answer it by porting the old shape. |
| `rn-forge-cli` is being refactored in a separate session | **Resolved — the refactor landed (pykit plan Part E).** The goldens build against `CliApp.from_config()`, drop `main.py` entirely, and drop the `log_options`/`output_options` keys. Phase C.3 step 2 remains the coordination point for `[cli.lifecycle]`. |
| `python-app` and `python-tool` look the same; a tool should handle install, uninstall, upgrade, version, doctor — uniformly, via an adapter | **Correct, and measurable: the two `pyproject.toml` files differ by a name and one dependency line, and `install/` contains only `archive.py`.** Built as D59 in a new Phase C.3, with exactly the adapter shape suggested: tooling owns the algorithms, a `ToolProduct` protocol with every member defaulted carries the per-tool difference, and `CliApp.from_config` mounts the verbs from config so the repo needs no `main.py`. It also exposes open question 11 — kiln itself is an installable tool whose repo shape is `python-lib`. |

______________________________________________________________________

### 0.10 The scope-expansion thread (revision 12)

> **Closed by revision 13.** The *Still open* list at the end is answered in
> §0.11, which revises D63 and D64 and is the section to resume from. This
> section is kept as the record of the reasoning.

**What changed conceptually.** Through revision 11, kiln was *one opinionated
standard, rendered per archetype*. The owner's target is *a standard generator
parameterized by the team's landscape*: org identity in `pyproject.toml`, Sonar
details that differ by where it is hosted, GitHub vs ADO, and per-org
conventions. Those have different failure modes. The one that threatens the
design is D43 + D54 together — goldens are the source of truth and every shipped
flag value needs a golden — because enough knobs means no golden covers any real
combination, at which point the goldens stop being the source of truth and
become decoration. D62 and D63 are the two answers to that.

#### The tier model (D62) — how much a knob costs

| Tier | What it changes | Golden cost | Examples |
| -- | -- | -- | -- |
| **1 — Values** | bytes inside files that exist either way | none | org/group name, author and maintainer, license, Sonar host + organization, project-key pattern, package prefix |
| **2 — Toggles** | a known fragment present or absent | one golden *fragment* | `ci.sonar`, publish step, docs deploy, coverage upload, `lifecycle` (D61) |
| **3 — Topology** | which files exist | a golden repo (or a rendered matrix cell — D63) | `archetype`, `ci.provider = github\|ado` |
| **4 — Policy** | what code is legal | unbounded — **not built** | class naming, package prefixes as *rules* |

Tier 4 is refused on purpose: ruff already implements naming rules (`N`/
pep8-naming) and `.importlinter` already expresses package boundaries. **kiln
generates those tools' configuration from declarative config and never
implements a matcher** — same capability, none of the ownership. A repo-standard
scaffolder that grows its own static-analysis engine maintains it forever.

Tier 1 identity in `pyproject.toml` does **not** reopen D60. D60's argument was
about *tool config tables* (ruff/pyright/pytest have no inheritance mechanism,
so the bytes duplicate whoever writes them). Identity metadata is the opposite
case — genuinely identical across an org and small — so doctor check 8a extends
to cover `[project]` identity fields, warning-only, verified never written.

#### Templates, goldens and the matrix harness (D63)

The owner's push-back is accepted: hand-authoring a golden per archetype × flag
combination is real overhead, and Jinja templates carry real value. But a golden
supplies **two** properties and only one of them survives the change:

- *runnable* — `uv sync && task validate` passes, workflows lint, docs build
  `--strict`. A matrix harness covers this **better** than hand-authoring,
  since it reaches every shipped combination rather than six.
- *reviewable as committed bytes* — the property that makes "a template change
  not first made in the golden is a bug" detectable, because the byte impact
  of a template edit shows up in a pull-request diff. A tree that exists only
  in a temp directory cannot be code-reviewed and cannot diff across time.

So the resolution keeps both, and inverts D43's direction of authorship:
templates are authored, goldens are **generated and committed like snapshot
fixtures**. See D63 for the three-part mechanism and its cost.

#### The concerns, and what they are called (D65, D67, D68)

`docs`, `tasks` and `cicd` become modules inside the kiln distribution behind
one promoted `Generator` protocol — `artifacts()` + `checks()`, which is the
seam §2.9 says kiln's own modules already use, and the same shape as
`ToolProduct` (D59). `kiln doctor` orchestrates them and merges commons
`Finding` rows into one report.

**`cicd`, not `devops`** — and this *upholds* verification packaging proposal
rather than reversing it. verification packaging proposal rejected `devops`
because it "names a domain that excludes nothing"; `cicd` names pipelines and
workflows and excludes infra provisioning, observability and deployment
topology, all of which are out of scope (§0.5). The ADR's reasoning stands
unamended.

**The technical constraint that shaped D66:** GitHub Actions cannot `include:` a
YAML file from `.venv` or from `.rn-forge/`. Its only reuse mechanisms are
reusable workflows fetched from a *git repo* and composite actions; ADO's
`extends`/`template:` is the same — git resources, not packages. So "thin
wrappers importing templates from inside the package" is not implementable, and
the nearest thing that is — reusable workflows from a devops git repo — is
exactly what **D45 rejected**, for reasons that still hold (CI stops being
self-contained; private-repo fetch needs auth; the ref is either churn-y when
pinned or unpinned like apollo's `branch = "main"`). Local composite actions
achieve the same thinness with reuse happening at *generation* time.

#### Counters recorded against proposals that were dropped or changed

| Proposal | Outcome |
| -- | -- |
| Make the golden repos themselves Jinja templates | **Changed, not dropped (D63).** Templates are authored in Jinja; goldens stay committed *rendered* trees, as snapshots rather than hand-written sources. The review property is what committed bytes buy. |
| `kiln doctor` should render a temp repo and compare, rather than diffing a golden | **Already the design — no change.** §2.5.6 and `kiln diff` render fresh and compare against disk; doctor never reads a golden. `check_generated.py` deliberately does neither, comparing disk against committed `state.json` hashes, stdlib-only so a cold clone can run it. Goldens appear only in tests. |
| Config discovered at `~/.rn-forge/kiln/` or cwd, absence falling back to kiln defaults | **Reproducibility bug, fixed by D64.** If home-level config affects rendering, `kiln apply` produces different bytes on different machines, `check_generated` goes red for whoever did not render last, and the committed `state.json` baseline — which configuration design rests on — becomes machine-dependent. Discovery is kept; it resolves at `kiln new` / `kiln config sync` and the resolved values are committed. |
| Workflows as thin wrappers including templates from inside the cicd package | **Not implementable (D66).** See the constraint above. Local composite actions instead. |
| `scripts/` subdirectories owned by kiln and cicd | **Declined — keeps verification packaging proposal.** The ADR removed `scripts/**` from kiln's ownership to stop shipping 1,454 lines per repo; the owner's own principle here ("minimal files, maximum reuse from inside the dependency") is that ADR's argument verbatim. Checkers stay console scripts from pinned dev dependencies. |
| kiln "owns its surface" inside `src/` and `tests/` | **Narrowed to verification.** If kiln *generates* files there it has become an application code generator and **D56 reopens**. kiln owns structural verification — src layout, package directory naming, test tree shape — and generates nothing. |
| `docs`/`tasks`/`cicd` as separately published distributions | **Modules, not distributions (D67).** A separate distribution is warranted only when something installs it *without* the others. `checks` has a proven case (CI installs it and must not install kiln); `cicd` has a plausible one; docs and tasks have none. Import-linter already enforces the boundaries inside one distribution — it is what CI policy does today for `rn_forge.kiln.checks`. |
| Move `rn-forge-kiln-checks` into pykit to settle open question 11 | **Declined (D61).** It answers *kiln today* and leaves the underlying question to resurface at the first `python-lib` that ships a command. The checkers are also stdlib-only by design and encode kiln's archetype catalogue, which would invert the layering. |

#### Still open — pick up here

1. **Which committed snapshots, and when the matrix runs** (open question 12).
   Committing all m×n rendered trees is too large; committing none loses the
   review property. The proposal is a representative subset committed, full
   matrix in CI — but *which* subset, and per-PR versus nightly, is unanswered
   and is a CI-time cost decision.
1. **Config source format and merge semantics** (open question 13). The
   org/project/repo hierarchy is agreed. Undecided: whether a remote source is
   a git URL or a published package, and the merge rule for **lists** — deep
   merge is unambiguous for scalars and tables and ambiguous for lists.
1. **Whether `cicd` is eventually published** (open question 14), which is the
   one asymmetry D67 leaves open.
1. **How an archetype declares its enabled modules** — the owner's framing is
   that "the archetype defines which dependencies are included and which kiln
   modules are initialized in the repo." That is a config-schema change to
   §2.5.2 that has not been drafted (open question 15).
1. **Phase sequencing.** D62–D68 are a Phase C.4 or a revised Phase D; nothing
   is scheduled yet, and Phase D's step list still assumes revision 11's
   shape.

All five are answered in §0.11.

______________________________________________________________________

### 0.11 Closing the thread (revision 13)

The owner answered §0.10's open items directly. Each answer is recorded as a
decision (D69–D72) so it is not re-derived; this section is the summary and the
executable sequence.

#### The answers

| Open item | Answer | Decision |
| -- | -- | -- |
| Which rendered trees are committed (OQ 12) | **None.** Rendered output is regenerable, so it does not belong in git. A task renders every shipped archetype × flag combination into a gitignored directory; the owner reviews and approves the output, optionally with a parallel review agent reading the rendered copies. The same task validates each cell. | D69 |
| Config source and merge rule (OQ 13) | A **local path or a git URL**, never a package. Deep merge, **lists replace**. `kiln new` resolves once and writes the merged config into the repo; every later operation reads only that file. Re-resolution is explicit: `kiln config update` (the source changed) and `kiln config upgrade` (kiln changed). | D70 |
| Is `cicd` published (OQ 14) | **No, and neither is any other internal module.** They are only usable through a kiln-generated repo. | D71 |
| How an archetype declares its modules (OQ 15) | **Each module owns its config section, its `kiln new` options, its artifacts and its checks**; kiln composes them into one schema, one CLI and one generator. `archetype.toml` lists the modules an archetype enables. | D72 |
| Phase sequencing | Below. | — |

#### What this changes elsewhere, so nobody trips on it

- **The review property moves from pull-request diffs to the owner's approval of
  rendered output.** D63's "reviewable as committed bytes" argument is
  consciously traded away. What replaces "a template change not first made in
  the golden is a bug" is: *a template change is not done until the owner has
  approved its rendered output.* To see a change's byte impact over time,
  render two refs side by side (`--ref`, below) and `diff -r` them — nothing
  needs to be committed for that.
- **Byte-exact snapshot tests against committed goldens (Phase D step 5, §4
  "templates drifting") go away.** kiln's own tests stay: idempotence (a
  second apply is all `UNCHANGED`), classification of a fresh directory, and
  per-module rendering tests on small inputs.
- **The hand-authored goldens are a bootstrap reference, not a permanent
  fixture.** Templates are written from them; once a rendered cell reproduces
  its golden (provenance version and repo name aside),
  `tests/fixtures/golden/` is deleted from git. Until then the README's
  "goldens are the source of truth" rule still holds, because they are the
  only runnable standard there is.
- **D64's reproducibility property survives unchanged** — the merged config is
  committed, so `kiln apply` is still a pure function of the checkout. Two
  parts of D64 are relaxed, because committing the result already buys what
  they were for: a git source **may** name a branch (the resolved commit is
  recorded, and nothing re-reads it implicitly), and `kiln doctor` **does not
  fetch** the source — drift from the org profile is
  `kiln config update --dry-run`, so doctor stays offline and deterministic.

#### The config lifecycle (D70)

| Command | Reads | Writes | Then |
| -- | -- | -- | -- |
| `kiln new <dir> --config <path\|git-url[@ref]> …` | kiln defaults → each source layer → flags | merged `.rn-forge/kiln/config.toml`, with a `[source]` table (location, ref, resolved commit) | scaffold + apply, as today |
| `kiln apply`, `kiln doctor`, `kiln diff` | **only** the committed `config.toml` | — | — |
| `kiln config update [--dry-run] [--apply]` | the recorded source, with the **current** kiln's defaults | re-merged `config.toml` | prints the artifacts that would change; `--apply` runs `kiln apply` |
| `kiln upgrade` | — (the lifecycle verb, D59/D61 — kiln upgrading itself) | the install | loads the committed config against the new schema: **warns** when it loads but a newer schema exists, **errors** when it no longer validates, and names `kiln config upgrade` either way |
| `kiln config upgrade [--dry-run] [--apply]` | the recorded source, with the **new** kiln's defaults and schema | migrated and re-merged `config.toml` | as `update` |

Three rules make that table safe:

1. **The config manager validates against the running kiln's schema on every
   load**, not only on `upgrade`. A config written by a newer kiln is refused
   with the version it needs.
1. **Local edits survive re-resolution.** `state.json` already records per-key
   provenance (D64). A key whose committed value differs from what its layer
   last supplied is a repo override; `update` and `upgrade` keep it and list
   it, rather than silently overwriting it.
1. **Lists replace.** A layer that sets a list owns the whole list. Append
   semantics were rejected because removing an inherited entry then needs a
   second syntax.

#### The module contract (D72)

```python
class KilnModule(Protocol):
    name: str                                         # "docs"; the config section [docs]
    config_model: type[BaseModel]                     # pydantic, strict; defaults are kiln's layer
    def options(self) -> Sequence[Option]: ...        # the `kiln new` flags this module adds
    def artifacts(self, config: KilnConfig) -> Sequence[Artifact]: ...
    def checks(self, config: KilnConfig, root: Path) -> Sequence[Finding]: ...
```

kiln owns only the composition: the root schema is `schema_version` +
`[repository]` + one section per enabled module; the `kiln new` command line is
the union of every enabled module's options, with a collision a startup error;
`apply` and `doctor` iterate modules in `archetype.toml` order. `archetype.toml`
gains
`modules = ["umbrella", "scaffold", "docs", "tasks", "cicd", "instructions"]`
alongside its dependency set, and a disabled module's section is rejected rather
than ignored. This is D68's `Generator` protocol with the config and options
halves added — still `artifacts()` + `checks()` at its core, still the §4
god-kit guard.

#### Next implementation steps

Superseded by revision 14: the sequence is now §3, Phases C.3 → C.4 → D → E,
with the status of each in §0.1. Two changes from the list that stood here: the
release pin no longer gates anything (D73), and the checks package is
reorganized around modules, with `umbrella` and `scaffold` becoming `core` and
`python` (D74).

______________________________________________________________________

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
commons ──► cli ──► tooling ──► kiln ──► kiln-checks  (checks never imports kiln)
   │         │         │    └──► rn-forge-django[codegen]  (extra; never the runtime surface)
   │         │         └───────► every python-tool repo
   │         └─────────────────► every python-app / python-web-* repo
   └───────────────────────────► rn-forge-django, rn-forge-fastapi

kiln ──entry points─► *[codegen]    (kiln discovers generators; never imports a framework)
CI ──► kiln-checks + tooling        (verification only; CI never installs kiln — verification packaging proposal)
```

> **Library graph acyclic, tooling graph free.** `rn-forge-commons`,
> `rn-forge-cli` and `rn-forge-tooling` are the only rn-forge packages that are
> build dependencies of a kit, and each depends only downward. pykit adopting
> kiln as dev tooling is not a cycle — nothing is imported. kiln invokes no
> other kit as a subprocess either (D58).
>
> **Three layers, not two (D52).** commons is what a library, a service and a
> batch can all take. `rn-forge-cli` is what any program with a command line
> takes — including business batches and ML jobs, which is the case the first
> two-package split got wrong. `rn-forge-tooling` is what a program that
> installs itself, owns files in someone else's repo, or renders templates
> takes. The placement test is what an API's *signature* contains, not who
> happens to call it today ([ADR-0002](../adr/ADR-0002.md)).

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

- A cold clone builds **without kiln**, without `$RNF_HOME` and without a custom
  bootstrap. It does install pinned dev dependencies — ruff, pyright, pytest,
  mkdocs and, from Phase D, `rn-forge-kiln-checks` — and then runs committed
  *configuration* against them. It never runs a generator. verification
  packaging proposal states this plainly rather than leaving the older, wider
  claim standing.
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
- `check-generated`, a console script from `rn-forge-kiln-checks`, verifies
  whole-file hashes, managed-block body hashes and presence of seeded
  artifacts against the committed state. `check-task-layout` parses the task
  graph and verifies that the archetype's required verbs are reachable from
  `validate` (its header carries the list). Neither checker renders templates.
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
1. **One prose home per repo: `README.md`** (D57). `CLAUDE.md` is a pointer to
   it plus the fenced blocks; `AGENTS.md` is a pointer to `CLAUDE.md`.
   Developer-facing prose is written once, in the file a human opens first.
1. **kiln invokes nothing** (D58). It seeds `README.md`, `CLAUDE.md` and
   `AGENTS.md` and owns its block in the latter two. A future agent-config
   tool adds its own fence to files kiln seeded; that is the whole seam.
1. Judgement is not automated. Where a human or agent must decide, kiln's docs
   hold a **runbook**, not a skill.

### 2.4 Ownership table (normative — kiln ownership policy)

| File / tree | Owner | Artifact kind |
| -- | -- | -- |
| `.rn-forge/kiln/config.toml` | repo (hand-edited input) | input |
| `.rn-forge/kiln/state.json` | kiln | generated, committed CI baseline; never hashes itself |
| `.rn-forge/kiln/standard.md` | kiln | managed — the rendered canon (§2.10) |
| `.rn-forge/kiln/backups/`, `rendered/` | kiln | gitignored derived data |
| `.gitignore` | repo body; `# BEGIN rn-forge kiln` block → kiln | block |
| `pyproject.toml` | **repo** — verified, not generated (D60) | input; doctor check `pyproject.tool-config` |
| `.editorconfig` | kiln | managed |
| `.importlinter` | kiln | managed import-boundary contracts |
| `Taskfile.yml`, `tasks/workspace.yml`, `tasks/quality.yml`, `tasks/docs.yml`, archetype namespace files (`tasks/api.yml`, `tasks/web.yml`) | kiln | managed |
| `tasks/self.yml` and any include declared `ownership = "repository"` | repo | seeded once, never rewritten |
| `scripts/**` | **repo only** — a repo's own lints, wired via `[tasks.extra_refs]`. kiln generates nothing here (verification packaging proposal, D51); `cicd` generates nothing here either (§0.10) | repo |
| `src/**`, `tests/**` | **repo** — kiln verifies *structure* (src layout, package directory naming, test tree shape) and generates nothing. Generating here would make kiln an application code generator and reopen D56 | input; doctor only |
| `README.md` | kiln body | **seeded** — the single prose home (D57) |
| `docs/_areas.yml`, `docs/_structure.md`, `docs/adr/_structure.md` | kiln | **seeded** — repos may extend areas (D44) |
| `docs/index.md`, `docs/<area>/index.md` | kiln | **seeded** — written if absent, never touched again |
| `mkdocs.yml` | repo body; `# BEGIN generated nav` block → kiln | block |
| `.github/workflows/ci.yml`, `docs.yml`; `sonar-project.properties` | kiln | managed |
| `CLAUDE.md`, `AGENTS.md` | body **seeded by kiln** (D58); `<!-- BEGIN rn-forge kiln -->` block → kiln | seeded body + block |
| `.claude/**`, `.codex/**`, installed skills | **unowned** (D58) — [agent-config-future.md](agent-config-future.md) | — |
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
    cli.py                 # rn_forge.cli.CliApp + --dry-run/--yes/--json
    config.py              # pydantic schema for config.toml (§2.5.2), load/validate
    umbrella.py            # .rn-forge/ discovery ($RNF_HOME, find_root markers), gitignore block
    artifacts.py           # kiln provider: repo-standardization artifacts and render inputs
    cycle.py               # thin adapter from kiln config to the tooling generation engine
    modules/               # revision 14 (D72, D74): each a KilnModule — config model, options, artifacts, checks
      base.py              # KilnModule protocol + registry
      core/                # umbrella, config manager (D70), state, cycle adapter, .gitignore block, .editorconfig, standard.md
      python/              # uv init + reconcile, .importlinter, pyproject check 8a, rn-forge dependency set
      docs/                # docs tree, _areas.yml, _structure.md, mkdocs.yml nav block
      tasks/               # Taskfile.yml + tasks/*.yml
      cicd/                # workflows, .github/actions/setup, sonar-project.properties, pin set
      instructions/        # README/CLAUDE/AGENTS seeds + kiln block
  packages/rn-forge-kiln-checks/src/rn_forge/kiln/checks/
      core/ python/ docs/ tasks/ cicd/   # render-free checks per module; CI's console scripts (D74)
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

#### 2.5.2 `.rn-forge/kiln/config.toml` (kiln configuration design)

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

[cli]                             # shared CLI design; rendered by kiln, read by rn-forge-cli
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
1. core         .rn-forge/kiln/, gitignore block, .editorconfig
2. python       (new only) uv init / pnpm create / nx g, then reconcile to archetype; .importlinter
3. docs         tree, _areas.yml, _structure.md, mkdocs.yml block
4. tasks        Taskfile.yml, tasks/*.yml
5. ci           workflows, sonar-project.properties
6. instructions README.md / CLAUDE.md / AGENTS.md bodies (seeded), the kiln block in
                the latter two, .rn-forge/kiln/standard.md
7. doctor       run every check; apply exits non-zero if any error remains
```

No step shells out to another kit (D58). `scripts/**` is gone from steps 3 and 4
under verification packaging proposal: the checkers are a pinned dev dependency,
not generated files.

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
| 8 | `gate.shrunk` | the set of tasks reachable from `validate` ⊇ the archetype's `required_validate` list; `rn-forge-kiln-checks`' `check-task-layout` enforces the same list in CI, reading it from `config.toml` |
| 8a | `pyproject.tool-config` (warning) | the `[tool.ruff*]`, `[tool.pyright]`, `[tool.pytest.ini_options]` and `[dependency-groups]` tables match the archetype's expected values. **Verified, never written** — pyproject stays repo-owned (D60) |
| 8b | `checks.version` | `rn-forge-kiln-checks` is a dev dependency, pinned, and its `schema_version` understands the committed `state.json` (verification packaging proposal) |
| 9 | `ci.unpinned` / `ci.permissions` | every `uses:` is SHA-pinned with a version comment; every job has `permissions:` |
| 10 | `docs.structure` / `.nav` / `.links` | tree matches the repo's `_areas.yml`; nav block current; no broken links/anchors/orphans |
| 11 | `hygiene.stray-root-file` (warning) | tracked root-level `*.md` not in the allow-list (`README.md`, `CLAUDE.md`, `AGENTS.md`, `LICENSE`, `CHANGELOG.md`) |
| 12 | `legacy.kiln-state` (error) | a pre-existing `.rn-forge/kiln/` or `$RNF_HOME/kiln/` tree without `schema_version` (§0.4) |

`kiln doctor --all <paths>` runs the same checks over many repos and prints one
table (F11).

### 2.6 Archetypes, golden repos and the docs profile (kiln archetype design)

| Archetype | Shape | Model repo (prior art) | Golden fixture | Release tag |
| -- | -- | -- | -- | -- |
| `python-app` | uv single package, src layout, optional internal-only workspace packages | intellibuild batches | `golden/python-app` | `v<version>` |
| `python-tool` | **alias for `python-app` + `lifecycle = true` (D61)** — self-install, `$RNF_HOME`, local state, plugins, doctor (the lifecycle surface, D59) | agentkit `self_command.py`, kiln | `golden/python-tool` | `v<version>` |
| `python-lib` | uv workspace of published library packages; per-package verify + release | pykit | `golden/python-lib` | `<package>-v<version>` |
| `python-web-api` | uv workspace, one API service, no separate frontend package; optional thin admin UI | — | `golden/python-web-api` (fastapi) | `v<version>` |
| `python-web-app` | uv workspace + API + pnpm-managed Nx frontend, one MkDocs site over both | apollo, intellibench `docs2/` | `golden/python-web-app-django`, `golden/python-web-app-fastapi` | `v<version>` |
| `node-lib` | pnpm/Nx workspace of published UI libraries | ngkit | *deferred* | `<package>-v<version>` |
| `node-web-app` | standalone pnpm-managed Nx frontend against remote APIs | — | *deferred* | `v<version>` |

**Flags, not archetypes, for the implementation library (D54).**
`--framework django|fastapi` on the web archetypes,
`--frontend angular|react|svelte` on `python-web-app`, and `lifecycle` on any
Python archetype (D61) change neither the file topology nor the task graph,
which is the whole rule. Every shipped value has a golden repo; a value without
one is `untested = true` and `kiln new` refuses it. v1 ships `python-web-app`
with `django + angular` and `fastapi + angular`, and `python-web-api` with
`fastapi`. Six golden repos, not the fourteen the matrix could name.

**Golden repos are the source of truth for templates (D43, revised by D63 — read
§0.10 before acting on this paragraph).** Under D63 the templates are authored
and the goldens are committed *rendered* snapshots, with a matrix harness
proving runnability across every shipped combination. What is written below
still describes the property each golden must hold. Each golden fixture is a
complete, *runnable* repo: `uv sync` and `task validate` pass in it standalone,
its workflows lint, its docs site builds `--strict`, and its committed checkers
run. They are reviewed as if they were the finished product *before* any
generator code exists (Phase B). The templates are then the golden output
parameterized, and kiln's snapshot tests assert
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
| `.importlinter` contracts | ✔ | ✔ | ✔ | ✔ |
| `README.md`, `CLAUDE.md`, `AGENTS.md` bodies (seeded); the kiln block in the latter two | ✔ | ✔ | ✔ | ✔ |
| `docs/_areas.yml`, `docs/_structure.md`, `docs/adr/_structure.md`, seeded index pages, `mkdocs.yml` nav block | d | d | d | d |
| `.github/workflows/ci.yml` (validate → sonar → check-version → build → publish) | ✔ | ✔ | ✔ (matrix over `packages`) | ✔ (+ pnpm/node setup) |
| `.github/workflows/docs.yml` (Pages deploy on main) | d | d | d | d |
| `sonar-project.properties` | s | s | s | s |

**`scripts/**` is not in that table (verification packaging proposal, D51).**
The four policy checkers ship in `rn-forge-kiln-checks` and the four docs
checkers in `rn-forge-tooling`; both are pinned dev dependencies, and
`tasks/quality.yml` calls their console scripts rather than
`python scripts/...`. `pyproject.toml` is not in it either, for the opposite
reason (D60): it is repo-owned and verified by doctor check 8a. A generated repo
has no `scripts/` directory unless it writes its own lints.

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
| ADR numbering, epic/feature/release naming, instruction filenames in `docs/structure.py` | **`rn-forge-kiln-checks`** (Phase D) | rn-forge policy, which ownership policy says is kiln's; tooling takes an explicit policy object instead (A2) |

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

### 2.9 The tool lifecycle surface (D59)

`python-app` and `python-tool` currently differ by a package name and one
dependency line. That is the whole evidence for D53, and it is not enough:
`rn-forge-tooling/install/` contains `archive.py` and nothing else, so
`$RNF_HOME`, self-install, local state and a tool doctor exist in the plan and
in no code. Phase C.3 builds them, in `rn-forge-tooling`, because they are
mechanism; the *policy* of any one tool stays in that tool.

**The seam is an adapter, and it is the one kiln's own modules already use** —
`artifacts()` + `checks()`, nothing else (§4). A product implements a protocol;
`rn-forge-tooling` owns every algorithm around it.

```python
class ToolProduct(Protocol):
    name: str                 # "agentkit"; $RNF_HOME/<name>/
    version: str
    release_source: ReleaseSource        # default: GitHub releases of `repo`
    state_schema_version: int

    def artifacts(self) -> Sequence[Artifact]: ...   # what `install` puts in place
    def checks(self) -> Sequence[Check]: ...         # product-specific doctor rows
    def migrate(self, frm: str, to: str) -> None: ...  # default: no-op
```

Every member is defaulted, so a trivial tool implements none of them and still
gets the verbs. Tooling supplies:

| Module | Owns |
| -- | -- |
| `install/home.py` | `$RNF_HOME` resolution, `<home>/<product>/versions/<v>/`, the `current` symlink (commons `atomic_symlink`, `DirectoryLock`) |
| `install/release.py` | resolve the latest tag, download, verify, extract (`archive.py`) |
| `install/lifecycle.py` | `install`, `upgrade`, `uninstall`, `cleanup`, `status`, `doctor` as transactional sequences over the protocol |

**The command line stays declared, not written (shared CLI design).** A
`[cli.lifecycle]` table in `.rn-forge/kiln/config.toml` lists which verbs the
tool exposes, and `CliApp.from_config` mounts them. **The table is gated by
`lifecycle = true`, a capability flag orthogonal to the archetype (D61)** —
which is why kiln itself, a `python-lib`, gets these verbs without being a
`python-tool`. `golden/python-tool` needs no `main.py` at all and
`golden-tool doctor` works — which is the acceptance test D53 never had, in the
same shape as the one D49 got in Phase C.2 step 10.

Two doctors, deliberately: **`kiln doctor` inspects a repository** (§2.5.6); **a
tool's `doctor` inspects its own install**. Both emit commons `Finding`, neither
knows about the other.

Prior art is agentkit's `commands/self_command.py` and `core/doctor.py`; read
them, port nothing. agentkit itself is out of the plan (D58) — see
[agent-config-future.md](agent-config-future.md).

### 2.10 The canon inside kiln (D36)

The standard has three forms, all owned by kiln, and one rendering mechanism:

| Form | Where | Audience |
| -- | -- | -- |
| **Decisions** — ownership policy…0008 (revision-6 U001–U008) | `kiln/docs/adr/` | kiln's maintainers; anyone asking *why* |
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
`kiln/docs/architecture/workspace.md` and is referenced, not repeated, from the
repos that need it. Runbook: `docs/runbooks/creating-a-repo.md` (`kiln new`,
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
  app.py             CliApp (typer.Typer subclass) + ExitCode + run
  options.py         --json --dry-run --yes --log-level --set; CliOptions
  surface.py         the [cli] surface records (shared CLI design)
                     (AppConsole lives in rn_forge.commons.runtime.console)

rn_forge/tooling/
  __init__.py        lazy facade — no eager import of jinja2
  generation/        artifacts.py  plan.py  apply.py
  templates.py       TemplateEngine
  state.py           StateStore
  install/           archive.py (extract_archive)  home.py ($RNF_HOME)
                     release.py  lifecycle.py  product.py (ToolProduct, §2.9)
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
test -f docs/adr/ADR-0006.md && test -f docs/reference/standard-repo.md && test -f docs/plans/harvest.md
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

**kiln verification packaging proposal is settled (D51).** The four docs
checkers (`check_docs`, `check_structure`, `gen_nav`, `_common` — 775 lines with
no per-repo variation) **are** part of what this phase extracts into tooling;
the four policy checkers go to `rn-forge-kiln-checks` in Phase D. Extract the
docs checkers here, not later, or they get moved twice.

**Added after the Phase B review.** The golden repos depend on
`rn-forge-commons` at a pinned tag and use it; `rn-forge-tooling` could not be
wired because it does not exist yet. This phase must therefore also:

1. **Split commons against shared CLI design's target**, not symbol by symbol.
   The Typer helpers, `AppConsole`, `StateStore` and `TemplateEngine` move to
   tooling as one coherent surface, because the point of tooling is that a
   repo takes its whole CLI/console/state layer from it rather than assembling
   one.
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

### Phase C.2 — the layer split, the re-layout, and the defect fixes *(1 week)* — **done; step 9 deferred by D73**

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
   `rn_forge.cli`: the Typer application class, the standard options, logging
   wiring, error-to-exit-code, the declared `[cli]` surface. (`AppConsole`
   went on to commons in pykit plan Part E.) `rn-forge-tooling` keeps
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

1. **Rename the golden repos and add the missing ones (D53).** — **done.**
   `golden/python-cli` → `golden/python-tool`; a new `golden/python-app`.
   `golden/python-lib` is unchanged. Update kiln's own
   `.rn-forge/kiln/config.toml` to `python-tool`, re-render
   `.rn-forge/kiln/standard.md`, and **re-seed `state.json`**.

1. **Close Phase C's addendum (F8).** — **open, deliberately.** Cut the first
   `rn-forge-cli` and `rn-forge-tooling` releases; point `golden/python-app`
   at `rn-forge-cli` and `golden/python-tool` at both; re-point every commons
   pin at the release cut after the boundary change; update each
   `check_rn_forge_deps.py` `REQUIRED` header; re-seed every `state.json`.

    The `REQUIRED`/`ALLOWED` headers and the dependency lines are already in
    place, and the golden repos already exercise all three libraries. What is
    not done, and is held back on purpose, is the *pin*: every rn-forge
    requirement names pykit's published `feature/upgrade` branch rather than a
    tag, so that upgrades found while exercising the golden repos land without
    re-cutting a release. A branch pin satisfies `check_rn_forge_deps.py` —
    `git+…@<ref>` is a ref — and `uv.lock` records the resolved commit, so the
    build is reproducible meanwhile. **kiln's templates must not be written
    against it**: this is an interim state for a fixture, not the contract.

1. **The acceptance test shared CLI design never had.** — **done.**
   `golden/python-app` contains a working CLI with **zero hand-written app
   construction** — a `main()`, its commands, its tests, and nothing else. If
   that repo cannot be written, shared CLI design is not ready and D49 stays
   proposed.

    `src/golden_app/cli.py` is one line — `app = CliApp.from_config(...)` — with
    `[project.scripts]` pointing at it and no `main()`; the surface is the
    `[cli]` table in `.rn-forge/kiln/config.toml`; `commands.py` holds one
    function with no Typer import, which `.importlinter` enforces.
    `golden/python-tool` is built the same way, and additionally exercises
    `rn-forge-tooling` by rendering its greeting through `TemplateEngine`.
    **D49 is met on the evidence shared CLI design asked for.**

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

### Phase C.3 — pykit: the tool lifecycle surface *(3 days)* — **not started**

Repo `rn-forge/pykit`, branch `feature/upgrade`. Mechanism only; no kiln change.
Follow pykit's own conventions (`docs/plans/commons-upgrade-plan.md` ground
rules: no compatibility re-exports, `.importlinter` contracts kept).

1. **`rn_forge/tooling/install/`** (§2.9, D59): `home.py` (`$RNF_HOME`, the
   `<home>/<product>/versions/<v>/` tree, the `current` symlink via commons
   `atomic_symlink` + `DirectoryLock`), `release.py` (resolve latest tag,
   download, verify, extract with `archive.py`), `product.py` (`ToolProduct`,
   every member defaulted), `lifecycle.py` (`install`, `upgrade`, `uninstall`,
   `cleanup`, `status`, `doctor`). Transactional in the shape of
   `generation/apply.py`: stage, back up, swap `current` last, restore on
   failure. Tests: failed download, failed migration, interrupted swap,
   `uninstall` over an install that never completed.
1. **`[cli.lifecycle]`** — a `CliSurface` record (on `StrictDataclassMixin`,
   like the rest of the surface) listing the verbs, and `CliApp.from_config`
   mounting them against a product object named in the table. `rn-forge-cli`
   must not import tooling (contract), so the mount resolves the product and
   the lifecycle functions by import string, the same way `[[cli.commands]]`
   targets already are.
1. Docs: tooling's guide gains a lifecycle page; cli's surface page documents
   the table.

**Acceptance**

```bash
cd rn-forge/pykit
uv run pytest -q packages/rn-forge-tooling packages/rn-forge-cli
uv run lint-imports && uv run pyright && uv run ruff check .
! rg -q 'rn_forge\.tooling' packages/rn-forge-cli/src
```

### Phase C.4 — kiln: realign the goldens and the canon with pykit *(3 days)* — **not started**

Repo `rn-forge/kiln`, branch `feature/v1`. The hand-authored goldens are the
reference Phase D writes templates from (D69), so they must match pykit as it
is, not as it was. Steps 1, 2 and 4 are independent of Phase C.3; step 3 waits
for it.

1. **Port `golden/python-app` and `golden/python-tool` to the Part E API.**
   `main.py` becomes `app = CliApp.from_config(CONFIG)` with no `main()` and
   no `run`; `[project.scripts]` points at `golden_app.main:app`;
   `commands.py` imports `console` from `rn_forge.commons`. Fix every prose
   reference to `rn_forge.cli.declare` / `build_app` in both goldens'
   `README.md`, `docs/architecture/repository-shape.md`,
   `docs/adr/ADR-0001.md` and the `config.toml` comment. Confirm neither
   `[cli]` table carries a key Part E deleted (`log_options`,
   `output_options`).
1. **Pins, per D73.** Every rn-forge requirement in every golden — including
   `python-lib/packages/golden-{alpha,beta}`, which still pin
   `rn-forge-commons-v0.2.2` — names `@feature/upgrade`. `uv lock --upgrade`
   in each golden, so the lock reaches `f59c40f` or later. Path sources are
   not used in goldens: they must stay CI-capable.
1. **Make `golden/python-tool` a tool** (after C.3). It declares
   `[cli.lifecycle]` and implements `ToolProduct` in one small module
   (`artifacts()` returning its one global artifact, one `checks()` row). Its
   `config.toml` records `archetype = "python-app"` + `lifecycle = true`
   (D61). `golden/python-app` gains no `$RNF_HOME` or lifecycle reference —
   the diff between the two is the flag and nothing else.
1. **The canon catches up.** In `docs/reference/standard-repo.md`: remove
   agentkit from the ownership table and the prose (D57, D58; `.claude/**`
   becomes unowned); add `rn-forge-web` beneath django and fastapi in the
   dependency-set table; state D69 (no committed goldens, the render matrix),
   D70 (config sources and lifecycle, in §9), D72/D74 (the module contract,
   `core`, and checks as the render-free half) and D73 (branch/path pins until
   release). archetype design amended for D61, D69 and D72; verification
   packaging proposal amended for D74; configuration design for D70's
   `[source]` table. A new ADR only if the owner wants the alternatives recorded
   beyond §5.
1. **Re-seed `state.json`** in every repo touched, and update the kiln
   `README.md` "Where kiln is" paragraph.

**Acceptance**

```bash
cd rn-forge/kiln
! rg -q 'rn_forge\.cli\.declare|build_app|from rn_forge\.cli import console' tests/fixtures/golden
! rg -q 'def main' tests/fixtures/golden/python-app/src tests/fixtures/golden/python-tool/src
! rg -q 'rn-forge-commons-v0\.2\.2' tests/fixtures/golden
! rg -qi 'agentkit' docs/reference/standard-repo.md
rg -q 'rn-forge-web' docs/reference/standard-repo.md
for g in tests/fixtures/golden/python-app tests/fixtures/golden/python-tool tests/fixtures/golden/python-lib; do
  (cd "$g" && uv sync && task validate) || echo "FAIL $g"
done
(cd tests/fixtures/golden/python-tool && uv run golden-tool doctor && uv run golden-tool status --json | jq -e '.version')
! rg -q 'RNF_HOME|lifecycle' tests/fixtures/golden/python-app
task lint
```

### Phase D — kiln: the generator *(2–3 weeks)* — **not started**

Repo `rn-forge/kiln`, which becomes a **`python-lib` workspace of two
distributions**: `rn-forge-kiln` (module `rn_forge.kiln`) and
`rn-forge-kiln-checks` (module `rn_forge.kiln.checks`). Depends on Phases C.3
and C.4. rn-forge dependencies are branch-pinned (D73). Sub-phases are
sequential; each ends green on `task validate`.

#### D.1 — `rn-forge-kiln-checks`, organized by module (D74, verification packaging proposal)

1. Convert the repo to a uv workspace: `packages/rn-forge-kiln/`,
   `packages/rn-forge-kiln-checks/`. kiln's own `config.toml` stays
   `python-tool` until D.9.
1. Port the four policy checkers from the goldens' `scripts/` into the module
   that owns each rule, replacing each `# BEGIN kiln config` header with a
   read of `.rn-forge/kiln/config.toml`: `checks/core/generated.py`
   (`check-generated`), `checks/python/rn_forge_deps.py`
   (`check-rn-forge-deps`), `checks/tasks/layout.py` (`check-task-layout`),
   `checks/cicd/entrypoint.py` (`check-ci-entrypoint`), plus
   `checks/docs/policy.py` — the docs policy object tooling's docs checkers
   take (A2). One console script per check and an aggregate `kiln-checks`.
   **No import of `rn_forge.kiln`, no Jinja** — an `.importlinter` contract
   holds it. Refuse an unknown `state.json` `schema_version` loudly.
1. In the three goldens and in kiln itself: delete `scripts/**`, add
   `rn-forge-kiln-checks` to the dev group (a local path source in the goldens
   while it is unreleased — goldens are validated locally, D69), point
   `tasks/quality.yml` at the console scripts, delete
   `tests/support/assert_generated_bodies.py` and its test, re-seed
   `state.json`.

#### D.2 — the `core` module, the config manager and the module contract (D70, D72, D74)

1. `modules/base.py` — `KilnModule` (§0.11) and the registry;
   `archetypes/*/ archetype.toml` lists `modules`, the dependency set,
   `forbidden_tools`, `required_validate`.
1. `core/config/` — the composed schema (`schema_version`, `[repository]`,
   `[source]`, one section per enabled module); layered resolution from a path
   or git URL; list-replace deep merge; per-key provenance recorded in state;
   schema compatibility on every load; override preservation on re-resolution.
   Built on commons `DictUtils.merge_layers` and documents, not reimplemented.
1. `core/` artifacts — `.rn-forge/kiln/` umbrella, `find_root`, the `.gitignore`
   block, `.editorconfig`, `.rn-forge/kiln/standard.md`, `legacy.kiln-state`
   detection (§0.4). `core/cycle.py` — the thin adapter over tooling
   `generation`. Core's `checks()` wraps `checks.core`.
1. Tests: every validation failure with its dotted path; list replacement;
   override preservation; a newer-schema config refused; a disabled module's
   section rejected; two modules declaring the same option refused at startup.

#### D.3 — the concern modules, with templates

In apply order, one at a time, each with its config model, options, Jinja
templates written from the C.4 goldens, and `checks()` = its `checks.<module>`
functions + its render-dependent checks (`artifact.stale`, `block.stale`):

`python` (`uv init` + reconcile, `.importlinter`, pyproject check 8a including
`[project]` identity per D62, rn-forge dependency set incl. `lifecycle`) →
`docs` (tree, `_areas.yml`, `_structure.md`, `mkdocs.yml` nav block) → `tasks`
(`Taskfile.yml`, `tasks/*.yml`, repo-owned includes, `extra_refs`) → `cicd`
(workflows, `.github/actions/setup`, `sonar-project.properties`, pin set) →
`instructions` (`README.md`/`CLAUDE.md`/`AGENTS.md` seeds, the kiln block).

Per-module tests: rendering on small configs; a fresh directory classifies as
only `CREATE`/`INSERT`/`SKIP`; a second apply is all `UNCHANGED`.

#### D.4 — the render matrix, and the goldens leave git (D69)

1. kiln's repo-owned `tasks/self.yml`: `self:golden:render [REF=<git-ref>]`
   writes every shipped archetype × flag cell to
   `.goldens/<ref>/<archetype>[-<flag>=<value>…]/` (gitignored in the repo
   body); `self:golden:validate` runs `uv sync && task validate`, `actionlint`
   and `mkdocs build --strict` per cell and prints one pass/fail table.
1. kiln's CI runs the render for every cell per pull request; validate is local.
1. **Bootstrap exit:** each rendered cell for `python-app`, `python-app` +
   `lifecycle` and `python-lib` equals its hand-authored golden apart from
   name and provenance-version lines; the owner approves the rendered output;
   then `tests/fixtures/golden/` is deleted.

#### D.5 — CLI

`cli.py` on `CliApp.from_config` (kiln's own `[cli]` table): `new` (with
`--config <path|git-url[@ref]>`), `apply`, `doctor`, `diff`, `version`,
`config update`, `config upgrade` (both `--dry-run`/`--apply`), and the
lifecycle verbs including `upgrade` via `[cli.lifecycle]` (D61, D70). `new`
tested with stdin closed and every flag given.

#### D.6 — doctor

Iterates modules in `archetype.toml` order and prints one `Finding` report:
checks 1–12, 8a, 8b (§2.5.6). `doctor/taskgraph.py` ported from taskkit
`validator.py` with its tests. `--all <paths>`.

#### D.7 — import contracts

`rn_forge.kiln` forbids `rn_forge.django`/`rn_forge.fastapi`/`rn_forge.web`;
`rn_forge.kiln.checks` forbids `rn_forge.kiln` and `jinja2`; each concern module
may import `core` and not its siblings.

#### D.8 — self-hosting

kiln's config becomes `archetype = "python-lib"` + `lifecycle = true` (D61).
`kiln apply --force` once; the second apply reports all `UNCHANGED`. kiln's
hand-copied skeleton is gone.

**Acceptance**

```bash
cd rn-forge/kiln
task validate && uv run lint-imports
task self:golden:render && task self:golden:validate
test ! -d tests/fixtures/golden
scratch=$(mktemp -d)
uv run kiln new "$scratch/demo" --archetype python-tool --docs mkdocs --yes --json </dev/null | jq -e '.artifacts | length > 0'
cd "$scratch/demo" && uv sync && task validate
uv run --project "$OLDPWD" kiln apply --dry-run --json | jq -e 'all(.artifacts[]; .action == "unchanged")'
printf '\n# edit\n' >> Taskfile.yml
! uv run check-generated .
! uv run --project "$OLDPWD" kiln apply
uv run --project "$OLDPWD" kiln apply --force Taskfile.yml
cd "$OLDPWD" && uv run kiln doctor && uv run kiln apply --dry-run --json | jq -e 'all(.artifacts[]; .action == "unchanged")'
```

### Phase E — the web archetypes *(2 weeks)* — **not started**

Repo `rn-forge/kiln`. **Gated on `rn-forge-fastapi`** reaching its plan's
acceptance in pykit; `rn-forge-web` already exists. Under D69 there are no
hand-authored goldens: templates are written directly and approved through the
render matrix.

1. Library sets: `python-web-api`/`python-web-app` take commons → web →
   `rn-forge-django` or `rn-forge-fastapi` (+ `rn-forge-cli` for management
   commands), `[codegen]` extras in dev only (D37).
1. `python` module gains the web shapes; `tasks` gains `tasks/api.yml` and, for
   `python-web-app`, `tasks/web.yml` (`pnpm nx run-many -t lint|test|build`);
   `cicd` gains pnpm/node setup; `forbidden_tools` adds `pnpm npx nx`.
1. `framework = fastapi|django` changes only `tasks/api.yml` primitives and the
   scaffold reconcile — never topology or task graph (D54).
1. `kiln new` end to end with `nx g` for the frontend; reconcile to `web_dir`.
1. Move taskkit's
   `tests/fixtures/repos/{python-pnpm-monorepo,python-django,python-fastapi*,python-angular-pnpm}`
   into `tests/fixtures/repos/` as scaffold-reconcile inputs.
1. Shipped cells: `python-web-api` + fastapi; `python-web-app` + django +
   angular; `python-web-app` + fastapi + angular. `react`, `svelte` and
   `python-web-api` + django stay `untested = true`.

**Acceptance**

```bash
cd rn-forge/kiln
task self:golden:render && task self:golden:validate   # all web cells pass
scratch=$(mktemp -d)
uv run kiln new "$scratch/web" --archetype python-web-app --framework fastapi --frontend angular --docs mkdocs --yes </dev/null
(cd "$scratch/web" && uv sync && pnpm install && task validate && uv run --project "$OLDPWD" kiln doctor)
```

### Phase F — rebuild the repos, retire the old *(3 weeks)* — **not started**

Per repo: `kiln new` into a fresh directory, port source and docs by hand,
`kiln doctor` and `task validate` green, then the fresh tree replaces the repo's
working tree on a branch. History before the replacement is not preserved (D39).

1. **pykit skeleton** (`python-lib`).
   `kiln new pykit-fresh --archetype python-lib --docs mkdocs`; set
   `[python] packages`; move `packages/`, `docs/`, the `mkdocs.yml` body and
   the root workspace tables in; `extra_refs` for anything the generated
   matrix does not cover; delete `_package-ci.yml`. Package source is
   untouched. Needs only Phase D.
1. **kiln** — already self-hosted (D.8).
1. **agentkit** — not in this phase (D58).
1. **intellibuild** — gated on Phase E and on `docs2/REFACTOR_PLAN.md` reporting
   complete; its archetype is open question 16. `docs2/` lands as `docs/` with
   a `context` area; repo-local lints via `extra_refs` (D34).
1. **taskkit** — archive (README banner, tag `archived/v0.2.0`, GitHub archive).
   **intellibench** — archive after intellibuild's first release. **apollo** —
   stays parked.

**Acceptance**

```bash
kiln doctor --all rn-forge/pykit rn-forge/kiln walgreens/intellibuild --json | jq -e '.summary.errors == 0'
for r in rn-forge/pykit rn-forge/kiln walgreens/intellibuild; do (cd "$r" && task validate && uv run lint-imports); done
```

### Phase G — ongoing

CI runs `task validate`, which reaches `rn-forge-kiln-checks`' console scripts;
it never installs or invokes kiln. Developers run `kiln doctor`;
`kiln doctor --all` is the cross-repo signal. A kiln upgrade is `kiln upgrade`,
then `kiln config upgrade --dry-run`, review, `--apply`.

**Triggered, not scheduled:**

- **pykit releases (D73).** When the owner declares pykit stable: cut the tags
  in the order commons → cli → tooling → web → django/fastapi (pykit plan
  D.8), release `rn-forge-kiln-checks`, flip the rn-forge source value in
  kiln's defaults from branch to tag, and run `kiln config upgrade --apply` in
  each repo.
- **ADO (D4)** — add `ci.provider = "ado"` to `cicd` when a repo needs it.

### Critical path

```text
done:  A ─→ B ─→ C ─→ C.2
next:  C.3 (pykit lifecycle) ──┐
       C.4 (kiln realign) ─────┴─→ D.1 checks ─→ D.2 core ─→ D.3 modules ─→ D.4 matrix
                                   (goldens leave git) ─→ D.5 CLI ─→ D.6 doctor ─→ D.7 ─→ D.8 self-host
                                                                              │
       rn-forge-fastapi (pykit) ───────────────────────────────────────────────┴─→ E ─→ F.4 intellibuild
                                                                   D.8 ─→ F.1 pykit skeleton
triggered: pykit releases (owner) · ADO
```

C.4 steps 1, 2 and 4 can start immediately alongside C.3; C.4 step 3 waits for
C.3. Nothing in Phase D waits on a pykit release any more (D73), but every
template Phase D writes renders the rn-forge dependency source from config, so
flipping to tags later is a config change, not a template change.

______________________________________________________________________

## 4. Risks

- **kiln becoming a god-kit.** Guard: every module is `artifacts()` +
  `checks()`, nothing else; no detection code anywhere; the archetype is
  always asserted by config; no adopt.
- **A template change reaching repos unreviewed** (D69 — no committed goldens
  means no diff in the pull request). Guard: a template change is not done
  until the owner has approved `task self:golden:render` output, and kiln's CI
  renders every cell so a broken template cannot merge.
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
- **The re-ideated agent tool never happens, and `.claude/**` stays unowned.**
  Accepted: no repo in scope needs it to build, `kiln apply` no longer calls
  it, and the current agentkit keeps working by hand meanwhile (D58).
- **Phase C.3 grows into an installer framework.** Guard: every `ToolProduct`
  member is defaulted, the only acceptance is `golden-tool doctor` and
  `golden-tool status`, and nothing in v1 self-installs except kiln.
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
| D15 | ~~Apply sequence is umbrella → scaffold → docs → tasks → ci → agentkit → instructions → doctor.~~ | **Revised by D58** — step 6 is gone; the sequence is umbrella → scaffold → docs → tasks → ci → instructions → doctor (§2.5.5) |
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
| D30 | kiln ships no skills. Judgement lives in kiln runbooks. | Confirmed |
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
| **D43** | **Golden repos are the source of truth for templates.** Hand-authored, runnable, reviewed before generator code exists; templates are derived from them; snapshot tests are byte-exact. | **Revised by D63** — the direction of authorship inverts (templates are authored, goldens are committed rendered snapshots) and a matrix harness takes over the *runnable* proof. The *reviewed as committed bytes* property survives intact, and it is why goldens stay in git at all |
| D44 | `docs/_areas.yml` and `_structure.md` are seeded, not managed, so a repo can extend its areas (intellibuild's `context`). Doctor validates against the repo's copy. | **Confirmed** — the generated docs scripts now depend on it: `_common.load_areas` has no fixed key list, and kiln's own tree adds a `plans` area |
| **D45** | **CI stays generated and committed; no reusable-workflow devops repo.** Pinned reusable workflows cost the same per-repo commit to propagate a fix as `kiln apply` does, and add an external repo dependency at CI time; floating the ref removes that churn but makes CI unpinned — apollo's `branch = "main"` failure in another form. The reviewability win is taken instead via a committed composite action, `.github/actions/setup`. Revisit only if per-repo churn measurably hurts. | **Confirmed** |
| **D46** | **rn-forge dependencies are pinned PEP 508 direct URLs in `dependencies`**, never `[tool.uv.sources]` — a source override does not survive into a built wheel, so a consumer of a published package could not resolve commons at all. Accepted: such a distribution cannot be uploaded to PyPI, and the tag *is* the version. Publishing to PyPI later relaxes this rule rather than breaking it. | **Confirmed** |
| **D47** | ~~**Four archetypes: `python-cli`, `python-lib`, `python-django-ng`, `python-fastapi-ng`.**~~ `-ng` means a pnpm-managed Nx workspace (Nx's own documented shape); `nx_cloud` is a config key, being an account decision rather than a repo shape. The `backend` and `web_runner` keys are removed: the archetype name says what the repo is. Supersedes D7. | **Superseded by D53/D54** — the catalogue and the flag rule both changed; the underlying principle (the name states the topology) survives |
| **D48** | **ADRs carry decisions; the reference carries specifications.** kiln's ADRs are restructured to nine, each with an *Alternatives considered* section; the verb list, ownership table, dependency sets, doctor codes, CI shape and config schema all live in `docs/reference/standard-repo.md`. An ADR that starts enumerating has become a spec. | **Confirmed** |
| **D50** | **`ruff check --fix` runs before `ruff format`, and `lint:python` mirrors `format:python`.** The linter's fixes are edits; running the formatter first leaves them unformatted. `lint:format` is removed as a separate task. | **Confirmed** |
| **D51** | **The checkers become a versioned package** (`rn-forge-kiln-checks`), split from the kiln CLI, with the docs checkers going to tooling; only `state.json`, `config.toml` and `standard.md` stay committed (kiln verification packaging proposal). Preserves CI policy's actual rule — CI never renders — while removing 1,454 duplicated lines per repo. Both distributions live in the kiln repo, which becomes a `python-lib` workspace in Phase D. The name is `checks`, not `devops`: `checks` names a role that excludes rendering, `devops` names a domain that excludes nothing. | **Confirmed**; reorganized by module by D74 |
| **D49** | **The libraries own the CLI, logging and state boilerplate, and a repo declares its CLI surface rather than writing it** (kiln shared CLI design). Not an application generator — D2 is unchanged. Phase C's package split is made against this target. | **Proposed** — revised by D52: the CLI boilerplate is `rn-forge-cli`, not tooling. Stays proposed until `golden/python-app` demonstrates a CLI with zero hand-written app construction |
| **D52** | **Three library layers, not two: `rn-forge-commons` → `rn-forge-cli` → `rn-forge-tooling`** (kiln dependency boundary). The seam is not workstation-versus-runtime but *every CLI* versus *tools that install, generate and own files*. A business batch or ML job takes `rn-forge-cli` and gets shared CLI design's zero-boilerplate `main()` without Jinja2, a generation engine, or a package whose contract tells deployed code not to depend on it. Placement is decided by what an API's **signature** contains, not by who calls it today: `DirectoryLock` and `atomic_symlink` return to commons, `extract_archive`/`StateStore`/`TemplateEngine` stay in tooling, `ManagedBlock` stays in commons. Rejected: a `[gen]` extra (an extra adds dependencies, it does not exclude modules or stop an eager initializer) and renaming tooling to `devtools`/`automation`/`core` (no architectural property changes). Refines D29/D35. | **Confirmed** |
| **D53** | **Seven archetypes: `python-app`, `python-tool`, `python-lib`, `python-web-api`, `python-web-app`, `node-lib`, `node-web-app`** (kiln archetype design). `python-cli` was two repos under one name — a batch behind a command line, and an installable tool that owns `$RNF_HOME`, state and plugins — with different library sets, which is what forced tooling to be a package most of the fleet was told not to use. The `-ng` pair collapses into `python-web-api`/`python-web-app`: the framework does not change the topology, a separate frontend package does. The two node archetypes are named and deferred to post-v1 — a second toolchain, and nothing in v1 scope uses them. "Is it a monorepo" is not the axis; **publishing** is. Supersedes D47. | **Confirmed** |
| **D54** | **A config flag may select an implementation library only when it changes neither the file topology nor the task graph, and every shipped value has a golden repo.** `framework = django\|fastapi` and `frontend = angular\|react\|svelte` pass; the rejected `backend` + `web_runner` pair failed because together they selected four topologies. The golden-repo rule is what stops flag freedom from reintroducing the combinatorial explosion D47 avoided: v1 ships six golden repos, not the fourteen the matrix could name. A value without one is `untested = true` and `kiln new` refuses it. | **Confirmed** |
| **D55** | **commons, cli and tooling are laid out as sub-packages by kind of mechanism** (§2.11): `lang/`, `fs/`, `data/`, `logging/`, `runtime/`, `integration/` in commons, and equivalents in the other two. **Public class names do not move** and the package facade keeps re-exporting them, so only submodule paths change; no compatibility shims, because D39 already says rebuild rather than migrate. `AppUtils` stays an acknowledged grab bag rather than breaking a public name for tidiness. | **Confirmed** |
| **D56** | **kiln generates repo structure; frameworks generate their own code.** `kiln generate package <name>` — adding a package to a workspace — is in scope for Phase D, because it emits the same repo structure kiln already owns. Application code generators (django model/serializer/api, UI wrappers) stay D2/D37: they ship in `rn-forge-django[codegen]`, register under `rn_forge.kiln.generators`, and kiln supplies only the command surface. The line is whether the output is repo shape or application logic. | **Confirmed** |
| **D57** | **README.md is the single prose home.** Developer-facing prose is written once, in the file a human opens first; `CLAUDE.md` is a pointer to it plus the fenced blocks, and `AGENTS.md` is a pointer to `CLAUDE.md`. The kiln repo and all three golden repos currently open `README.md` and `CLAUDE.md` with the same sentence and repeat the same status pointers — two copies with nothing to detect when one goes stale, which is §2.3's own rule applied to prose. Rejected: dropping `CLAUDE.md` to a pure symlink-like stub (the kiln and agent blocks have to live somewhere a tool can fence), and keeping agent-specific guidance in `CLAUDE.md` (in practice every line of it was developer-facing). | **Confirmed** |
| **D58** | **agentkit leaves the plan; kiln seeds the instruction files itself.** Apply step 6 — the `agentkit project init/update` subprocess — is deleted, and kiln seeds `README.md`, `CLAUDE.md` and `AGENTS.md` bodies while owning its block in the latter two. `.claude/**`, `.codex/**` and machine-level agent config become unowned until an agent-config tool is re-ideated from scratch; the fenced-block model (D27) is what makes re-entry cheap, since a future tool adds its own fence to files kiln already seeds. taskkit's retirement record and agentkit's prior art, outstanding questions and harvest move to `docs/plans/agent-config-future.md`. Revises D15. Rejected: keeping the seam as a documented no-op (the plan would keep describing a consumer that will not exist for v1). | **Confirmed** |
| **D59** | **The tool lifecycle surface is built, in `rn-forge-tooling`, behind a defaulted `ToolProduct` adapter** (§2.9). `python-app` and `python-tool` differ today by a package name and one dependency line, and `install/` holds only `archive.py` — so D53's split has no evidence. Tooling owns `$RNF_HOME`, the versioned install tree and the `install`/`upgrade`/`uninstall`/`cleanup`/`status`/`doctor` algorithms; a product supplies `artifacts()`, `checks()` and `migrate()`, all defaulted, which is the same seam kiln's own modules use. The verbs are mounted by `CliApp.from_config` from a `[cli.lifecycle]` config table, so shared CLI design's zero-hand-written-construction property holds. Scheduled as Phase C.3, before any template derives from a golden repo. | **Confirmed** |
| **D60** | **`pyproject.toml` stays repo-owned and is verified, not generated.** Every archetype's `[tool.ruff*]`, `[tool.pyright]`, `[tool.pytest.ini_options]` and `[dependency-groups]` tables are near-identical, but **no import mechanism exists**: pytest and coverage have none, pyright's `extends` is not available in the `[tool.pyright]` form, and ruff's `extend` takes a filesystem path that would have to reach inside `.venv`. So the bytes are duplicated on disk whether kiln writes them or a human does — generating them buys propagation and drift detection, not deduplication, and costs a config round trip every time someone adds a dev dependency. Doctor check 8a compares the tables against the archetype's expected values and warns, which is the propagation signal without the friction; it is also verification packaging proposal's own line, that verification and generation are different powers. Revisit if a repo's tool config is found to have silently diverged — that is F2 in config rather than code. | **Confirmed** |
| **D61** | **The tool lifecycle surface is a capability flag, not an archetype.** `lifecycle = true` may be set by any Python archetype; it adds a dependency and mounts `[cli.lifecycle]` verbs at runtime through `declare()`, changing neither the file topology nor the task graph — which is D54's own admission test, already passed by `framework` and `frontend`. `python-tool` survives as a **CLI alias** that expands to `python-app` + `lifecycle = true`, normalized in `state.json`, so the catalogue keeps seven names for humans and carries six shapes internally; `golden/python-tool` is unchanged on disk and becomes the golden repo for the flag value, satisfying D54's every-shipped-value rule at no fixture cost. This is what lets kiln self-host as `python-lib` while still shipping `install`/`upgrade`/`doctor` (verification packaging proposal), and it generalizes: any `python-lib` that ships a command — pykit, if it ever does — takes the same flag. Rejected: **letting `python-lib` alone opt in** (leaves `python-app` and `python-tool` differing by a flag both could carry, which is the smell D59 raised, and leaves D53 unproven rather than resolved); **making kiln a special case** with hand-written lifecycle wiring (kiln self-hosting on a special case is the one exception the plan can least afford); and **dissolving the question by moving `rn-forge-kiln-checks` out of the kiln repo** so kiln ships one distribution again — that answers *kiln today* and leaves the underlying question to resurface at the first `python-lib` that ships a command. Resolves open question 11. Refines D53 and D54. | **Confirmed** |
| **D62** | **Config knobs are tiered, and each tier has a stated golden-repo price** (§0.10). Tier 1 *values* substitute into files that exist either way and cost nothing; Tier 2 *toggles* include or remove a known fragment and cost one golden fragment; Tier 3 *topology* changes which files exist and costs a golden repo or matrix cell; Tier 4 *policy* — naming rules, package-prefix enforcement — is **not built**, because kiln would become a configurable static-analysis framework as a side effect of being a scaffolder. kiln instead **generates ruff and import-linter configuration from declarative config and never implements a matcher**. Amends D54, whose "neither topology nor task graph" rule is the Tier 1/2 versus Tier 3 line stated as a binary; making it a priced tier is what lets the catalogue absorb org-level configurability without the combinatorial explosion D47 avoided. Tier 1 identity in `pyproject.toml` extends doctor check 8a and does not reopen D60, whose argument was about tool-config tables with no inheritance mechanism, not about metadata. | **Confirmed** |
| **D63** | **Jinja templates are the authored source; golden repos become committed rendered snapshots, and a matrix harness validates every shipped combination.** Hand-authoring a golden per archetype × flag combination is real overhead, and this is what D43 got backwards — but a golden supplies two properties, and only *runnable* is replaceable by a harness. *Reviewable as committed bytes* is what makes "a template change not first made in the golden is a bug" detectable, because the byte impact of a template edit appears in a pull-request diff; a tree that exists only in a temp directory cannot be code-reviewed and cannot diff across time. So: **(1)** templates are authored in `archetypes/**`; **(2)** a representative set of rendered trees stays committed under `tests/fixtures/golden/`, regenerated by a command rather than hand-edited, exactly as snapshot fixtures are; **(3)** a matrix harness renders every shipped archetype × flag combination into a temp directory and runs `uv sync && task validate`, `actionlint` and `mkdocs --strict` in it. Revises D43: goldens remain the review artifact and stop being the authorship artifact. Cost: the harness is slow (a `uv sync` per cell), which is what open question 12 prices. | **Revised by D69** — part (1) and (3) stand; part (2) is dropped: no rendered tree is committed |
| **D64** | **Layered external config is resolved once and committed; rendering is a pure function of the checkout.** The layer order is kiln defaults → org → project → repo, deep-merged, with the source given by `--config-path` (a local path or a pinned remote) rather than by implicit machine-local discovery. **Resolution happens at `kiln new` and `kiln config sync`, never at `kiln apply`**, and the resolved values plus the source reference are committed to the repo. Without this, home-level config makes `kiln apply` produce different bytes on different machines, `check_generated` fails for whoever did not render last, and the committed `state.json` baseline that configuration design rests on becomes machine-dependent — a failure that presents as CI going red on a clean checkout with no diff to explain it. A remote source **must be pinned to a tag or SHA**, never a branch, which is D45's apollo `branch = "main"` lesson applied to configuration. `kiln doctor` re-reads the source and reports drift from the current org profile — the propagation signal without the reproducibility cost, which is the shape D60 chose for `pyproject.toml`. Per-key provenance is recorded in state so doctor can say *which layer* supplied a value. | **Revised by D70** — resolve-once-and-commit stands; a git source may name a branch (the resolved commit is recorded), `kiln doctor` does not fetch the source, and re-resolution is `kiln config update`/`upgrade` rather than `kiln config sync` |
| **D65** | **The CI concern is named `cicd`, not `devops`, and this upholds verification packaging proposal rather than reversing it.** verification packaging proposal rejected `devops` because it "names a domain that excludes nothing"; `cicd` names pipelines and workflows and **does** exclude infra provisioning, observability and deployment topology, all out of scope per §0.5. The ADR's naming rule stands unamended and no reversal is recorded. | **Confirmed** |
| **D66** | **`cicd` generates committed workflows plus local composite actions; it is a generate-time dependency, never a CI-runtime one.** GitHub Actions cannot `include:` a YAML file from `.venv` or `.rn-forge/` — its only reuse mechanisms are reusable workflows fetched from a git repo and composite actions, and ADO's `extends`/`template:` is likewise a git resource. So thin wrappers importing templates from inside a Python package is not implementable, and its nearest implementable form is the reusable-workflow devops repo **D45 already rejected** (CI stops being self-contained; private-repo fetch needs auth; the ref is churn-y when pinned and unpinned when not). Local composite actions under `.github/actions/` — which `golden/python-tool` already carries — give the same thinness with reuse resolved at generation time on the developer's machine. configuration design holds: CI never renders. `cicd` writes `.rn-forge/cicd/state.json` in the **same schema** as kiln's, and the one `check_generated.py` runs over both baselines rather than being forked. | **Confirmed** |
| **D67** | **docs, tasks and cicd are modules inside the kiln distribution, not separate libraries or distributions.** A separate distribution is warranted only when something installs it *without* the others: `rn-forge-kiln-checks` has a proven case (CI installs it and must not install kiln, verification packaging proposal) and `cicd` a plausible one (open question 14); docs and tasks have none, and four independently versioned distributions that must agree on one config schema is a release matrix paid on every schema change for no gained independence. Boundaries are enforced by `.importlinter` contracts per module, which is already what CI policy does for `rn_forge.kiln.checks` — a contract does not require a distribution. Escape hatch, per D36's rule: promote a module to a distribution when a non-kiln consumer appears. Rejected: unpublished workspace packages under `libs/` (they buy enforceable boundaries that import-linter already supplies, at the cost of N more `pyproject.toml` files). | **Confirmed**; its open asymmetry is closed by D71 — `cicd` is not published |
| **D68** | **The `Generator` protocol is promoted from an internal seam to kiln's module contract, and `kiln doctor` orchestrates it.** `artifacts()` + `checks()` — the seam §2.9 records kiln's own modules as already using, and structurally the same as `ToolProduct` (D59), which is worth collapsing into one protocol with two registries rather than maintaining two similar ones. Each module registers, `kiln doctor` collects commons `Finding` rows across all of them and prints one unified report, and a module's own doctor (`cicd doctor`) is the same rows reached by a different entry point. This is what makes the concern split structural rather than cosmetic. | **Confirmed**; extended by D72 |
| **D69** | **No rendered golden is committed.** Rendered output is regenerable and does not belong in git. `task self:golden:render` renders every shipped archetype × flag combination into gitignored `.goldens/<ref>/`; `task self:golden:validate` runs each cell's gate; the **owner reviews and approves the rendered output**, optionally with a parallel review agent. The hand-authored goldens are the bootstrap reference for writing templates and are deleted from git once the rendered cells reproduce them. kiln's CI renders every cell per pull request; the per-cell `uv sync && task validate` is local and on demand. Trade-off accepted knowingly: D63's "reviewable as committed bytes" becomes "reviewable as rendered output on request", and a change's byte impact is seen by rendering two refs and diffing them. Revises D63; retires the byte-exact golden snapshot tests. Closes open question 12. | **Confirmed** |
| **D70** | **Config sources are a local path or a git URL; deep merge replaces lists; the merged config is committed and is the only input after `kiln new`.** `kiln new --config` resolves kiln defaults → source layers → flags and writes `.rn-forge/kiln/config.toml` with a `[source]` table. `apply`/`doctor`/`diff` read only that file. `kiln config update` re-resolves from the recorded source under the current kiln; `kiln upgrade` (kiln's own lifecycle verb) warns or errors when the committed config no longer matches the new schema; `kiln config upgrade` re-resolves and migrates under the new kiln. Both config commands report the resulting artifact changes and run `kiln apply` only with `--apply`. The config manager validates against the running kiln's schema on every load, and repo overrides — keys whose committed value differs from what their layer last supplied, known from per-key provenance — survive re-resolution. Rejected: a published config package (a release per org-profile edit, for no property a pinned commit lacks) and list append (removing an inherited entry then needs a second syntax). Revises D64. Closes open question 13. | **Confirmed** |
| **D71** | **No internal kiln module is published.** `docs`, `tasks`, `cicd` and the rest are usable only through a kiln-generated repo, so they carry no public API, no separate version and no compatibility promise. `rn-forge-kiln-checks` is not an internal module in this sense — generated repos' CI installs it and must not install kiln (verification packaging proposal) — and stays a distribution. Closes open question 14 and D67's asymmetry. | **Confirmed** |
| **D72** | **Each module declares the config it supports, and kiln composes.** A `KilnModule` owns its config section (a strict pydantic model whose defaults are kiln's layer), its `kiln new` options, its `artifacts()` and its `checks()`; kiln owns only composition — the root schema, the union of options (a collision is a startup error), and module iteration for `apply` and `doctor`. `archetype.toml` lists the enabled modules alongside the dependency set, and a section for a disabled module is rejected. Extends D68's protocol with the config and options halves. Closes open question 15. | **Confirmed** |
| **D73** | **pykit is consumed from its `feature/upgrade` branch or a local path until the owner declares it stable; no release gates kiln.** C.2 step 9's premise — templates must not render a branch pin — is kept by making the rn-forge dependency source a Tier 1 config value (D62) that every template renders, rather than by waiting for tags: `git` + ref (the default, CI-capable) or `path` (a `[tool.uv.sources]` path entry, local only). Flipping to tags later is `kiln config upgrade --apply` per repo, not a template change. Guards: `check-rn-forge-deps` accepts a branch or path source with a warning and refuses one in a publish job; goldens and generated repos that run CI use `git`, never `path`. Suspends, does not reverse, D46 — a tag is still the release contract once releases exist. | **Confirmed** |
| **D74** | **`rn-forge-kiln-checks` is the render-free half of each module's checks, organized by module, and a `core` module owns what every module shares.** The owner asked whether module doctors make the package redundant. They share code, not packaging: a check that needs only committed files (`state.json` hashes, the task graph, workflow entrypoints, the dependency set) runs in CI; a check that needs a fresh render (`artifact.stale`, `block.stale`) cannot, because CI never renders (CI policy). So each module's `checks()` = its functions in `rn_forge.kiln.checks.<module>` + its render-dependent checks, one implementation of each rule, reachable from `kiln doctor` locally and from console scripts in CI. `core` holds the umbrella, config manager, state baseline, `standard.md`, the gitignore block and `check-generated`; `scaffold` becomes `python` (uv init, `.importlinter`, pyproject 8a, rn-forge deps), naming the language rather than the moment. Rejected: **running the module doctors in CI by installing kiln as a dev dependency** — it puts Jinja, the generation engine, pydantic and every template set into every repo's lock and CI environment, makes a kiln upgrade a dependency bump in every repo whether or not an artifact changed, and reopens CI policy/verification packaging proposal for no check CI can run that the split cannot. Refines D51 and D72. | **Proposed** — recommended; Phase D.1 is written against it. Confirm or override before D.1 starts |

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

**Answered by the owner, revision 11 (D61):** 11. ~~Is the lifecycle surface
orthogonal to the archetype?~~ Yes — `lifecycle` is a capability flag any Python
archetype may set, and `python-tool` becomes a CLI alias for `python-app` +
`lifecycle = true`. D53's seven names survive as names; D54's rule is what
decided it. kiln self-hosts as `python-lib` with the flag.

**Before Phase F:** 6. `ngkit` (Nx + Angular library monorepo): a fourth
archetype `ng-lib`, or hand-managed? 7. ~~Does the rebuilt agentkit keep its
version line?~~ — moot; agentkit is out of the plan (D58).

**Answered by the owner, revision 13 (§0.11):** 12 → D69 (no rendered tree is
committed; a gitignored render matrix, owner-approved). 13 → D70 (path or git
URL; lists replace; merged config committed; `kiln config update`/`upgrade`). 14
→ D71 (no internal module is published). 15 → D72 (modules declare their config;
`archetype.toml` lists modules). The original wording is kept below.

**Formerly open — the §0.10 thread (revision 12):** 12. Under D63, **which
rendered trees stay committed, and when does the matrix run?** All m×n is too
large to commit; none loses the review property. Proposal: the six current
goldens stay committed as snapshots and run per-PR, the full matrix runs nightly
or on demand. Needs a call on CI time budget. 13. D64's **config source format
and merge semantics** — is a remote source a pinned git URL or a published
package, and do **lists** replace or append when layers deep merge? Scalars and
tables are unambiguous; lists are not, and leaving it unspecified makes merge
behaviour unpredictable. Recommendation: lists replace. 14. Is `cicd` eventually
**published** as its own distribution (D67's one open asymmetry), and does that
happen when ADO lands or only when a non-kiln consumer appears? 15. **How does
an archetype declare its enabled modules?** The owner's framing is that the
archetype names both the dependency set and the kiln modules initialized in the
repo; that is an undrafted change to the §2.5.2 config schema.

**Before Phase D.1 (revision 14):** confirm **D74** — checks stay a
CI-installable package organized by module, rather than CI installing kiln and
running module doctors.

**Before Phase E (revision 14):** 16. **intellibuild's archetype.** D41 and
Phase F say `python-web-app` (`fastapi + angular`); pykit's
`fastapi-library-plan.md` says `python-web-api`. The two differ by whether the
repo carries a separately built frontend package (D53). Decide before Phase E
picks its first shipped cell.

**Parked:** 8. ADO provider (D4). 9. ~~An `agentkit docs …` command~~ — see
[agent-config-future.md](agent-config-future.md). 10. apollo's return (D40).

______________________________________________________________________

## 7. Revision history

**Revision 14** — implementation-ready. §0.1 rewritten as a phase board with
verified on-disk state (goldens behind pykit Part E, `golden-lib` on a pre-split
commons tag, agentkit still in the reference, `rn-forge-web` absent from it);
§0.2 gains web and fastapi; §3 rewritten from Phase C.3 on — C.3 (pykit
lifecycle), new C.4 (kiln realignment), D split into D.1–D.8 against D69–D74, E
gated on `rn-forge-fastapi`, pykit releases moved to a triggered item under G.
D73 (branch/path pins until stable), D74 (checks by module, `core` module;
proposed). Open question 16 raised.

**Revision 13** — the §0.10 thread closed (§0.11) from the owner's answers: no
committed rendered goldens, a gitignored render matrix and owner approval (D69);
path-or-git config sources, list replacement, committed merged config and
`kiln config update`/`upgrade` (D70); no internal module published (D71);
modules declare their own config and options (D72). Open questions 12–15
answered; the next implementation steps are sequenced, and two stale status
claims in §0.1 (C.3 progress, goldens on `CliApp.from_config`) are flagged.

**Revision 12** — the scope-expansion thread (§0.10): the tier model amending
D54 (D62), Jinja templates as the authored source with goldens as committed
snapshots plus a matrix harness (D63, revising D43), resolved-and-committed
layered config (D64), `cicd` naming and its generate-time model (D65, D66),
concerns as modules rather than distributions (D67), and the promoted
`Generator` protocol (D68). **Unfinished — open questions 12–15 gate any
template or golden work.**

**Revision 11** — open question 11 answered: the lifecycle surface is a
capability flag and `python-tool` is an alias for `python-app` + `lifecycle`
(D61); the kiln repo is cleared to publish further distributions.

**Revision 10** — after the owner's Phase C.2 review (§0.9). README becomes the
single prose home and the instruction files become pointers plus blocks (D57).
agentkit leaves the plan and kiln seeds the instruction files itself, deleting
apply step 6 (D58); the agent-config material moves to
`docs/plans/agent-config-future.md`. The tool lifecycle surface is built behind
a defaulted `ToolProduct` adapter, as new Phase C.3, because `python-app` and
`python-tool` were otherwise the same repo (D59). `pyproject.toml` stays
repo-owned and is verified rather than generated (D60). verification packaging
proposal gets a schedule: `scripts/**` leaves the ownership table, the template
inventory, the apply sequence and the golden repos, and `rn-forge-kiln-checks`
becomes Phase D step 1.

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
`docs/reference/standard-repo.md` (D48); shared CLI design proposed for the
tooling boilerplate target (D49). Eight defects from the codex review fixed in
the golden repos — see §0.6.

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
