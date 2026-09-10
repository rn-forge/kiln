# Harvest inventory

What was carried into the golden repos from the donor repos, what was
deliberately dropped, and where each thing landed. This is the review artifact
for "everything common and worth carrying over" — the counterpart to
[ADR-0006](../adr/0006-runbooks-not-skills.md)'s rule that repos are rebuilt
rather than migrated. Behaviour is harvested; files are not.

Donor paths are relative to their repo root. Target paths are relative to a
golden repo, and therefore to every generated repo.

## Task layout and the vocabulary

| Donor | Behaviour kept | Behaviour dropped | Target |
| -- | -- | -- | -- |
| `agentkit/Taskfile.yml` | the wrapper-only root, the `includes` set, `UV_CACHE_DIR` in-repo, the ten verbs | `lint:markdown` and the `format:markdown` wrapper — mdformat is repository-owned (agentkit ADR-0014) | `Taskfile.yml` |
| `agentkit/tasks/workspace.yml` | `install`, `version`, `build`, `clean`; the separate packaging cache dir and its rationale | `scripts/check_dist_contents.py` as a build step — a repo-specific lint, wired through `[tasks.extra_refs]` instead | `tasks/workspace.yml` |
| `agentkit/tasks/quality.yml` | every `internal: true` primitive; `lint:docs-structure` and `lint:docs-nav` delegating to `:docs:*` | `lint:markdown`, `format:markdown`, the docformatter step in `format:python` | `tasks/quality.yml` |
| `agentkit/tasks/docs.yml` | `build`, `serve`, `nav`, `structure`; `MKDOCS_SITE_DIR` with a `CLI_ARGS` override so CI can target a temp dir | serve port 8083 (arbitrary; now 8080) | `tasks/docs.yml` |
| `apollo/docs/guides/task-vocabulary.md` | the idea of a written vocabulary, as input to [ADR-0007](../adr/0007-task-vocabulary.md) | the generated prose page itself, and apollo's verbs (`format-check`, `dev`, `docs`) | ADR-0007; the rendered `.rn-forge/kiln/standard.md` |
| `taskkit` `extra_refs` / repository-owned include model | both mechanisms, as `[tasks.extra_refs]` and `[tasks.includes]` with `ownership = "repository"` | discovery, planner, adapters, the install layer (F16) | `.rn-forge/kiln/config.toml` schema |

## Checkers

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
| `agentkit/pyproject.toml` dependencies | nothing | the direct `jinja2`/`pydantic`/`rich`/`ruamel-yaml`/`tomlkit`/`typer` dependencies — a `python-cli` repo takes that surface from `rn-forge-tooling` (F12) | `.importlinter` `frameworks-come-from-rn-forge`; [ADR-0005](../adr/0005-archetypes.md) |

## Docs toolchain

| Donor | Behaviour kept | Behaviour dropped | Target |
| -- | -- | -- | -- |
| `agentkit/scripts/docs/setup/_common.py` | the `Area`/`Finding` dataclasses, the pyyaml-optional fallback loader, the MkDocs-compatible slugifier | `ALL_AREA_KEYS` / `CORE_AREA_KEYS` — a fixed area whitelist contradicts a seeded `_areas.yml` (D44); `ChangeLog`, `resolve_asset_path`, `templates_dir`, `default_areas_source`, `dump_yaml` — all skill-installer machinery with no customer once no skill installs anything | `scripts/docs/_common.py` |
| `agentkit/scripts/docs/setup/check_structure.py` | area scaffolding, ADR numbering and status, release and epic/feature naming, link and anchor resolution, the `_*.md` reference rule, the instruction-pointer rule | the specs-board status cross-check (couples an index table's prose to file state; belongs to whoever owns the board, not to the repo standard); `--selftest` and its fixture directory | `scripts/docs/check_structure.py` |
| `agentkit/scripts/docs/site/check_docs.py` | broken links, broken anchors, orphan pages, nav targets, gitignored-generated-subtree detection | module-level `ROOT`/`DOCS_DIR` globals — the checker now takes a repo root, so it can be run against a fixture | `scripts/docs/check_docs.py` |
| `agentkit/scripts/docs/site/gen_nav.py` | the marker-fenced nav block, `--check`, index-link ordering, the acronym title map | its private 30-line `_areas.yml` parser — a third YAML loader in the same script set | `scripts/docs/gen_nav.py` |
| `intellibench/tools/docs/{check,_nav,generate_order,check_mermaid}.py` | nothing they did not share with agentkit's versions (F3: four forks of one link checker) | all four implementations | superseded |
| `agentkit/docs/_areas.yml`, `_structure.md` | both, verbatim in shape: seven areas, nav modes, the "where new material goes" routing rule | their status as generated-and-owned — they are now seeded, so a repo can add an area (D44) | `docs/_areas.yml`, `docs/_structure.md` |
| `agentkit` E17 docs area model | the model itself | agentkit's ownership of it — it moves to kiln's `docs` module | [ADR-0005](../adr/0005-archetypes.md) |
| `apollo` ADR-0024 | `.docs-site/` as the rendered-output directory, and the `MKDOCS_SITE_DIR` override | `.apollo/site/` and everything about apollo's app-state root | `tasks/docs.yml`, `.gitignore` |

## CI

| Donor | Behaviour kept | Behaviour dropped | Target |
| -- | -- | -- | -- |
| `agentkit/.github/workflows/ci.yml` | the job shape `validate → sonar → check-version → build → publish`; the tag-exists release check; `repo-token` on setup-task; the strict docs build inside validate | the unpinned `actions/*@v4` uses; the missing per-job `permissions:`; the missing `concurrency:`; the four separate lint/typecheck/test steps, now one `task validate` | `.github/workflows/ci.yml` |
| `agentkit/.github/workflows/docs.yml` | the Pages build/deploy split, the temp-dir site build, the "enable Pages by hand" note | the top-level `pages: write` / `id-token: write` grant — those move to the deploy job, which is the only one that needs them | `.github/workflows/docs.yml` |
| `pykit/.github/workflows/_package-ci.yml` | the per-package matrix and the `<package>-v<version>` tag shape | the `workflow_call` indirection and the direct `uv run` steps (every step now goes through `task`) | `golden/python-lib/.github/workflows/ci.yml` |
| `agentkit/sonar-project.properties` | the key/organization shape, the coverage report path, the idea of excluding template assets | the assets-specific exclusion | `sonar-project.properties`, excluding `scripts/**` |

## Instruction files and hygiene

| Donor | Behaviour kept | Behaviour dropped | Target |
| -- | -- | -- | -- |
| `agentkit` ADR-0011, ADR-0012 (instructions single-sourced, seeded) | both: one body, seeded once, and `CLAUDE.md` == `AGENTS.md` | — | `CLAUDE.md` / `AGENTS.md` body, agentkit-owned |
| `agentkit` ADR-0018 (structure rules live in the repo) | the rule, generalized: the repo's own `_areas.yml` is what the checkers read | — | [ADR-0001](../adr/0001-ownership.md), D44 |
| `agentkit` ADR-0021 (install only what CI runs) | promoted to [ADR-0003](../adr/0003-ci-runs-committed-code.md) and strengthened: committed, hashed, and checked | — | [ADR-0003](../adr/0003-ci-runs-committed-code.md) |
| `agentkit/feedback.md`, `apollo/epic-design-docs-handoff.md`, `intellibench/{ADR_REVIEW.md,temp.txt}` | nothing | all of it — tracked session residue (F10) | not carried; `hygiene.stray-root-file` |
| `agentkit` setup skills (`go-task-setup`, `docs-setup`, `mkdocs-site-setup`, `spec-structure-setup`) | their *outputs*, which are now templates | the skills themselves, and the fact that a skill installed a file CI runs (F8) | [ADR-0006](../adr/0006-runbooks-not-skills.md) |
| `agentkit` generic skills (`gh-fix`, `python-simplify`, `sonar-cleanup`) | all three, unchanged in scope | — | agentkit, rebuilt (out of scope here) |
| `agentkit/.editorconfig` | the file | `trim_trailing_whitespace = false` and `insert_final_newline = false` globally — both now on, with the Markdown exception where trailing spaces are a hard line break | `.editorconfig` |

## The rule that had no mechanism

§2.1 of the plan says commons and tooling are the only permitted rn-forge peer
imports, "enforced by import-linter". It is not, and cannot be: import-linter
rejects subpackages of external packages, so `rn_forge.kiln` is not a legal
forbidden module — verified empirically, both with `rn_forge` installed and
without. [ADR-0005](../adr/0005-archetypes.md) moves that rule to
`scripts/standards/check_rn_forge_deps.py`, where it is decidable, and gives
`.importlinter` the complementary rule it *can* enforce: no direct import of a
framework or CLI toolkit that an rn-forge library already owns.

## Not harvested at all

- `agentkit/core/**` and `taskkit/core/**` — replaced by `rn-forge-tooling`
  (F12, [ADR-0002](../adr/0002-the-dependency-graphs.md)).
- `taskkit`'s discovery, planner, adapters and install layer — 1,950 of 5,248
  lines, dead weight once the archetype is asserted (F16).
- `intellibench/docs/` — superseded by its own `docs2/`, which becomes
  intellibuild's `docs/`.
- Every scaffold-output template: `uv init`, `pnpm create` and `nx g` are
  shelled out to and their output reconciled
  ([ADR-0005](../adr/0005-archetypes.md)).
