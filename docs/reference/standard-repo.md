# The standard repository

The normative statement of what an rn-forge repository is. The reasoning behind
each rule is in [the decision log](../adr/index.md); this page states the rules
and carries the specifications those decisions produced — the verb list, the
ownership table, the dependency sets, the config schema. It changes whenever an
archetype or an artifact does, which is exactly why it is not an ADR.

kiln renders this page, with the repo's archetype, docs profile and task surface
filled in, into every repo it generates as `.rn-forge/kiln/standard.md`. A repo
therefore always carries the standard it is held to, and an agent working in it
never has to find kiln to read the rules.

## 1. One entrypoint

`task` is the only entrypoint. Nobody — human, agent, or CI — invokes `uv`,
`pytest`, `ruff`, `pyright`, `mkdocs`, `pnpm`, `nx` or `kiln` directly.
`kiln doctor`'s `ci-entrypoint` check enforces that for every workflow file; the
forbidden list is the archetype's, read from `.rn-forge/kiln/config.toml`.

The public surface is ten root verbs:

```text
setup  validate  lint  format  typecheck  test  test:coverage  build  clean  version
```

plus, under `docs.profile = mkdocs`, four public docs verbs:

```text
docs:build  docs:serve  docs:nav  docs:structure
```

`validate` calls `lint`, `typecheck`, `test`, and — for `mkdocs` — `docs:build`.
Every other task is `internal: true`. The root `Taskfile.yml` holds wrappers
only: each of its `cmds:` entries is a `task:` call into a `tasks/*.yml`
namespace. Every task carries a non-empty `desc:`.
([ADR-0007](../adr/ADR-0007.md))

In a workspace archetype, `build` and `version` take a package name after `--`
(`task version -- rn-forge-commons`); given none, they act on every member.

**`required_validate`**, per archetype — the tasks that must stay reachable from
`validate`, enforced by `kiln doctor`'s `task-layout` check and by
`kiln doctor`'s `gate.shrunk`:

```text
quality:lint:python          quality:lint:generated
quality:lint:rn-forge-deps   quality:lint:imports
quality:lint:task-layout     quality:lint:ci-entrypoint
quality:typecheck:python     quality:test:python
```

plus, under `docs.profile = mkdocs`:

```text
quality:lint:docs   quality:lint:docs-structure
quality:lint:docs-nav   quality:lint:markdown   docs:build
```

An archetype adds to this list; it never removes from it.

Repo-specific work attaches through `.rn-forge/kiln/config.toml`, never by
editing a managed file:

| Key | Effect |
| -- | -- |
| `[tasks] includes` | wire a repository-owned namespace file into the root Taskfile |
| `[tasks.extra_refs]` | append a call to a managed wrapper verb |
| `[tasks.command_overrides]` | replace one primitive's shell line |

## 2. One owner per file, or per block

Three artifact kinds, and they are the whole model
([ADR-0001](../adr/ADR-0001.md)):

| Kind | Meaning | What CI checks |
| -- | -- | -- |
| **managed** | kiln owns the whole file | its SHA-256 |
| **block** | kiln owns a fenced region inside a repo-owned file | the region's body SHA-256 |
| **seeded** | kiln wrote it once and never returns | that it still exists |

Two owners never write the same bytes. The assignment is normative:

| File / tree | Owner | Artifact kind |
| -- | -- | -- |
| `.rn-forge/kiln/config.toml` | repo (merged, committed input) | input |
| `.rn-forge/kiln/state.json` | kiln | generated, committed CI baseline; never hashes itself |
| `.rn-forge/kiln/standard.md` | kiln | managed — the rendered canon |
| `.rn-forge/kiln/backups/`, `rendered/`, `state.lock` | kiln | gitignored derived data |
| `.gitignore` | repo body; `# BEGIN rn-forge kiln` block → kiln | block |
| `pyproject.toml` | **repo** — verified, not generated ([ADR-0001](../adr/ADR-0001.md)) | input; doctor check `pyproject.tool-config` |
| `.editorconfig` | kiln | managed |
| `.importlinter` | kiln | managed import-boundary contracts |
| `Taskfile.yml`, `tasks/workspace.yml`, `tasks/quality.yml`, `tasks/docs.yml`, archetype namespace files (`tasks/api.yml`, `tasks/web.yml`) | kiln | managed |
| `tasks/self.yml` and any include declared `ownership = "repository"` | repo | seeded once, never rewritten |
| `scripts/**` | **repo only** — a repo's own lints, wired via `[tasks.extra_refs]`. kiln and `cicd` generate nothing here ([ADR-0010](../adr/ADR-0010.md), [ADR-0003](../adr/ADR-0003.md)) | repo |
| `src/**`, `tests/**` | **repo** — kiln verifies *structure* (src layout, package directory naming, test tree shape) and generates nothing ([ADR-0011](../adr/ADR-0011.md)) | input; doctor only |
| `README.md` | written once by `kiln new`, then repo | the single prose home; never rewritten |
| `docs/_areas.yml`, `docs/_structure.md`, `docs/adr/_structure.md` | kiln | **seeded** — repos may extend areas |
| `docs/index.md`, `docs/<area>/index.md` | kiln | **seeded** — written if absent, never touched again |
| `mkdocs.yml` | repo body, written once by `kiln new` with `nav:` as its last key; `# BEGIN generated nav` block → kiln, inserted at the end | block |
| `.github/workflows/ci.yml`, `docs.yml`; `.github/actions/setup`; `sonar-project.properties` | kiln (`cicd`) | managed |
| `CLAUDE.md`, `AGENTS.md` | bodies written once by `kiln new`, then repo; the `<!-- BEGIN rn-forge kiln -->` block in `CLAUDE.md` → kiln | block (`CLAUDE.md` only; `AGENTS.md` points at it) |
| `.claude/**`, `.codex/**`, installed skills | not kiln's | — |
| Repo-specific lints (`check_brand.py`, `check_gate_tags.py`, …) | repo, wired via `[tasks.extra_refs]` | repo |

`docs/_areas.yml` and `_structure.md` are **seeded, not managed**, so a repo can
add an area kiln has never heard of — intellibuild needs a `context` area, and
kiln's own tree has a `plans` area. `doctor` validates against the repo's copy.

To change a managed file: change `.rn-forge/kiln/config.toml`, run `kiln apply`.

### The render matrix

To change what kiln renders: change its Jinja templates, which are the authored
source ([ADR-0005](../adr/ADR-0005.md)). A rendered repo is reviewed whole but
never committed:

1. `task self:golden:render` renders every shipped archetype × flag cell into
   gitignored `.goldens/<ref>/`; `task self:golden:validate` runs each cell's
   gate (`uv sync && task validate`, `actionlint`, `mkdocs build --strict`).
1. The owner reviews and approves the rendered output before a template change
   is done. kiln's CI renders every cell on every pull request.
1. The hand-authored goldens under `tests/fixtures/golden/` are the bootstrap
   reference for the first templates. Until the rendered cells reproduce them
   they are the only runnable standard, and a standard change starts there;
   then they leave git.

## 3. The dependency set

An archetype carries the libraries a repo of that shape is built on
([ADR-0005](../adr/ADR-0005.md)):

| Archetype | Runtime | Dev |
| -- | -- | -- |
| every python repo | `rn-forge-commons` | — |
| `python-app` | + `rn-forge-cli` | — |
| `python-tool` | + `rn-forge-cli`, `rn-forge-tooling` | — |
| `python-lib` | `rn-forge-commons` in each distributable | — |
| `python-web-api` · `python-web-app`, `backend = "django"` | + `rn-forge-cli`, `rn-forge-web`, `rn-forge-django` | + `rn-forge-django[codegen]` |
| `python-web-api` · `python-web-app`, `backend = "fastapi"` | + `rn-forge-cli`, `rn-forge-web`, `rn-forge-fastapi`, when that package exists | + `rn-forge-fastapi[codegen]` |
| `node-lib` · `node-web-app` | — (deferred) | — |

The three python libraries are layered ([ADR-0002](../adr/ADR-0002.md)):
`rn-forge-commons` holds runtime-neutral mechanisms, `rn-forge-cli` holds the
process and command-line shape, `rn-forge-tooling` holds the machinery for a
program that installs itself, owns files in someone else's repo, or renders
templates. `rn-forge-web` holds framework-free inbound HTTP wire semantics on
commons alone, and sits beneath `rn-forge-django` and `rn-forge-fastapi`. A repo
takes the highest layer it actually needs; `check_rn_forge_deps.py`'s `REQUIRED`
list is what makes that a rule rather than a preference.

Every rn-forge requirement is a **PEP 508 direct URL** in `dependencies`:

```toml
dependencies = [
  "rn-forge-commons @ git+https://github.com/rn-forge/pykit@feature/upgrade#subdirectory=packages/rn-forge-commons",
]
```

Never `[tool.uv.sources]` — that is a *local* override which does not survive
into a built wheel, so a consumer of a published package could not resolve the
dependency at all. An `[tool.uv.sources]` entry for an rn-forge package is
rejected outright.

**Until the owner declares pykit stable, repos consume it from its branch**
([ADR-0005](../adr/ADR-0005.md)). The dependency source is a Tier 1 value every
template renders from config: `git` + ref (the default, CI-capable) or `path`
(local only). The checker accepts a branch or path source with a warning and
refuses one in a publish job; goldens and every repo that runs CI use `git`.
Once pykit is tagged, the tag is the version and there is no separate specifier;
flipping a repo to tags is `kiln config upgrade --apply`, not a template change.

`kiln doctor`'s `rn-forge-deps` check enforces three rules — **required**,
**allowed**, **pinned-and-direct**. Its required and allowed lists are config,
so pykit — which *contains* commons and cannot depend on it — renders an empty
required list rather than needing an exemption.

kiln itself is a **dev** dependency of every generated repo, `rn-forge-kiln`
pinned the same way ([ADR-0010](../adr/ADR-0010.md)). A pykit workspace that
takes kiln lists every pykit member kiln reaches in
`[tool.uv] override-dependencies`, so kiln resolves to the workspace copies.

## 4. The import boundary

`rn-forge-commons`, `rn-forge-cli` and `rn-forge-tooling` are the only rn-forge
packages a repo may import (plus its own framework runtime package). Every other
rn-forge component — kiln included, although it is a dev dependency — is a
subprocess or nothing. That rule is enforced at the dependency declaration, in
§3: import-linter rejects subpackages of external packages, so it cannot express
it.

What `.importlinter` enforces is the complement — product code imports no
framework or CLI toolkit *directly* (`typer`, `jinja2`, `click`, `django`,
`fastapi`); those arrive through the rn-forge library that owns them — plus each
archetype's internal boundaries, such as a workspace's packages being
independent of each other, and — inside pykit — the library layering itself:
`rn_forge.commons` may not import `rn_forge.cli` or `rn_forge.tooling`, and
`rn_forge.cli` may not import `rn_forge.tooling`. `quality:lint:imports` runs
it; `task validate` reaches it. ([ADR-0002](../adr/ADR-0002.md))

## 5. What `task validate` proves

CI runs the pinned kiln read-only ([ADR-0010](../adr/ADR-0010.md)): it never
runs `kiln apply` and never writes a generated file. `task validate` runs
`kiln doctor` — the render-free checks, `generated`, `rn-forge-deps`,
`task-layout`, `ci-entrypoint`, `docs-structure`, `docs-nav` and `docs-site` —
on every run. `kiln doctor --full`, which adds a full render and diff, runs
where the workflow asks for it: `lint` runs it when the `KILN_DOCTOR_FULL` task
variable is set, by default on pushes to the default branch and on manual
dispatch.

A cold clone with go-task and the pinned language toolchain — `uv sync`, but no
installed kiln, no `$RNF_HOME`, no bootstrap script — proves all of this:

- ruff is clean and everything is ruff-formatted — `lint:python` asserts both,
  and `format:python` applies them in the order that makes them agree
  (`check --fix`, then `format`);
- the archetype's dependency set is present, allowed, and pinned as a direct
  URL;
- the import contracts hold;
- the task layout is intact and no gate has been removed from `validate`;
- no workflow step invokes a wrapped tool;
- the docs tree matches the repo's `docs/_areas.yml`, the nav block is current,
  every tracked Markdown file is mdformat-clean, and no link or anchor is
  broken (`mkdocs` profile);
- **every managed file and every managed block still hashes to the value
  committed in `.rn-forge/kiln/state.json`**;
- pyright is clean in strict mode ([ADR-0008](../adr/ADR-0008.md));
- the tests pass;
- the docs site builds `--strict` (`mkdocs` profile).

## 6. What `kiln doctor --full` adds

Exactly one question `kiln doctor` cannot ask without `--full`: whether a newer
kiln, or an edited config, would now render something different from what is
committed. Everything else `--full` reports, `kiln doctor` reports too.

kiln is modules under one contract ([ADR-0011](../adr/ADR-0011.md)): `core`,
`python`, `docs`, `tasks`, `cicd` and `instructions`, each owning its config
section, its `kiln new` options, its `artifacts()` and its `checks()`.
`kiln doctor` collects every module's `Finding` rows into one report; a module's
render-free checks are the ones `kiln doctor` runs by default.

| Code prefix | Check |
| -- | -- |
| `config.*` | `config.toml` parses and validates |
| `artifact.missing` / `.drift` / `.stale` | present; disk == committed; committed == fresh render |
| `artifact.seed-missing` | every seeded artifact present |
| `block.missing` / `.stale` | every fenced block present and current |
| `taskgraph.*` | exact public surface; wrappers only at the root; inner tasks internal except `docs:*`; every task has `desc`; every include exists; every `task:` ref resolves; no cycles; no reserved-namespace collision |
| `taskgraph.unresolved-ref` | every `task <name>` in `.github/workflows/**`, `CLAUDE.md`, `AGENTS.md` resolves |
| `ci.entrypoint` | no forbidden tool, `kiln` included, invoked directly in a workflow |
| `gate.shrunk` | tasks reachable from `validate` ⊇ the archetype's `required_validate` |
| `pyproject.tool-config` (warning) | the `[tool.ruff*]`, `[tool.pyright]`, `[tool.pytest.ini_options]` and `[dependency-groups]` tables, and the `[project]` identity fields, match the archetype's expected values — verified, never written |
| `kiln.pin` | `rn-forge-kiln` is in the dev group with a pinned source, and the running kiln is the version `uv.lock` records |
| `ci.unpinned` / `ci.permissions` | every `uses:` SHA-pinned with a version comment; every job has `permissions:` |
| `deps.*` | the §3 contract, re-checked against a fresh render of the archetype's list |
| `docs.structure` / `.nav` / `.links` | tree matches `_areas.yml`; nav current; no broken links, anchors or orphans |
| `hygiene.stray-root-file` (warning) | a tracked root `*.md` outside the allow-list |
| `legacy.kiln-state` (error) | a pre-kiln `.rn-forge/kiln/` or `$RNF_HOME/kiln/` tree |

`kiln doctor --all <paths>` runs the same checks across many repos and prints
one table.

## 7. The state baseline

`.rn-forge/kiln/state.json` is generated and committed:

```json
{
  "schema_version": "1",
  "metadata": { "kiln_version": "…", "config_hash": "…" },
  "entries": {
    "Taskfile.yml":      { "path": "Taskfile.yml", "kind": "managed", "content_hash": "…" },
    ".gitignore#rn-forge kiln": { "path": ".gitignore", "kind": "block",
                           "begin_marker": "# BEGIN rn-forge kiln",
                           "end_marker": "# END rn-forge kiln",
                           "content_hash": "…" },
    "docs/index.md":     { "path": "docs/index.md", "kind": "seeded" }
  }
}
```

It is written by tooling's generation engine, in that engine's format: a
`content_hash` is the SHA-256 hex digest of the file — of a block's body, as
read between its markers — and a block's key is its path and block name. It
never contains an entry for itself. `kiln doctor`'s `generated` check reads it
without rendering anything ([ADR-0003](../adr/ADR-0003.md),
[ADR-0010](../adr/ADR-0010.md)).

## 8. CI shape

`validate → sonar → release`, with the release job a matrix over the workspace
members for `python-lib`. The rules:

- Repeated setup lives in the committed composite action
  `.github/actions/setup`, not in a copy per job.
- Every `uses:` is SHA-pinned with the version in a trailing comment; every job
  declares least-privilege `permissions:`; the workflow declares
  `concurrency:` per ref. Dependabot watches kiln, not the generated
  workflows.
- `UV_LOCKED: "1"` at workflow level: CI resolves the committed lockfile and
  never rewrites it.
- The Sonar job is skipped for fork pull requests, whose workflows cannot see
  `SONAR_TOKEN`. Validation stays required.
- `sonar.qualitygate.wait=true`, and `release` depends on `sonar`. Submitting an
  analysis is not passing a gate.
- Release is idempotent: the **release**, not the tag, is the record of what
  shipped, and the tag is created by the publish step itself. A failed publish
  is therefore resumable; a tag-first design made it permanent.

## 9. Configuration

`.rn-forge/kiln/config.toml` is the one committed input
([ADR-0004](../adr/ADR-0004.md)). It is a pydantic strict model; every failure
is reported with its dotted path, never just the first.

```toml
schema_version = 1

[source]                         # written by kiln new; absent without --config
location = "git+https://github.com/my-org/kiln-profile"  # or a local path
ref = "main"                     # a branch is allowed
commit = "…"                     # the resolved commit

[repository]
name = "my-tool"
archetype = "python-tool"  # python-app | python-tool | python-lib
                           # python-web-api | python-web-app
                           # node-lib | node-web-app   (deferred)
lifecycle = false          # any python archetype; python-tool is the alias
                           # for python-app + lifecycle = true (ADR-0005)

[docs]
profile = "mkdocs"         # mkdocs | external | none
site_dir = ".docs-site"    # mkdocs only
external_url = ""          # external only; surfaced in the instructions block

[ci]
provider = "github"        # github only in v1; "ado" reserved
sonar = true
release = "tag-exists"     # tag-exists | none

[tasks]
includes = [{ namespace = "self", taskfile = "tasks/self.yml" }]

[tasks.extra_refs]
lint = ["self:check:dist"]

[tasks.command_overrides]
"quality:test:python" = "uv run pytest -q -p no:randomly"

[archetype.python-lib]
packages = ["packages/rn-forge-commons", "packages/rn-forge-django"]

[archetype.python-app]           # or [archetype.python-tool]
packages = []                    # internal-only; never published

[archetype.python-web-api]
backend = "fastapi"            # fastapi (shipped) | django (untested)
api_dir = "apps/api"
admin_ui = false                 # a thin self-contained management surface

[archetype.python-web-app]
backend = "fastapi"            # fastapi (shipped) | django (untested)
frontend = "angular"             # angular (shipped) | react | svelte (untested)
api_dir = "apps/api"
web_dir = "apps/web"
nx_cloud = false                 # an account decision, not a repo shape

[cli]                            # ADR-0009; read by rn-forge-cli, not by kiln
name = "my-tool"
options = ["json", "dry-run", "yes", "log-level"]
```

`--backend` and `--frontend` map to the matching keys under
`[archetype.<name>]`. They select an implementation library, never a topology
([ADR-0005](../adr/ADR-0005.md)): a pnpm-managed Nx workspace — Nx's own
documented shape — is what the `-app` archetypes mean, and the presence of a
separate frontend package is what separates `python-web-app` from
`python-web-api`. A flag value without a golden repo is `untested` and
`kiln new` refuses it.

The archetype selects the toolchain and which components exist. Reject a backend
or frontend selector when that archetype has no corresponding component, and
reject implementations outside its supported values. `frontend = "none"` cannot
turn a web app into an API-only repo. There is no `framework` alias,
`web_runner`, `stack`, or separate `runtime` selector. Additional ecosystems
such as Java require new archetypes; they are outside E5's scope.

### Layered configuration

Configuration is resolved once and committed.
`kiln new --config <path|git-url[@ref]>` deep-merges kiln defaults → each source
layer → flags, and writes the merged result with a `[source]` table recording
the location, the ref and the resolved commit. **Lists replace**: a layer that
sets a list owns the whole list, so removing an inherited entry needs no second
syntax.

| Command | Reads | Writes |
| -- | -- | -- |
| `kiln apply`, `kiln doctor`, `kiln diff` | only the committed `config.toml`; never the source | — |
| `kiln config update [--dry-run] [--apply]` | the recorded source, with the running kiln's defaults | re-merged `config.toml`; prints the artifacts that would change, and `--apply` runs `kiln apply` |
| `kiln config upgrade [--dry-run] [--apply]` | the recorded source, with a newer kiln's defaults and schema | migrated and re-merged `config.toml`; as `update` |

Every load validates against the running kiln's schema; a config written by a
newer kiln is refused with the version it needs. Local edits survive
re-resolution: `state.json` records per-key provenance, and a key whose
committed value differs from what its layer last supplied is a repo override
that `update` and `upgrade` keep and list.
