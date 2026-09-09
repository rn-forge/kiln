# ADR-0005 — The `.rn-forge/` umbrella, the config schema, the state schema

**Status:** accepted

## Context

`.rn-forge/` had no owner: each kit wrote its own gitignore block and its own
root-discovery logic, and the retired predecessor of this tool wrote both a
global and a project-local `.rn-forge/kiln/` tree (F14). apollo's configuration
also showed what happens when a tool infers rather than reads: tool config at the
root `pyproject.toml`, tasks emitted with `dir: apps/api`, and a detection layer
that got it wrong (F13).

## Decision

**kiln owns the umbrella.** There is no umbrella-level manifest file; each kit
keeps its own `.rn-forge/<kit>/config.toml`, following the existing convention.

```text
.rn-forge/kiln/
  config.toml     hand-authored input — the only one
  state.json      generated, committed; the CI baseline
  standard.md     generated; the canon rendered for this repo
  backups/        gitignored
  rendered/       gitignored staging
```

`config.toml` is a pydantic strict model. Every failure is reported with its
dotted path, never just the first:

```toml
schema_version = 1

[repository]
name = "agentkit"
archetype = "python-cli"        # python-cli | python-lib | python-web

[docs]
profile = "mkdocs"              # mkdocs | external | none
site_dir = ".docs-site"
external_url = ""

[ci]
provider = "github"             # github only in v1; "ado" reserved
sonar = true
release = "tag-exists"          # tag-exists | none

[tasks]
includes = [{ namespace = "self", taskfile = "tasks/self.yml" }]

[tasks.extra_refs]              # appended to the managed wrapper verbs
lint = ["self:check:dist"]

[tasks.command_overrides]       # replace one primitive's shell line
"quality:test:python" = "uv run pytest -q -p no:randomly"

[archetype.python-lib]
packages = ["packages/rn-forge-commons"]
```

**The archetype is asserted, never inferred.** Detection was 1,950 of taskkit's
5,248 lines and produced roughly 80 lines of YAML for taskkit's own repo (F16);
it is not built.

`state.json` carries `schema_version`, `metadata` (`kiln_version`,
`config_hash`) and `entries`. A managed entry stores `path`, `kind` and
`content_hash`; a block entry adds its exact begin and end markers and hashes
the body only; a seeded entry stores presence and no hash at all, because kiln
must never care what a repo did with a file it seeded.

**Legacy trees are never overwritten implicitly.** A pre-existing
`.rn-forge/kiln/` or `$RNF_HOME/kiln/` without `schema_version` belongs to the
retired predecessor; kiln refuses and reports `legacy.kiln-state`. Removing it
is an explicit user action.

## Consequences

- One file to hand-edit, one to commit as the baseline, and two gitignored.
- A repo whose shape defeats inference (apollo) is described rather than
  detected, so the failure mode becomes "the config is wrong", which a human can
  read and fix.
- Reassigning the `kiln` name costs one doctor rule.
