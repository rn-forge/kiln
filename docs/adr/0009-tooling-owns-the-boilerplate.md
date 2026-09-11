# ADR-0009 — The libraries own the boilerplate; the CLI is declared, not written

**Status:** proposed

*Proposed rather than accepted because `rn-forge-cli` and `rn-forge-tooling` do
not exist yet: they are extracted in Phase C. This ADR is what that extraction
is aimed at, so that the package boundary is chosen against a known target
instead of being discovered afterwards.*

*Revised after the Phase C review: the boilerplate does not all live in one
package. The command-line boilerplate is `rn-forge-cli`; the file-owning
machinery is `rn-forge-tooling`. See [ADR-0002](0002-the-dependency-graphs.md)
for why the seam moved.*

## Context

[ADR-0005](0005-archetypes.md) says an archetype carries a library set, and the
golden repos now prove the wiring. But wiring a library in is not the same as
the library being worth wiring in. The question the Phase B review raised is
what `rn-forge-commons` and `rn-forge-tooling` must actually *hold* for a
generated repo to contain no boilerplate at all.

The evidence for what that is comes from the two kits that wrote it twice:

- **CLI construction.** agentkit and taskkit each built their own Typer app
  factory, their own `--json` / `--dry-run` / `--yes` flag set, their own
  console wrapper and their own error-to-exit-code mapping. They drifted to
  `typer>=0.26.8` and `typer>=0.12` (F12).
- **Logging.** Each kit configured logging its own way; commons had `AppLogger`
  and neither used it.
- **Local state and templates.** Both grew `core/{state,config,paths,io}.py`
  over the same ground (F12), which commons already covered at the wrong
  package boundary (F17).

The generated repo is currently honest about this and unhelpful: `kiln new`
gives you a perfect pipeline around a `main()` you write from scratch.

### Alternatives considered

- **Leave it. The libraries exist; repos import what they need.** This is the
  status quo that produced two Typer floors and two console conventions. A
  library nobody is *steered* into using is a library that gets rewritten.
- **Generate the CLI boilerplate as template files.** Every repo then owns a
  copy of the same 200 lines, which is F2 with extra steps: the fix for a bug
  in the argument parsing would be N commits instead of a version bump.
- **A full application generator** — `kiln generate cli command sync`, emitting
  command modules. This is what D2 defers, and deferring it is still right:
  the interesting decisions in a command are the ones a generator cannot make.
- **A framework rather than a library** — the repo's `main` is kiln's, and the
  application registers into it. Rejected: it inverts control over the
  process, which is exactly the coupling an application repo must not have to
  a library it depends on.

## Decision

**The boilerplate lives in the libraries, and the repo declares its shape rather
than writing it.**

Three levels, in increasing order of how much a repo gives up:

1. **Library, always.** `rn-forge-cli` owns the console conventions, the Typer
   app factory, the standard option set (`--json`, `--dry-run`, `--yes`,
   `--log-level`) and the error-to-exit-code mapping. `rn-forge-commons` owns
   logging configuration, document loading, path guards, hashing and the
   integration protocols. `rn-forge-tooling` owns local state, the template
   engine and the generation engine — which a `python-tool` repo needs and a
   `python-app` repo does not. A repo importing these gets one convention
   instead of inventing a second.

1. **Declared, by default.** A `[cli]` section in `.rn-forge/kiln/config.toml`
   describes the application's *surface* — name, help text, which standard
   option groups it takes, which subcommand namespaces exist and where their
   implementations live. `rn-forge-cli` builds the Typer app from that at
   import time. The repo writes command functions; it never writes app
   construction, flag plumbing, or exit-code handling.

1. **Escape hatch, always available.** A repo that needs an app the library
   cannot describe drops to level 1 and constructs its own, using the same
   primitives. No generated file is involved either way, so dropping down
   costs nothing and is not a fork.

**What this is not.** It is not an application generator: nothing emits a
command module, and D2 is unchanged. The `[cli]` section describes a surface
that already has to be described somewhere; today it is described in imperative
Python that every repo writes slightly differently.

**Boundary.** The `[cli]` section is kiln config, but the thing that reads it is
`rn-forge-cli` — kiln renders it into the repo and never imports it, and
`rn-forge-cli` never learns about archetypes. That keeps
[ADR-0002](0002-the-dependency-graphs.md)'s graph intact: a repo depends on the
library, not on kiln. It also means a `python-app` repo gets the declared
surface without installing Jinja2 or the generation engine.

## Consequences

- A generated `python-app` or `python-tool` repo contains a `main()`, its
  commands, and its tests. Everything else that a CLI needs is a dependency.
- Fixing the flag plumbing is a tooling release, not N commits — the propagation
  property that [ADR-0003](0003-ci-runs-committed-code.md) deliberately gives
  up for CI is available here, because a library is versioned and a workflow
  is not.
- Phase C's package split must be made against this target. The Typer helpers
  and `AppConsole` move to `rn-forge-cli` as one coherent surface;
  `StateStore`, `TemplateEngine` and the generation engine move to
  `rn-forge-tooling`. (The first revision of this ADR put all four in tooling;
  that is what the Phase C review corrected.)
- A declarative surface is a schema, and schemas grow. The mitigation is level
  3: the moment describing an app is harder than writing it, writing it is
  supported and unremarkable.
- This ADR is a target, not a specification. What `[cli]` actually contains is
  settled when the libraries are extracted and the first repos — kiln,
  agentkit, and a `python-app` — are built on them.
- **The acceptance test is a golden repo.** Under
  [ADR-0005](0005-archetypes.md), a claim not demonstrated in a runnable
  golden repo is not demonstrated. `golden-app` must contain a working CLI
  with zero hand-written app construction; if that repo cannot be written,
  this ADR is not ready to be accepted.
