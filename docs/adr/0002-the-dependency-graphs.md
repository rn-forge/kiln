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

The first revision of this ADR drew one line, between *runtime-neutral* and
*development-time*, and put everything on the development side into one package.
The Phase C review showed that line is in the wrong place. A business batch or a
scheduled ML job is a CLI: it wants the Typer app factory, the console, the
standard flag set and the error-to-exit-code mapping that
[ADR-0009](0009-tooling-owns-the-boilerplate.md) says a repo should never write.
It does not want the generation engine, the template engine, the local state
store or the installer. Under one package it had to take all of them, from a
distribution whose own contract told deployed code not to depend on it — so it
wrote its own `main()` instead, which is the outcome ADR-0009 exists to prevent.

The seam is not workstation-versus-runtime. It is *every CLI* versus *tools that
install, generate and own files*.

### Alternatives considered

- **One `forge-core` package for everything shared.** Specified in revision 3
  and dropped: it would have to depend on Typer to be useful to the kits,
  which makes Typer a transitive dependency of every Django application that
  imports it.
- **One graph, enforced by convention.** The drifting Typer floors are what
  convention produced.
- **One `rn-forge-tooling` with a `[gen]` extra.** The cheaper split. Rejected:
  an extra adds dependencies, it does not conditionally exclude modules or
  prevent an eager package initializer from importing them. Making it work
  needs lazy `__getattr__` exports plus a discipline nothing checks, and the
  distribution still carries a name that tells a business batch not to use it.
- **Renaming tooling to `devtools`, `automation` or `core`.** Considered in the
  Phase C review and rejected there: none of them changes an architectural
  property, and `core`/`foundation` would create a second vaguely defined
  common package beside commons.
- **Framework generators as separate provider packages**
  (`rn-forge-django-gen`). Rejected because a generator must be co-versioned
  with the runtime whose code it emits, and two distributions cannot be
  co-versioned by wishing.

## Decision

### Three library layers

```text
commons ──► cli ──► tooling ──► kiln
   │         │         │    └─► agentkit
   │         │         └──────► rn-forge-django[codegen]
   │         └────────────────► every python-app repo
   └──────────────────────────► rn-forge-django, rn-forge-fastapi

kiln ──subprocess──► agentkit          (never the reverse)
kiln ──entry points─► *[codegen]       (kiln never imports a framework)
```

| Layer | Distribution | Holds | Depends on |
| -- | -- | -- | -- |
| **runtime** | `rn-forge-commons` | runtime-neutral mechanisms: collections, dataclasses, documents, configuration, logging, filesystem and text-file primitives, hashing, entry-point discovery, `Finding`, the integration protocols | — |
| **application** | `rn-forge-cli` | the Typer app factory, `AppConsole`, the standard option set, logging wiring, error-to-exit-code mapping, and the declared `[cli]` surface | commons, typer, rich |
| **developer tool** | `rn-forge-tooling` | the generation engine, the template engine, local state, installer mechanics, docs mechanics | commons, cli, jinja2 |

The layers are ordered by what a consumer gives up. A library gives up nothing
and takes commons. Any application with a command line takes `rn-forge-cli` and
gains a process shape it did not write. A tool that installs itself, owns files
in someone else's repo, or renders templates takes `rn-forge-tooling`.

**The library graph is acyclic**, and it is the whole set: commons, cli and
tooling are the only rn-forge packages that may be a build dependency of a kit.
Each layer depends only downward; commons never imports cli, and cli never
imports tooling.

**Test for placement.** Not "who calls it today" — the only current callers are
developer tools, so that test returns the same answer for everything. The test
is what the API's *signature* contains. A directory lock and an atomic symlink
carry no installer policy, so they are commons. An archive extractor that
requires exactly one root directory encodes a release-bundle convention, so it
is tooling. A template engine that hardcodes `autoescape=False` and adds TOML
and YAML filters targets generated configuration, so it is tooling.

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
  `jinja2`, and holds the layering itself as a contract: `rn_forge.commons`
  may not import `rn_forge.cli` or `rn_forge.tooling`, and `rn_forge.cli` may
  not import `rn_forge.tooling`.

`import-linter` is a dev dependency, an internal `quality:lint:imports` task
runs `lint-imports`, root `lint` calls it, and CI reaches it through
`task validate`.

## Consequences

- A framework package can be installed by an application with no generator
  dependencies at all, and `import rn_forge.django` succeeds with no extras.
- "Which package does this belong in?" has a mechanical answer read off the
  signature: runtime-neutral mechanism → commons, process and command-line
  shape → cli, owns-files/installs/renders → tooling, rn-forge policy → kiln.
- A batch or ML repo gets ADR-0009's zero-boilerplate `main()` without
  installing Jinja2 or a generation engine, and without depending on a package
  that tells it not to.
- One more distribution to release, pin and document. Accepted: the alternative
  is a name that lies to most of the fleet.
- The boundary fails in the developer's own `task lint`, not in review.
- Two enforcement mechanisms instead of one is a real cost. It is the price of
  the rule being true rather than merely written down.
