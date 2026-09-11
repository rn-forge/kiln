# Reviews

Review passes over a phase's output, kept verbatim. They are not corrected after
the fact: what a reviewer actually said is the useful record, and what was done
about it is in the plan's own §0.6/§0.8 and decision log.

## Phase B — the canon and the golden repos

- [Owner review](phase-b-owner.md) — the ADR set reads as spec rather than
  decision; the CI model; archetype naming; instruction-file drift; Markdown
  formatting; how much boilerplate the archetypes should carry.
- [codex review](phase-b-codex.md) — eight defects in the golden repos, from a
  published package that could not resolve its own dependency to a release
  that could never be retried.

All items from both are addressed. The outcome table is
[§0.6 of the plan](../standardization-plan.md).

## Phase C — the package boundary

- [Owner review](phase-c-owner.md) — how the archetypes should be designed,
  defined and used: what a library repo, a batch, an installable tool, a web
  API and a full web app each are, and which capabilities belong to which.
- [codex review](phase-c-codex.md) — the commons/tooling boundary reopened, kiln
  policy carried into a general-purpose library, and fourteen implementation
  findings.

Both landed on the same seam from opposite directions. The outcome table is
[§0.8 of the plan](../standardization-plan.md), and the work is Phase C.2.
