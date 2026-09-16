# Decisions

kiln's decision log: the choices behind the repository standard and behind kiln
itself, each with the alternatives rejected. The specification those choices
produced — the verb list, the ownership table, the dependency sets, the config
schema — lives in [the standard-repo reference](../reference/standard-repo.md),
which kiln renders into every repo it generates as `.rn-forge/kiln/standard.md`.

An ADR states a decision that should outlive the spec built on it. If a page
here starts listing things, it has become a spec and belongs in the reference.
When a decision changes, the ADR that owns the topic is revised in place: it
keeps its number, its Decision states what is true now, and what it replaced
moves under its `## History`. The log stays one clean list, and every link keeps
pointing at one file. A genuinely new topic gets the next number.

Open questions are not ADRs: they live on the epic or feature they block, under
[specs](../specs/index.md), and become an ADR — or a change to one — when
answered. The plan's `D<n>` decision numbers map to these ADRs in
[context §2.2](../plans/context.md#22-decisions).

- [ADR-0001 — One owner per managed file, or per fenced block](ADR-0001.md)
- [ADR-0002 — Two dependency graphs, and an executable boundary](ADR-0002.md)
- [ADR-0003 — CI runs committed code; kiln is a developer tool](ADR-0003.md)
- [ADR-0004 — The `.rn-forge/` umbrella, and asserted, committed configuration](ADR-0004.md)
- [ADR-0005 — An archetype is a shape, a library set, and a rendered, approved template set](ADR-0005.md)
- [ADR-0006 — No skills; one-time judgement is a kiln prompt; repos are created, not migrated](ADR-0006.md)
- [ADR-0007 — The task vocabulary is closed, and the gate cannot shrink](ADR-0007.md)
- [ADR-0008 — Type-check with pyright in strict mode, not mypy](ADR-0008.md)
- [ADR-0009 — The libraries own the boilerplate; the CLI is declared, not written](ADR-0009.md)
- [ADR-0010 — kiln is a pinned dev dependency, and CI runs it read-only](ADR-0010.md)
- [ADR-0011 — kiln is one distribution of modules under one contract](ADR-0011.md)
