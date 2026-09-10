# ADR-0002 — Two dependency graphs, and an executable boundary

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

### Alternatives considered

- **One `forge-core` package for everything shared.** Specified in revision 3
  and dropped: it would have to depend on Typer to be useful to the kits,
  which makes Typer a transitive dependency of every Django application that
  imports it.
- **One graph, enforced by convention.** The drifting Typer floors are what
  convention produced.
- **Framework generators as separate provider packages**
  (`rn-forge-django-gen`). Rejected because a generator must be co-versioned
  with the runtime whose code it emits, and two distributions cannot be
  co-versioned by wishing.

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

**The boundary is executable, in two halves**, because one tool cannot express
both:

- **At the dependency**, by `scripts/standards/check_rn_forge_deps.py`: which
  rn-forge distributions a repo may depend on at all
  ([ADR-0005](0005-archetypes.md)). import-linter rejects subpackages of
  external packages, so `rn_forge.kiln` cannot be named as a forbidden module
  — verified, with and without `rn_forge` installed.
- **At the import**, by `.importlinter`: no direct import of a framework or CLI
  toolkit that an rn-forge library already owns, plus each archetype's
  internal boundaries. In pykit it also forbids `rn_forge.django` minus
  `rn_forge.django.codegen` from importing `rn_forge.tooling`, `typer` or
  `jinja2`.

`import-linter` is a dev dependency, an internal `quality:lint:imports` task
runs `lint-imports`, root `lint` calls it, and CI reaches it through
`task validate`.

## Consequences

- A framework package can be installed by an application with no generator
  dependencies at all, and `import rn_forge.django` succeeds with no extras.
- "Which package does this belong in?" has a mechanical answer: runtime-neutral
  → commons, shared local-development → tooling, rn-forge policy → kiln.
- The boundary fails in the developer's own `task lint`, not in review.
- Two enforcement mechanisms instead of one is a real cost. It is the price of
  the rule being true rather than merely written down.
