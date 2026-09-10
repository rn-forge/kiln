# ADR-0006 — Judgement is a runbook; repos are created, not migrated

**Status:** accepted

## Context

Two failed shapes, both from the same instinct — automate the judgement.

The first: skills that install things. `go-task-setup` installed a script that
`task lint` then ran, which meant a CI-relevant file's provenance was a skill
someone may or may not have invoked (F8).

The second: `adopt`. A third of kiln's revision-6 specification existed only to
reconcile pre-existing files — `ADOPT`/`ADOPT_CONFLICT` classification, closure
capture, a gate-shrink preflight, a model-delta harness, an inventory script, a
mapping-apply script and a docs-migration runbook (F18). The one existing
implementation, taskkit's, replaced rather than reconciled: `extra_refs`,
`ownership` and `command_overrides` were all empty in apollo after it ran (F4).

### Alternatives considered

- **Build `adopt` properly**, reconciling instead of replacing. Roughly a third
  of the generator's surface, in service of a one-time operation on pre-v1
  repos whose git history nobody needs.
- **Skills that install, with a provenance marker.** Adds a fourth owner to the
  ownership table for files CI runs, in exchange for convenience during setup.
- **Preserve git history through the rebuild** (`git filter-repo`, subtree
  merges). Real work to keep history that has no consumer: these repos are
  pre-v1 and their decisions are being carried as ADRs regardless.

## Decision

**kiln ships no skills.** Judgement lives in kiln's runbooks — prose an agent or
a human reads and acts on, with the decision points named. No skill installs
anything.

**There is no `kiln adopt`.** A repo either was created by `kiln new` or is not
a kiln repo. None of the adopt machinery is built. The one rule worth keeping
from it, `gate.shrunk`, compares the tasks reachable from `validate` against the
archetype's `required_validate` list — no closure capture required.

**Repos are rebuilt from scratch, not migrated.** Git history of pre-v1 repos is
not preserved. What is carried over is decisions, specs, tests and fixtures,
read as prior art; files are not. pykit's package source is the single
exception: it is split at a new package boundary, not rebuilt.

## Consequences

- The generator has one write path instead of two, and no classification that
  exists only for files it did not write.
- Adopting an existing repo means creating a new one and porting source into it.
  For pre-v1 repos that is cheaper than reconciliation and far easier to
  review.
- Anything that genuinely needs judgement — choosing an archetype for an odd
  repo, deciding whether drift is a mistake or a standard that is wrong — is a
  runbook with a decision point, and stays a human's call.
- A repo that is *not* pre-v1 has no supported path in. That is a real gap, and
  the honest answer when it arrives is a new decision, not a hidden `adopt`.
