# The standard repository

The normative statement of what an rn-forge repository is. The reasoning behind
each rule is in [the decision log](../adr/index.md); this page states the rules.

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
([ADR-0008](../adr/0008-task-vocabulary.md))

Repo-specific work attaches through `.rn-forge/kiln/config.toml`:

| Key | Effect |
| --- | --- |
| `[tasks] includes` | wire a repository-owned namespace file into the root Taskfile |
| `[tasks.extra_refs]` | append a call to a managed wrapper verb |
| `[tasks.command_overrides]` | replace one primitive's shell line |

Never by editing a managed file.

## 2. One owner per file, or per block

Three artifact kinds, and they are the whole model:

| Kind | Meaning | What CI checks |
| --- | --- | --- |
| **managed** | kiln owns the whole file | its SHA-256 |
| **block** | kiln owns a fenced region inside a repo-owned file | the region's body SHA-256 |
| **seeded** | kiln wrote it once and never returns | that it still exists |

The assignment is the table in [ADR-0002](../adr/0002-the-ownership-table.md).
Two owners never write the same bytes.

To change a managed file: change `.rn-forge/kiln/config.toml`, run `kiln apply`.
To change what kiln renders: change the golden repo in kiln, let the snapshot
test fail, update the template until it passes
([ADR-0006](../adr/0006-archetypes-and-golden-repos.md)).

## 3. The dependency set

An archetype is a shape *and* a set of component libraries
([ADR-0009](../adr/0009-archetype-dependency-defaults.md)). Every repo depends on
`rn-forge-commons`; a `python-cli` repo also on `rn-forge-tooling`; a
`python-web` repo also on the framework package its `backend` names, with that
package's `[codegen]` extra as a dev dependency.

rn-forge distributions are git sources — pykit publishes GitHub Releases, not to
PyPI — and every one of them resolves to a `tag` or a `rev`, never a branch.

`scripts/standards/check_rn_forge_deps.py` enforces all three rules: required,
allowed, pinned. Its `REQUIRED` and `ALLOWED` lists are config in its header, so
a repo that legitimately cannot take the default — pykit, which contains commons
— renders an empty list rather than an exemption.

## 4. The import boundary

`rn-forge-commons` and `rn-forge-tooling` are the only rn-forge packages a repo
may import. Every other rn-forge component — kiln and agentkit included — is a
subprocess or nothing. That rule is enforced at the dependency declaration, by
the checker above: import-linter rejects subpackages of external packages, so it
cannot express it.

What `.importlinter` does enforce is the complement — product code imports no
framework or CLI toolkit *directly* (`typer`, `jinja2`, `click`, `django`,
`fastapi`); those arrive through the rn-forge library that owns them — plus each
archetype's internal boundaries, such as a workspace's packages being
independent of each other. `quality:lint:imports` runs it; `task validate`
reaches it. ([ADR-0003](../adr/0003-the-dependency-graphs.md),
[ADR-0009](../adr/0009-archetype-dependency-defaults.md))

## 5. What `task validate` proves without kiln

A cold clone with go-task and the pinned language toolchain — no kiln, no
agentkit, no `$RNF_HOME`, no bootstrap script — proves all of this:

- ruff is clean;
- the archetype's dependency set is present, allowed and pinned;
- the import contracts hold;
- the task layout is intact and no gate has been removed from `validate`;
- no workflow step invokes a wrapped tool;
- the docs tree matches the repo's `docs/_areas.yml`, the nav block is current,
  and no link or anchor is broken (`mkdocs` profile);
- **every managed file and every managed block still hashes to the value
  committed in `.rn-forge/kiln/state.json`**;
- the type checker is clean;
- the tests pass;
- the docs site builds `--strict` (`mkdocs` profile).

## 6. What `kiln doctor` adds

Exactly one question CI cannot ask: whether a newer kiln, or an edited config,
would now render something different from what is committed. Everything else it
reports, CI reports too.

| Code prefix | Check |
| --- | --- |
| `config.*` | `config.toml` parses and validates |
| `artifact.missing` / `.drift` / `.stale` | present; disk == committed; committed == fresh render |
| `artifact.seed-missing` | every seeded artifact present |
| `block.missing` / `.stale` | every fenced block present and current |
| `taskgraph.*` | exact public surface; wrappers only at the root; inner tasks internal except `docs:*`; every task has `desc`; every include exists; every `task:` ref resolves; no cycles; no reserved-namespace collision |
| `taskgraph.unresolved-ref` | every `task <name>` in `.github/workflows/**`, `CLAUDE.md`, `AGENTS.md` resolves |
| `ci.entrypoint` | no forbidden tool, `kiln` included, invoked directly in a workflow |
| `gate.shrunk` | tasks reachable from `validate` ⊇ the archetype's `required_validate` |
| `ci.unpinned` / `ci.permissions` | every `uses:` SHA-pinned with a version comment; every job has `permissions:` |
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
([ADR-0004](../adr/0004-ci-runs-committed-code.md))

## 8. CI shape

`validate → sonar → check-version → build → publish`, with the release half a
matrix over `[archetype.python-lib] packages` for a workspace. Every `uses:` is
SHA-pinned with the version in a trailing comment; every job declares
least-privilege `permissions:`; the workflow declares `concurrency:` per ref.
Release is a tag-exists check: a push whose version is already tagged is a no-op,
not a failure. Dependabot watches kiln, not the generated workflows.
