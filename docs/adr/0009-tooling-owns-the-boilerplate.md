# ADR-0009 — Tooling owns the boilerplate; the CLI is declared, not written

**Status:** proposed

*Proposed rather than accepted because `rn-forge-tooling` does not exist yet: it
is extracted in Phase C. This ADR is what that extraction is aimed at, so that
the package boundary is chosen against a known target instead of being
discovered afterwards.*

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
  process, which is exactly the coupling `python-cli` repos must not have to a
  developer-tooling package.

## Decision

**The boilerplate lives in `rn-forge-tooling` as a library, and the repo
declares its shape rather than writing it.**

Three levels, in increasing order of how much a repo gives up:

1. **Library, always.** `rn-forge-tooling` owns the console conventions, the
   Typer app factory, the standard option set (`--json`, `--dry-run`, `--yes`,
   `--log-level`), the error-to-exit-code mapping, local state and the
   template engine. `rn-forge-commons` owns logging configuration, document
   loading, path guards, hashing and the integration protocols. A repo
   importing these gets one convention instead of inventing a second.

1. **Declared, by default.** A `[cli]` section in `.rn-forge/kiln/config.toml`
   describes the application's *surface* — name, help text, which standard
   option groups it takes, which subcommand namespaces exist and where their
   implementations live. Tooling builds the Typer app from that at import
   time. The repo writes command functions; it never writes app construction,
   flag plumbing, or exit-code handling.

1. **Escape hatch, always available.** A repo that needs an app tooling cannot
   describe drops to level 1 and constructs its own, using the same
   primitives. No generated file is involved either way, so dropping down
   costs nothing and is not a fork.

**What this is not.** It is not an application generator: nothing emits a
command module, and D2 is unchanged. The `[cli]` section describes a surface
that already has to be described somewhere; today it is described in imperative
Python that every repo writes slightly differently.

**Boundary.** The `[cli]` section is kiln config, but the thing that reads it is
tooling — kiln renders it into the repo and never imports it, and tooling never
learns about archetypes. That keeps [ADR-0002](0002-the-dependency-graphs.md)'s
graph intact: a repo depends on tooling, not on kiln.

## Consequences

- A generated `python-cli` repo contains a `main()`, its commands, and its
  tests. Everything else that a CLI needs is a dependency.
- Fixing the flag plumbing is a tooling release, not N commits — the propagation
  property that [ADR-0003](0003-ci-runs-committed-code.md) deliberately gives
  up for CI is available here, because a library is versioned and a workflow
  is not.
- Phase C's package split must be made against this target. In particular the
  Typer helpers, `AppConsole`, `StateStore` and `TemplateEngine` move to
  tooling as a coherent surface rather than as individually relocated symbols.
- A declarative surface is a schema, and schemas grow. The mitigation is level
  3: the moment describing an app is harder than writing it, writing it is
  supported and unremarkable.
- This ADR is a target, not a specification. What `[cli]` actually contains is
  settled when tooling is extracted and the first two repos — kiln and
  agentkit — are built on it.
