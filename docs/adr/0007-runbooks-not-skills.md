# ADR-0007 — Judgement is a runbook; repos are created, not migrated

**Status:** accepted

## Context

Two failed shapes, both from the same instinct — automate the judgement.

The first: skills that install things. `go-task-setup` installed a script that
`task lint` then ran, which meant a CI-relevant file's provenance was a skill
someone may or may not have invoked (F8). agentkit ADR-0021 had already drawn the
opposite line.

The second: `adopt`. A third of kiln's revision-6 specification existed only to
reconcile pre-existing files — `ADOPT`/`ADOPT_CONFLICT` classification, closure
capture, a gate-shrink preflight, a model-delta harness, an inventory script, a
mapping-apply script, and a docs-migration runbook (F18). And the one existing
implementation of adopt, taskkit's, replaced rather than reconciled: `extra_refs`,
`ownership` and `command_overrides` were all empty in apollo after it ran (F4).

## Decision

**kiln ships no skills.** Judgement lives in kiln's runbooks — prose an agent or
a human reads and acts on, with the decision points named. No skill installs
anything.

**There is no `kiln adopt`.** A repo either was created by `kiln new` or is not a
kiln repo. None of the adopt machinery is built. The one rule worth keeping from
it, `gate.shrunk`, compares the tasks reachable from `validate` against the
archetype's `required_validate` list — no closure capture required.

**Repos are rebuilt from scratch, not migrated.** Git history of pre-v1 repos is
not preserved. What is carried over is decisions, specs, tests and fixtures, read
as prior art; files are not. pykit's package source is the single exception: it
is split at a new package boundary, not rebuilt.

## Consequences

- The generator has one write path instead of two, and no classification that
  exists only for files it did not write.
- Adopting an existing repo means creating a new one and porting source into it.
  For pre-v1 repos that is cheaper than reconciliation and much easier to review.
- Anything that genuinely needs judgement — choosing an archetype for an odd
  repo, deciding whether drift is a mistake or a standard that is wrong — is a
  runbook with a decision point, and stays a human's call.
