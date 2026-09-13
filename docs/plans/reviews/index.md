# Reviews

Review passes over a phase's output, kept verbatim. They are not corrected after
the fact: what a reviewer actually said is the useful record, and what was done
about it is in [context §7](../context.md#7-review-outcomes) and the ADRs.

## Phase B — the canon and the golden repos

- [Owner review](phase-b-owner.md) — the ADR set reads as spec rather than
  decision; the CI model; archetype naming; instruction-file drift; Markdown
  formatting; how much boilerplate the archetypes should carry.
- [codex review](phase-b-codex.md) — eight defects in the golden repos, from a
  published package that could not resolve its own dependency to a release
  that could never be retried.

All items from both are addressed. The outcome table is
[context §7.1](../context.md#71-what-the-phase-b-review-changed), and the work
was [E1](../../specs/epics/E1-canon-and-golden-repos/index.md).

## Phase C — the package boundary

- [Owner review](phase-c-owner.md) — how the archetypes should be designed,
  defined and used: what a library repo, a batch, an installable tool, a web
  API and a full web app each are, and which capabilities belong to which.
- [codex review](phase-c-codex.md) — the commons/tooling boundary reopened, kiln
  policy carried into a general-purpose library, and fourteen implementation
  findings.

Both landed on the same seam from opposite directions. The outcome table is
[context §7.3](../context.md#73-what-the-phase-c-review-changed), and the work
was [E2](../../specs/epics/E2-layer-split-and-golden-rename/index.md).
