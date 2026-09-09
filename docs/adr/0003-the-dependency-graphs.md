# ADR-0003 — Two dependency graphs, and an executable boundary

**Status:** accepted

## Context

Both kits had grown their own `core/{state,config,paths,io}.py` with overlapping
mechanisms and drifting dependency floors — `typer>=0.26.8` in one,
`typer>=0.12` in the other (F12). Meanwhile pykit's commons already held most of
what a shared core would provide, but at the wrong package boundary: local
development mechanisms (a state store, a template engine, Typer wiring) had
landed in a runtime-neutral library (F17).

Left alone, that ends one of two ways: a repo takes a build dependency on a CLI
kit, or a runtime library grows a dependency on Typer.

## Decision

Two graphs, with different rules.

```text
commons (pykit) ──► tooling (pykit) ──► kiln
                          │       └───► agentkit
                          └───► rn-forge-django[codegen]

kiln ──subprocess──► agentkit          (never the reverse)
kiln ──entry points─► *[codegen]       (kiln never imports a framework)
```

**The library graph is acyclic.** `rn-forge-commons` and `rn-forge-tooling` are
the only rn-forge packages that may be a build dependency of a kit. Tooling
depends on commons; commons never imports tooling.

**The tooling graph is free.** kiln and agentkit never import each other; kiln
calls agentkit as a subprocess. pykit adopting kiln as dev tooling is not a
cycle, because nothing is imported.

**Framework generators are `[codegen]` extras of their runtime package.**
`rn-forge-django[codegen]` installs tooling, Typer and Jinja; the code lives in
`rn_forge.django.codegen`, which the runtime surface never imports. Generators
register under the `rn_forge.kiln.generators` entry-point group and are
Python-callable without Typer; kiln supplies the command surface. Co-versioning
with the runtime is the reason they ship together.

**The boundary is executable.** Every repo carries an `.importlinter` contract
that kiln owns, `import-linter` is a dev dependency, an internal
`quality:lint:imports` task runs `lint-imports`, root `lint` calls it, and CI
reaches it through `task validate`. In pykit the contract additionally forbids
`rn_forge.django` minus `rn_forge.django.codegen` from importing
`rn_forge.tooling`, `typer` or `jinja2`.

## Consequences

- A framework package can be installed by an application with no generator
  dependencies at all, and `import rn_forge.django` succeeds with no extras.
- "Which package does this belong in?" has a mechanical answer: runtime-neutral
  → commons, shared local-development → tooling, rn-forge policy → kiln.
- The contract fails in the developer's own `task lint`, not in review.
