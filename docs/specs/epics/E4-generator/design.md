# E4 design — the generator

Design shared across [E4](index.md)'s features. The config schema itself is
normative and lives in
[the reference, §9](../../../reference/standard-repo.md#9-configuration); the
decisions are ADR-0005 to ADR-0003.

## Package layout

```
rn-forge/kiln/
  docs/                    # the canon: adr/, reference/standard-repo.md, architecture/, runbooks/, specs/
  src/rn_forge/kiln/       # the one distribution, rn-forge-kiln (ADR-0010)
    main.py cli.toml       # CliApp.from_config over the packaged declaration (ADR-0009); never a hand-built app
    commands.py            # one function per command; F4.5 adds them
    config.py              # KilnConfig: the validated config, typed reads
    checks.py              # the render-free check registry `kiln doctor` runs
    archetypes/            # one archetype.toml per archetype: modules, dependency set, forbidden tools, gate, untested values
      python_app/  python_tool/  python_lib/  python_web_api/  python_web_app/
    modules/               # each a KilnModule — config model, options, artifacts, checks/ (render-free), templates/, scaffold
      base.py registry.py  # KilnModule protocol + registry
      core/                # umbrella, config manager, state, cycle adapter, .gitignore block, .editorconfig
      python/              # uv init + reconcile, the frontend scaffold, .importlinter, check 8a, rn-forge dependency set
      docs/                # docs tree, _areas.yml, _structure.md, mkdocs.yml body (scaffold) + nav block
      tasks/               # Taskfile.yml + tasks/*.yml
      cicd/                # workflows, .github/actions/setup, sonar-project.properties, pins.toml
      instructions/        # README/CLAUDE/AGENTS bodies (scaffold), the kiln block in CLAUDE.md, standard.md
    doctor/                # F4.6: the report across modules, taskgraph.py (ported from taskkit), --all
  tests/
    fixtures/golden/       # hand-authored bootstrap references; deleted by F4.4
      python-app/  python-tool/  python-lib/
    fixtures/scaffold/     # captured scaffolder output, the reconcile's test input (S5.2.2)
```

Every module exposes the same two functions:
`artifacts(config, root) -> list[Artifact]` and
`checks(config, root) -> list[Finding]`. That is the whole internal contract,
and it is what keeps kiln from becoming a god-kit: a module is a template set
plus a doctor check, nothing more.

## The module contract

```python
class KilnModule(Protocol):
    name: str                                         # "docs", as archetype.toml lists it
    section: str | None                               # the config table it owns: [docs]; cicd owns [ci]
    config_model: type[StrictModel] | None            # commons[pydantic], strict; defaults are kiln's layer
    def options(self) -> Sequence[Option]: ...        # the `kiln new` flags this module adds
    def artifacts(self, config: KilnConfig, root: Path) -> Sequence[Artifact]: ...
    def checks(self, config: KilnConfig, root: Path) -> Sequence[Finding]: ...
```

kiln owns only the composition: the root schema is `schema_version` + `[source]`
\+ `[repository]` + rn-forge-cli's `[cli]`, carried as written, + one section per
enabled module; the `kiln new` command line is the union of every enabled
module's options, with a collision a startup error; `apply` and `doctor` iterate
modules in `archetype.toml` order. `archetype.toml` gains
`modules = ["core", "python", "docs", "tasks", "cicd", "instructions"]`
alongside its dependency set, and a disabled module's section is rejected rather
than ignored. This is the `Generator` protocol with the config and options
halves added — still `artifacts()` + `checks()` at its core
([ADR-0011](../../../adr/ADR-0011.md)).

## Commands

| Command | Behaviour |
| -- | -- |
| `kiln new <dir> --archetype A [--docs P] [--backend F] [--frontend W] [--config <path\|git-url[@ref]>] [--dry-run] [--yes] [--json]` | collect config in memory for a new repo; preview and write nothing unless `--yes`, which writes `config.toml` and runs scaffold + apply. Refuses a non-empty `<dir>`. |
| `kiln apply [--dry-run] [--json] [--force <artifact>]…` | the full sequence (below); idempotent and non-interactive; re-run after editing `config.toml` or upgrading kiln; each forced path must name a reported conflict, drift, or missing managed artifact |
| `kiln doctor [PATH] [--only <name>] [--full] [--json] [--all <path>…]` | by default, the render-free checks over committed files — what `task validate` runs in CI; `--full` opts in to every check below, including a fresh render and diff; exit 1 on any error-severity finding |
| `kiln docs-nav [PATH]` | regenerate `mkdocs.yml`'s nav block; `kiln doctor --only docs-nav` is its check |
| `kiln diff [<artifact>]` | unified diff of on-disk vs fresh render |
| `kiln config update` / `kiln config upgrade` | see the config lifecycle |
| `kiln version`, and the lifecycle verbs via `[cli.lifecycle]` | — |
| `kiln prompt [<name>]` | print a one-time procedure shipped with kiln, or list them; reads and writes nothing ([ADR-0006](../../../adr/ADR-0006.md)) |

There is no `adopt` ([ADR-0006](../../../adr/ADR-0006.md)). A repo either was
created by `kiln new` or is not a kiln repo. **Flag parity is non-negotiable**
(D8, D14). `config.toml` is the interactive flow's only durable hand-authored
input; preview writes nothing, `--yes` executes the plan, `apply` is
non-interactive and idempotent, and every prompt has a flag; `--yes` accepts
defaults. Agents are the main callers. CI reaches this CLI only through
committed `task` entrypoints — `kiln doctor` always, `kiln doctor --full` where
the workflow sets `KILN_DOCTOR_FULL` — and never runs `apply`
([ADR-0010](../../../adr/ADR-0010.md)).

## The config lifecycle

([ADR-0004](../../../adr/ADR-0004.md))

| Command | Reads | Writes | Then |
| -- | -- | -- | -- |
| `kiln new <dir> --config <path\|git-url[@ref]> …` | kiln defaults → each source layer → flags | merged `.rn-forge/kiln/config.toml`, with a `[source]` table (location, ref, resolved commit) | scaffold + apply, as today |
| `kiln apply`, `kiln doctor`, `kiln diff` | **only** the committed `config.toml` | — | — |
| `kiln config update [--dry-run] [--apply]` | the recorded source, with the **current** kiln's defaults | re-merged `config.toml` | prints the artifacts that would change; `--apply` runs `kiln apply` |
| `kiln upgrade` | — | in a repo, the `rn-forge-kiln` pin and `uv.lock`, then `uv sync`; outside one, the installed tool (the lifecycle verb) | the **new** kiln loads the committed config against its schema: **warns** when it loads but a newer schema exists, **errors** when it no longer validates, and names `kiln config upgrade` either way |
| `kiln config upgrade [--dry-run] [--apply]` | the recorded source, with the **new** kiln's defaults and schema | migrated and re-merged `config.toml` | as `update` |

Three rules make that table safe:

1. **The config manager validates against the running kiln's schema on every
   load**, not only on `upgrade`. A config written by a newer kiln is refused
   with the version it needs.
1. **Local edits survive re-resolution.** `state.json` records per-key
   provenance. A key whose committed value differs from what its layer last
   supplied is a repo override; `update` and `upgrade` keep it and list it,
   rather than silently overwriting it.
1. **Lists replace.** A layer that sets a list owns the whole list.

## Artifact kinds and the cycle

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

Approved writes are staged under `.rn-forge/kiln/rendered/`, the state write
holds `.rn-forge/kiln/state.lock`, backups go to
`.rn-forge/kiln/backups/<UTC timestamp>/<repo-relative path>`, and atomic
replacements begin only after every render and check succeeds. On a write or
post-apply check failure, kiln restores backups and removes newly created
artifacts. The committed `state.json` is excluded from artifact enumeration and
written last; a failed transaction restores its previous bytes. State uses
tooling `StateStore` with commons-owned JSON value types and hashing; metadata
is `kiln_version: str`, `config_hash: str` and `config_provenance` — per-key
provenance, each dotted path's layer and the value it supplied. Managed entries
store `path`, `kind`, and `content_hash`; block entries also store their exact
begin and end markers; seeded entries store presence but no content hash.

## Apply sequence

```
1. core         .rn-forge/kiln/, gitignore block, .editorconfig
2. python       (new only) uv init / pnpm create / nx g, then reconcile to archetype; .importlinter
3. docs         (new only) the mkdocs.yml body; tree, _areas.yml, _structure.md, mkdocs.yml block
4. tasks        Taskfile.yml, tasks/*.yml
5. cicd         workflows, sonar-project.properties
6. instructions (new only) README.md / CLAUDE.md / AGENTS.md bodies; the kiln block in
                CLAUDE.md, .rn-forge/kiln/standard.md
7. doctor       run every check; apply exits non-zero if any error remains
```

No apply step shells out ([ADR-0001](../../../adr/ADR-0001.md)). `scripts/**` is
gone from steps 3 and 4 under ADR-0010: the checks ship in kiln, a pinned dev
dependency, not in generated files. **Scaffolding shells out.** `kiln new` runs
`uv init` and `create-nx-workspace`, then reconciles the result (move files, fix
pyproject sections); each module's `scaffold(root, config)` runs once, before
the first apply, in module order. It never templates another tool's scaffold
output (D16), and a body a scaffold writes (`mkdocs.yml`, `CLAUDE.md`) is never
also an artifact: the engine refuses a whole-file write and a block write to one
path.

## Doctor checks

Each is a stable `Finding.code`. The reference's §6 is the normative list; this
numbering is what [F4.6](F4.6-doctor.md) builds against.

| # | Code prefix | Check |
| -- | -- | -- |
| 1 | `config.*` | `config.toml` parses and validates |
| 2 | `artifact.missing` / `.drift` / `.stale` | every managed artifact present; disk hash == committed last-applied; last-applied == fresh render |
| 3 | `artifact.seed-missing` | every seeded artifact present |
| 4 | `block.missing` / `.stale` | every fenced block present and current |
| 5 | `taskgraph.*` | ported from taskkit `validator.py`: exact public surface, root file holds wrappers only, inner tasks are internal except `docs:*` (and `api:*`, `web:*` on the web archetypes), every task has `desc`, every include exists, every `task:` ref resolves, no cycles, no reserved-namespace collision |
| 6 | `taskgraph.unresolved-ref` | every `task <name>` in `.github/workflows/**`, `CLAUDE.md`, `AGENTS.md` resolves against `task --list-all` |
| 7 | `ci.entrypoint` | no forbidden tool, including `kiln`, invoked directly in any workflow (list from `archetype.toml`) |
| 8 | `gate.shrunk` | the set of tasks reachable from `validate` ⊇ the archetype's `required_validate` list; `kiln doctor` enforces the same list in CI, reading it from `config.toml` |
| 8a | `pyproject.tool-config` (warning) | the `[tool.ruff*]`, `[tool.pyright]`, `[tool.pytest.ini_options]` and `[dependency-groups]` tables — and `[project]` identity fields — match the archetype's expected values. **Verified, never written** ([ADR-0005](../../../adr/ADR-0005.md)) |
| 8b | `kiln.pin` | `rn-forge-kiln` is in the dev group with a pinned source, and the running kiln is the version `uv.lock` records ([ADR-0010](../../../adr/ADR-0010.md)) |
| 9 | `ci.unpinned` / `ci.permissions` | every `uses:` is SHA-pinned with a version comment; every job has `permissions:` |
| 10 | `docs.structure` / `.nav` / `.links` | tree matches the repo's `_areas.yml`; nav block current; no broken links/anchors/orphans |
| 11 | `hygiene.stray-root-file` (warning) | tracked root-level `*.md` not in the allow-list (`README.md`, `CLAUDE.md`, `AGENTS.md`, `LICENSE`, `CHANGELOG.md`) |
| 12 | `legacy.kiln-state` (error) | a pre-existing `.rn-forge/kiln/` or `$RNF_HOME/kiln/` tree without `schema_version` |

`kiln doctor --all <paths>` runs the same checks over many repos and prints one
table (F11). `docs.unclassified` is not a check: with no docs migration
([ADR-0006](../../../adr/ADR-0006.md)), `docs.structure` failing on an unknown
directory is the whole signal.

## Template inventory

✔ = generated for that archetype; d = only when `docs.profile = mkdocs`; s =
only when `ci.sonar`.

| Artifact | app | tool | lib | web |
| -- | -- | -- | -- | -- |
| `.editorconfig`, `.gitignore` block, instructions block, `.rn-forge/kiln/standard.md` | ✔ | ✔ | ✔ | ✔ |
| `Taskfile.yml` (10 root wrappers: `setup validate lint format typecheck test test:coverage build clean version`; public `docs:build docs:serve docs:nav docs:structure` only for `mkdocs`) | ✔ | ✔ | ✔ | ✔ |
| `tasks/workspace.yml` (`install`, `build`, `version`, `clean`) | ✔ | ✔ | ✔ | ✔ |
| `tasks/quality.yml` (internal `lint:python lint:generated lint:imports lint:task-layout lint:ci-entrypoint lint:docs* format:python typecheck:python test:python test:coverage`) | ✔ | ✔ | ✔ (per-package `uv run --package`) | ✔ (api side) |
| `tasks/api.yml` (public `api:dev`; `api:migrate` for django) |  |  |  | ✔ |
| `tasks/web.yml` (public `web:lint web:test web:build web:dev` via `pnpm nx …`) |  |  |  | ✔ (`-app` only) |
| `tasks/docs.yml` (`build serve nav structure`) | d | d | d | d |
| `.importlinter` contracts | ✔ | ✔ | ✔ | ✔ |
| `README.md`, `CLAUDE.md`, `AGENTS.md` bodies (written once by `kiln new`); the kiln block in `CLAUDE.md` | ✔ | ✔ | ✔ | ✔ |
| `docs/_areas.yml`, `docs/_structure.md`, `docs/adr/_structure.md`, seeded index pages, `mkdocs.yml` nav block | d | d | d | d |
| `.github/workflows/ci.yml` (validate → sonar → check-version → build → publish) | ✔ | ✔ | ✔ (matrix over `packages`) | ✔ (+ pnpm/node setup) |
| `.github/workflows/docs.yml` (Pages deploy on main) | d | d | d | d |
| `sonar-project.properties` | s | s | s | s |

**`scripts/**` is not in that table ([ADR-0010](../../../adr/ADR-0010.md)).**
The policy and docs checks ship in kiln as `kiln doctor`, a pinned dev
dependency, and `tasks/quality.yml` calls them rather than `python scripts/...`.
`pyproject.toml` is not in it either, for the opposite reason: it is repo-owned
and verified by doctor check 8a. A generated repo has no `scripts/` directory
unless it writes its own lints.

CI templates bake in the F5 fixes: SHA-pinned actions with version comments,
least-privilege `permissions:` per job, `concurrency:` per ref, tag-exists
release check (D22). The pin set lives in `modules/cicd/pins.toml`; Dependabot
watches kiln, not the generated workflows (D21).

## Steady state after release-1

CI runs `task validate`, which runs the pinned kiln's `kiln doctor`; pushes to
the default branch also run `kiln doctor --full`. Developers run
`kiln doctor --full`; `kiln doctor --all` is the cross-repo signal. A kiln
upgrade is `kiln upgrade` (the pin and the lock), `uv sync`, then
`kiln config upgrade --dry-run`, review, `--apply` — in a pull request whose CI
runs the new kiln.
