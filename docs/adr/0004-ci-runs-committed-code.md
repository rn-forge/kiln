# ADR-0004 — CI runs committed code; kiln is a developer tool

**Status:** accepted

## Context

CI was unowned across the fleet: four pipelines shared nothing, and only one of
them pinned action SHAs or set `permissions:` (F5). The tempting fix is to have
CI install the generator and render on the fly. That makes every build depend on
a private tool being installable, makes a cold clone unbuildable, and makes the
generator's own bugs into build failures in every repo at once.

agentkit ADR-0021 had already reached the narrower version of this conclusion:
install only what CI runs.

## Decision

**All repo-specific logic that CI runs is committed. kiln is a developer-only
generator and freshness checker; CI never installs or invokes it.** CI installs
pinned language toolchains and go-task, then invokes only committed `task`
entrypoints and generated checkers.

- A cold clone builds without kiln, agentkit, `$RNF_HOME`, or a bootstrap script.
- Every generated file carries a provenance header naming kiln and the config it
  came from.
- A script that differs per repo by a list carries that list in a **config header
  block** fenced by `# BEGIN kiln config` / `# END kiln config`, rendered from
  the archetype. The body below the fence is identical in every repo, and
  `tests/support/assert_generated_bodies.py` proves it.
- `.rn-forge/kiln/state.json` is generated and committed: per artifact, its
  repo-relative path, kind, SHA-256, and (for blocks) the exact fence markers,
  plus `kiln_version` and `config_hash`. It excludes itself, so it never hashes
  itself.
- `scripts/standards/check_generated.py` is a generated, committed, stdlib-only
  checker that compares that baseline against the tree. It renders nothing.
- `kiln doctor` additionally renders current templates, to answer the one
  question CI cannot: whether a newer kiln or an edited config *would* change an
  artifact. `kiln apply` refuses unapproved drift.
- Workflows are SHA-pinned with a version comment, set least-privilege
  `permissions:` per job, and declare `concurrency:` per ref. Dependabot watches
  kiln, not the generated workflows.

## Consequences

- CI cannot tell you that kiln has moved on. That is deliberate: staleness is a
  developer's problem, not a build failure in ten repos the day kiln releases.
- The checker must stay stdlib-only, which caps how clever it can get. Good.
- Fixing a workflow means fixing a template and re-applying, so the fix lands
  everywhere instead of in the repo that noticed.
