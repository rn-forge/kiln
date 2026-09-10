# ADR-0003 — CI runs committed code; kiln is a developer tool

**Status:** accepted

## Context

CI was unowned across the fleet: four pipelines shared nothing, and only one of
them pinned action SHAs or set `permissions:` (F5). agentkit ADR-0021 had
already reached the narrower version of this conclusion: install only what CI
runs.

### Alternatives considered

- **CI installs kiln and renders on the fly.** Every build then depends on a
  private tool being installable, a cold clone is unbuildable, and a generator
  bug becomes a build failure in ten repos at once.
- **Reusable workflows in a shared devops repo**, with a thin caller per repo.
  Re-raised in the Phase B review and re-examined: pinned to a tag it needs
  the same commit in every repo to propagate a fix as `kiln apply` does, and
  adds an external repo dependency at CI time; floated to a branch it
  propagates for free, but that is unpinned CI — the failure apollo already
  had with `branch = "main"`. Its real benefit, a workflow too short to
  hand-edit, is bought more cheaply by a committed composite action.
- **A `forge-ci` repo of reusable workflow fragments** (revision 1). Collapsed
  into the generator in revision 3 and not revived.

## Decision

**All repo-specific logic that CI runs is committed. kiln is a developer-only
generator and freshness checker; CI never installs or invokes it.** CI installs
pinned language toolchains and go-task, then invokes only committed `task`
entrypoints and generated checkers.

- A cold clone builds without kiln, agentkit, `$RNF_HOME`, or a bootstrap
  script.
- Every generated file carries a provenance header naming kiln and its config.
- A script that differs per repo by a list carries that list in a **config
  header block** fenced by `# BEGIN kiln config` / `# END kiln config`. The
  body below the fence is identical in every repo, and
  `tests/support/assert_generated_bodies.py` proves it.
- `.rn-forge/kiln/state.json` is generated and committed, and
  `scripts/standards/check_generated.py` — generated, committed, stdlib-only —
  compares it against the tree. It renders nothing.
- Repeated setup steps live in a committed composite action, not in four copies
  inside one workflow.
- `kiln doctor` additionally renders current templates, to answer the one
  question CI cannot: whether a newer kiln or an edited config *would* change
  an artifact. `kiln apply` refuses unapproved drift.
- Workflows are SHA-pinned with a version comment, set least-privilege
  `permissions:` per job, declare `concurrency:` per ref, and resolve the
  committed lockfile rather than rewriting it. Dependabot watches kiln, not
  the generated workflows.

## Consequences

- CI cannot tell you that kiln has moved on. That is deliberate: staleness is a
  developer's problem, not a build failure in ten repos the day kiln releases.
- The checker must stay stdlib-only, which caps how clever it can get. Good.
- Fixing a workflow means fixing a template and re-applying, so the fix lands
  everywhere — but it lands as N commits, not one. That is the accepted cost
  of every repo being self-contained.
