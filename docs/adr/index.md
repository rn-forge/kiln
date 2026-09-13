# Decisions

kiln's decision log: the choices behind the repository standard and behind kiln
itself, each with the alternatives rejected. The specification those choices
produced — the verb list, the ownership table, the dependency sets, the config
schema — lives in [the standard-repo reference](../reference/standard-repo.md),
which kiln renders into every repo it generates as `.rn-forge/kiln/standard.md`.

An ADR states a decision that should outlive the spec built on it. If a page
here starts listing things, it has become a spec and belongs in the reference.
When a decision is refined, the ADR that owns the topic is updated in place so
the log stays one clean list; a genuinely new topic gets the next number.

Open questions are not ADRs: they live on the epic or feature they block, under
[specs](../specs/index.md), and become an ADR — or a change to one — when
answered. The plan's `D<n>` decision numbers map to these ADRs in
[context §2.2](../plans/context.md#22-decisions).

- [ADR-0001 — One owner per managed file, or per fenced block](0001-ownership.md)
- [ADR-0002 — Two dependency graphs, and an executable boundary](0002-the-dependency-graphs.md)
- [ADR-0003 — CI runs committed code; kiln is a developer tool](0003-ci-runs-committed-code.md)
- [ADR-0004 — The `.rn-forge/` umbrella, and asserted, committed configuration](0004-the-rn-forge-umbrella.md)
- [ADR-0005 — An archetype is a shape, a library set, and a rendered, approved template set](0005-archetypes.md)
- [ADR-0006 — Judgement is a runbook; repos are created, not migrated](0006-runbooks-not-skills.md)
- [ADR-0007 — The task vocabulary is closed, and the gate cannot shrink](0007-task-vocabulary.md)
- [ADR-0008 — Type-check with pyright in strict mode, not mypy](0008-pyright-strict-not-mypy.md)
- [ADR-0009 — The libraries own the boilerplate; the CLI is declared, not written](0009-tooling-owns-the-boilerplate.md)
  *(proposed)*
- [ADR-0010 — The checkers become a versioned package; only their inputs stay committed](0010-checkers-are-a-package.md)
- [ADR-0011 — kiln is one distribution of modules under one contract](0011-kiln-is-modules-under-one-contract.md)
