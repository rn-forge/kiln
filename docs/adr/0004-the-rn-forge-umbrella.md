# ADR-0004 — The `.rn-forge/` umbrella, and asserted configuration

**Status:** accepted

## Context

`.rn-forge/` had no owner: each kit wrote its own gitignore block and its own
root-discovery logic, and the retired predecessor of this tool wrote both a
global and a project-local `.rn-forge/kiln/` tree (F14). apollo also showed what
happens when a tool infers rather than reads: tool config at the root
`pyproject.toml`, tasks emitted with `dir: apps/api`, and a detection layer that
got it wrong (F13).

### Alternatives considered

- **Detect the repo's shape.** taskkit did. Discovery, planner and adapters were
  1,950 of its 5,248 lines and produced roughly 80 lines of YAML for taskkit's
  own repo (F16), and still misread apollo.
- **An umbrella-level manifest** listing every kit's config. A second registry
  to keep in step with the directory it describes.
- **Config in `pyproject.toml`.** Couples repo policy to a Python packaging file
  that a `python-*-ng` repo's frontend half has no reason to contain.

## Decision

**kiln owns the umbrella**, and each kit keeps its own
`.rn-forge/<kit>/config.toml` — no umbrella-level manifest.

```text
.rn-forge/kiln/
  config.toml     hand-authored input — the only one
  state.json      generated, committed; the CI baseline
  standard.md     generated; the canon rendered for this repo
  backups/        gitignored
  rendered/       gitignored staging
```

**The archetype is asserted, never inferred.** `config.toml` is a pydantic
strict model; every failure is reported with its dotted path, never just the
first. Its schema is documented in
[the standard-repo reference](../reference/standard-repo.md#9-configuration),
which is where it changes as options are added.

**State records what was written, not how.** A managed entry stores `path`,
`kind` and `content_hash`; a block entry adds its exact fence markers and hashes
the body only; a seeded entry stores presence and no hash at all, because kiln
must never care what a repo did with a file it seeded. State never contains an
entry for itself.

**Legacy trees are never overwritten implicitly.** A pre-existing
`.rn-forge/kiln/` or `$RNF_HOME/kiln/` without `schema_version` belongs to the
retired predecessor that once held this name; kiln refuses and reports
`legacy.kiln-state`. Removing it is an explicit user action.

## Consequences

- One file to hand-edit, one to commit as the baseline, and two gitignored.
- A repo whose shape defeats inference is *described* rather than detected, so
  its failure mode becomes "the config is wrong" — which a human can read.
- Asserting the archetype means a new repo shape needs a config option or a new
  archetype, not a smarter detector. That is the intended pressure.
- Reassigning the `kiln` name costs exactly one doctor rule.
