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
`scripts/ci/check_ci_entrypoint.py` enforces that for every workflow file; the
forbidden list is the archetype's, carried in the script's config header.

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
([ADR-0007](../adr/0007-task-vocabulary.md))

In a workspace archetype, `build` and `version` take a package name after `--`
(`task version -- rn-forge-commons`); given none, they act on every member.

**`required_validate`**, per archetype — the tasks that must stay reachable from
`validate`, enforced by `scripts/task/check_task_layout.py` and by
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
([ADR-0001](../adr/0001-ownership.md)):

| Kind | Meaning | What CI checks |
| -- | -- | -- |
| **managed** | kiln owns the whole file | its SHA-256 |
| **block** | kiln owns a fenced region inside a repo-owned file | the region's body SHA-256 |
| **seeded** | kiln wrote it once and never returns | that it still exists |

Two owners never write the same bytes. The assignment is normative:

| File / tree | Owner | Kind |
| -- | -- | -- |
| `.rn-forge/kiln/config.toml` | repo (hand-edited input) | input |
| `.rn-forge/kiln/state.json` | kiln | managed; the CI baseline; never hashes itself |
| `.rn-forge/kiln/standard.md` | kiln | managed — the rendered canon |
| `.rn-forge/kiln/backups/`, `rendered/` | kiln | gitignored derived data |
| `.rn-forge/agentkit/**` | agentkit | as today |
| `.gitignore` | repo body; `# BEGIN rn-forge kiln` → kiln; `# BEGIN rn-forge agentkit` → agentkit | block |
| `.editorconfig` | kiln | managed |
| `.importlinter` | kiln | managed |
| `.mdformat.toml` | kiln | **seeded** — its presence opts the repo in; the style is the repo's |
| `Taskfile.yml`, `tasks/workspace.yml`, `tasks/quality.yml`, `tasks/docs.yml`, archetype namespace files | kiln | managed |
| `tasks/self.yml`, and any include declared `ownership = "repository"` | repo | seeded once, never rewritten |
| `scripts/task/check_task_layout.py`, `scripts/ci/check_ci_entrypoint.py` | kiln | managed (config header) |
| `scripts/standards/check_generated.py`, `scripts/standards/check_rn_forge_deps.py` | kiln | managed; stdlib-only CI checkers |
| `scripts/docs/{_common,check_docs,gen_nav,check_structure}.py` | kiln (`mkdocs` profile) | managed |
| `.github/actions/setup/action.yml` | kiln | managed |
| `.github/workflows/ci.yml`, `docs.yml`; `sonar-project.properties` | kiln | managed |
| `docs/_areas.yml`, `docs/_structure.md`, `docs/<area>/_structure.md` | kiln | **seeded** — repos extend their areas |
| `docs/index.md`, `docs/<area>/index.md` | kiln | **seeded** — written if absent, never touched again |
| `mkdocs.yml` | repo body; `# BEGIN generated nav` → kiln | block |
| `CLAUDE.md` | body seeded by agentkit; `<!-- BEGIN rn-forge kiln -->` → kiln; agentkit's own block → agentkit | block |
| `AGENTS.md` | agentkit | seeded — a static pointer at `CLAUDE.md`, so there is one file to keep current |
| `.claude/**`, `.codex/**`, installed skills | agentkit | as today |
| `pyproject.toml`, `src/**`, `tests/**` | repo | not kiln's after the scaffold — but its rn-forge dependencies are constrained by §3 |
| Repo-specific lints (`check_brand.py`, …) | repo, wired via `[tasks.extra_refs]` | repo |

`docs/_areas.yml` and `_structure.md` are **seeded, not managed**, so a repo can
add an area kiln has never heard of — intellibuild needs a `context` area, and
kiln's own tree has a `plans` area. `doctor` validates against the repo's copy.

To change a managed file: change `.rn-forge/kiln/config.toml`, run `kiln apply`.
To change what kiln renders: change the golden repo in kiln, let the snapshot
test fail, update the template until it passes
([ADR-0005](../adr/0005-archetypes.md)).

## 3. The dependency set

An archetype carries the libraries a repo of that shape is built on
([ADR-0005](../adr/0005-archetypes.md)):

| Archetype | Runtime | Dev |
| -- | -- | -- |
| every python repo | `rn-forge-commons` | — |
| `python-app` | + `rn-forge-cli` | — |
| `python-tool` | + `rn-forge-cli`, `rn-forge-tooling` | — |
| `python-lib` | `rn-forge-commons` in each distributable | — |
| `python-web-api` · `python-web-app`, `framework = "django"` | + `rn-forge-cli`, `rn-forge-django` | + `rn-forge-django[codegen]` |
| `python-web-api` · `python-web-app`, `framework = "fastapi"` | + `rn-forge-cli`, `rn-forge-fastapi`, when that package exists | + `rn-forge-fastapi[codegen]` |
| `node-lib` · `node-web-app` | — (deferred) | — |

The three python libraries are layered
([ADR-0002](../adr/0002-the-dependency-graphs.md)): `rn-forge-commons` holds
runtime-neutral mechanisms, `rn-forge-cli` holds the process and command-line
shape, `rn-forge-tooling` holds the machinery for a program that installs
itself, owns files in someone else's repo, or renders templates. A repo takes
the highest layer it actually needs; `check_rn_forge_deps.py`'s `REQUIRED` list
is what makes that a rule rather than a preference.

Every rn-forge requirement is a **pinned PEP 508 direct URL** in `dependencies`:

```toml
dependencies = [
  "rn-forge-commons @ git+https://github.com/rn-forge/pykit@rn-forge-commons-v0.2.2#subdirectory=packages/rn-forge-commons",
]
```

Never `[tool.uv.sources]` — that is a *local* override which does not survive
into a built wheel, so a consumer of a published package could not resolve the
dependency at all. An `[tool.uv.sources]` entry for an rn-forge package is
rejected outright. The tag is the version; there is no separate specifier.

`scripts/standards/check_rn_forge_deps.py` enforces three rules — **required**,
**allowed**, **pinned-and-direct**. Its `REQUIRED`, `ALLOWED` and
`PYPROJECT_PATHS` lists are config in its header, so pykit — which *contains*
commons and cannot depend on it — renders an empty `REQUIRED` rather than
needing an exemption.

## 4. The import boundary

`rn-forge-commons`, `rn-forge-cli` and `rn-forge-tooling` are the only rn-forge
packages a repo may import (plus its own framework runtime package). Every other
rn-forge component — kiln and agentkit included — is a subprocess or nothing.
That rule is enforced at the dependency declaration, in §3: import-linter
rejects subpackages of external packages, so it cannot express it.

What `.importlinter` enforces is the complement — product code imports no
framework or CLI toolkit *directly* (`typer`, `jinja2`, `click`, `django`,
`fastapi`); those arrive through the rn-forge library that owns them — plus each
archetype's internal boundaries, such as a workspace's packages being
independent of each other, and — inside pykit — the library layering itself:
`rn_forge.commons` may not import `rn_forge.cli` or `rn_forge.tooling`, and
`rn_forge.cli` may not import `rn_forge.tooling`. `quality:lint:imports` runs
it; `task validate` reaches it.
([ADR-0002](../adr/0002-the-dependency-graphs.md))

## 5. What `task validate` proves without kiln

A cold clone with go-task and the pinned language toolchain — no kiln, no
agentkit, no `$RNF_HOME`, no bootstrap script — proves all of this:

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
- pyright is clean in strict mode
  ([ADR-0008](../adr/0008-pyright-strict-not-mypy.md));
- the tests pass;
- the docs site builds `--strict` (`mkdocs` profile).

## 6. What `kiln doctor` adds

Exactly one question CI cannot ask: whether a newer kiln, or an edited config,
would now render something different from what is committed. Everything else it
reports, CI reports too.

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
  "schema_version": 1,
  "metadata": { "kiln_version": "…", "config_hash": "sha256:…" },
  "entries": {
    "Taskfile.yml":      { "path": "Taskfile.yml", "kind": "managed", "content_hash": "sha256:…" },
    ".gitignore::kiln":  { "path": ".gitignore", "kind": "block",
                           "begin_marker": "# BEGIN rn-forge kiln",
                           "end_marker": "# END rn-forge kiln",
                           "content_hash": "sha256:…" },
    "docs/index.md":     { "path": "docs/index.md", "kind": "seeded" }
  }
}
```

It never contains an entry for itself. `scripts/standards/check_generated.py`
reads it with the standard library alone, so a cold clone can run it.
([ADR-0003](../adr/0003-ci-runs-committed-code.md))

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

`.rn-forge/kiln/config.toml` is the one hand-authored input
([ADR-0004](../adr/0004-the-rn-forge-umbrella.md)). It is a pydantic strict
model; every failure is reported with its dotted path, never just the first.

```toml
schema_version = 1

[repository]
name = "agentkit"
archetype = "python-tool"  # python-app | python-tool | python-lib
                           # python-web-api | python-web-app
                           # node-lib | node-web-app   (deferred)

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
framework = "fastapi"            # fastapi (shipped) | django (untested)
api_dir = "apps/api"
admin_ui = false                 # a thin self-contained management surface

[archetype.python-web-app]
framework = "django"             # django | fastapi   (both shipped)
frontend = "angular"             # angular (shipped) | react | svelte (untested)
api_dir = "apps/api"
web_dir = "apps/web"
nx_cloud = false                 # an account decision, not a repo shape

[cli]                            # ADR-0009; read by rn-forge-cli, not by kiln
name = "agentkit"
options = ["json", "dry-run", "yes", "log-level"]
```

There is no `backend` key and no `web_runner` key. `framework` and `frontend`
select an implementation library, never a topology
([ADR-0005](../adr/0005-archetypes.md)): a pnpm-managed Nx workspace — Nx's own
documented shape — is what the `-app` archetypes mean, and the presence of a
separate frontend package is what separates `python-web-app` from
`python-web-api`. A flag value without a golden repo is `untested` and
`kiln new` refuses it.
