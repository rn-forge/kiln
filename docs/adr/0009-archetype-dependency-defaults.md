# ADR-0009 — An archetype carries a dependency set, and it is enforced

**Status:** accepted

## Context

[ADR-0006](0006-archetypes-and-golden-repos.md) defines an archetype as a repo
*shape*: a layout, a task surface, a CI pipeline. That is half of what an
archetype is for. The other half is what a repo of that shape is *built on* —
the component libraries that mean it does not write the boilerplate again. A
`python-cli` repo that hand-rolls its own console conventions is the right shape
and the wrong repo.

The fleet shows both failure modes:

- **No reuse.** agentkit depends on `jinja2`, `pydantic`, `rich`, `ruamel-yaml`,
  `tomlkit` and `typer` directly, and grew its own `core/{state,config,paths,io}.py`
  — while pykit's commons already held most of it (F12, F17).
- **Reuse without a standard for it.** apollo depends on commons via
  `{ git = "…/pykit", branch = "main", subdirectory = "…" }`. It invented that
  declaration alone, and it is unpinned: what apollo builds changes when pykit's
  main moves, without a single tracked byte in apollo changing.

There is also a mechanical problem. [ADR-0003](0003-the-dependency-graphs.md)
says commons and tooling are the only rn-forge packages a repo may import, and
that the boundary is executable via `.importlinter`. It is not: import-linter
rejects subpackages of external packages, so `rn_forge.kiln` cannot be named as
a forbidden module however the contract is written — verified, both with and
without `rn_forge` installed. The rule as stated has no enforcement.

## Decision

**An archetype's dependency set is part of the archetype**, rendered into
`pyproject.toml` and checked by a generated, committed lint.

| Archetype | Runtime | Dev |
| --- | --- | --- |
| every repo | `rn-forge-commons` | — |
| `python-cli` | + `rn-forge-tooling` | — |
| `python-lib` | `rn-forge-commons` in each distributable that needs it | — |
| `python-web`, `backend = "django"` | + `rn-forge-django` | + `rn-forge-django[codegen]` |
| `python-web`, `backend = "fastapi"` | + `rn-forge-fastapi`, when that package exists | + `rn-forge-fastapi[codegen]` |

`backend` is a choice, not a union: a `python-web` repo gets one framework
package, the one its config names.

`tooling` is a **runtime** dependency of a `python-cli` repo, not a dev one. It
is called the development-layer package because of what it contains — console
and Typer conventions, local state, templates — not because of when it is
installed. For a CLI, that layer *is* the runtime.

The `[codegen]` extra is a **dev** dependency: kiln discovers generators through
the `rn_forge.kiln.generators` entry-point group, so they must be importable in
the environment kiln runs in, and never in the one the application ships.

**Sources are git, and pinned.** pykit publishes GitHub Releases rather than to
PyPI, so an rn-forge dependency is a git source with a `subdirectory`. It must
resolve to a `tag` or a `rev`. A branch source is rejected.

**Enforcement is at the dependency, not the import.**
`scripts/standards/check_rn_forge_deps.py` is generated, committed, stdlib-only,
and reads `pyproject.toml` with `tomllib`. Three rules:

1. every distribution in the archetype's `REQUIRED` list is a runtime dependency
   of at least one distributable in the repo;
2. no `rn-forge-*` distribution outside `ALLOWED` appears anywhere — runtime,
   optional, or dependency group;
3. every rn-forge git source names a `tag` or a `rev`.

Both lists live in the script's `# BEGIN kiln config` header, exactly like the
lists in the other generated checkers, so pykit — which *contains* commons and
cannot depend on it — renders an empty `REQUIRED` and stays compliant.

`.importlinter` keeps the half it can enforce, and gains a rule worth having:
product code may not import `typer`, `jinja2`, `click`, `django` or `fastapi`
**directly**. Those arrive through the rn-forge library that owns them. That is
the import-level expression of the same idea, and it is what would have caught
agentkit's and taskkit's two divergent Typer floors.

## Consequences

- A generated repo starts with the component libraries wired in, which is the
  point of naming archetypes at all. Both golden repos depend on commons and
  *use* it, so the fixture proves the wiring rather than asserting it.
- Every golden repo's `uv sync` now fetches from GitHub. pykit is public, so no
  CI credential is needed, and the pinned tag keeps resolution reproducible.
- The `REQUIRED` list is config, so "every repo depends on commons" is a default
  and not a law of physics. pykit is the standing exception; a repo that wants
  another needs to say so in its own ADR, which is the friction that keeps the
  default meaningful.
- Bumping the pinned tag is a kiln release, not a per-repo decision. That is the
  intended trade: a fleet on one commons version is worth more than each repo
  tracking main.
- kiln's own `REQUIRED` is empty until Phase D, because kiln has no source yet.
  Declaring a dependency nothing imports is the decoration this ADR argues
  against; the entry lands with the code.
