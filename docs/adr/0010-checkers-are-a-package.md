# ADR-0010 — The checkers become a versioned package; only their inputs stay committed

**Status:** accepted

*Accepted before the code exists. The package cannot be built until Phase D, but
the decision has to be settled now: it changes where Phase C puts the docs
checkers, and deciding it after `kiln apply` has copied 1,454 lines into ten
repos is the expensive order.*

## Context

[ADR-0003](0003-ci-runs-committed-code.md) decided that CI runs committed code
and never installs the generator. The implementation reads that as *the checkers
themselves are committed*, and a generated repo therefore carries **1,454
lines** of Python across seven scripts:

| Script | Lines | Per-repo variation |
| -- | -- | -- |
| `scripts/docs/check_structure.py` | 291 | none |
| `scripts/docs/_common.py` | 172 | none |
| `scripts/docs/check_docs.py` | 158 | none |
| `scripts/docs/gen_nav.py` | 154 | none |
| `scripts/task/check_task_layout.py` | 198 | a list of task names |
| `scripts/standards/check_rn_forge_deps.py` | 191 | three lists |
| `scripts/standards/check_generated.py` | 151 | none |
| `scripts/ci/check_ci_entrypoint.py` | 139 | two lists |

Four of the seven vary not at all. The other three vary by lists that are
already config, and every one of those lists is *derivable* from
`.rn-forge/kiln/config.toml` — the archetype, the docs profile, the CI provider,
the workspace members.

So the fleet is about to acquire ten copies of the same 1,454 lines, kept
byte-identical by a test that exists solely to notice when they stop being
identical. That is F2 — the four forks of `check_ci_entrypoint.py` that started
this whole plan — reproduced deliberately, at ten times the scale, with a
regression test standing where the divergence used to be.

The distinction ADR-0003 was actually protecting is **generation**, not
verification: CI must never render a template, because then a cold clone depends
on a private generator and a generator bug becomes ten simultaneous build
failures. A checker renders nothing. It reads committed bytes and compares them.
That difference was collapsed in the original decision, and it is the whole
question here.

### Alternatives considered

- **Keep the status quo: commit every checker.** Maximum self-containment — a
  cold clone needs only the pinned interpreter for `check_generated.py`. But a
  cold clone already runs `uv sync` to get ruff, pyright, pytest and mkdocs
  before `task validate` can do anything, so "no dependencies" was never true
  of the gate as a whole. What it buys, in practice, is that a fix to a
  checker is ten commits instead of a version bump.
- **Put the checkers in `rn-forge-commons` or `rn-forge-tooling`.** Rejected on
  [ADR-0002](0002-the-dependency-graphs.md)'s own table: commons is
  runtime-neutral and tooling is generic local-development mechanism, while
  "every managed artifact matches the committed state baseline" and "these are
  the tools a workflow may not invoke" are *rn-forge repository policy*.
  Policy in a runtime-neutral library is how `forge-core` went wrong.
- **One distribution, `rn-forge-kiln[checks]`.** Extras add dependencies; they
  cannot subtract modules. CI would have the generator's code importable and
  merely unused, which is a weaker guarantee than ADR-0003 gives today, in
  exchange for one fewer distribution.
- **Name it `rn-forge-kiln-devops`, and widen it to hold reusable scripts and
  templates.** Rejected, and the name is the reason. `checks` names a role
  that can be falsified — a checker renders nothing — and that is the property
  CI relies on when it installs the package at all. `devops` names a domain,
  and a domain excludes nothing: every task a repo runs in CI is devops,
  generation included, so a package under that name has no principled ground
  on which to refuse a template. Ship templates in it and ADR-0003 degrades
  from *CI cannot render* to *CI happens not to*, which is the same weakening
  the `rn-forge-kiln[checks]` extra was rejected for. The name would also be
  inaccurate: of the four checkers that stay, only `check_ci_entrypoint` is
  about CI, and all four run in a developer's `task validate` before they ever
  run in a pipeline. The want underneath it is real and already housed —
  reusable *mechanism* is `rn-forge-tooling`
  ([ADR-0009](0009-tooling-owns-the-boilerplate.md)), reusable *templates* are
  kiln's and arrive generated and committed, and a shared devops repo of CI
  assets was examined and rejected on its own terms (D45).
- **Config headers stay, bodies move — a ten-line generated shim per checker.**
  Keeps the "list is config in the repo" property that fixed F2 while removing
  the duplicated logic. Rejected as an intermediate: the lists are already in
  `config.toml`, so the shim would restate config that the package can read
  directly.

## Decision

**Split verification from generation into two distributions, and commit only the
inputs.**

- **`rn-forge-kiln`** — the CLI, the templates, the rendering engine. A
  developer tool. Never installed in CI, exactly as
  [ADR-0003](0003-ci-runs-committed-code.md) says.
- **`rn-forge-kiln-checks`** — the checkers, and nothing else. No templates, no
  rendering, no Jinja. A dev dependency of every archetype, pinned like any
  other ([ADR-0005](0005-archetypes.md)). It exposes one console script per
  check plus an aggregate, and `tasks/quality.yml` calls those instead of
  `python scripts/...`.

An `.importlinter` contract forbids `rn_forge.kiln.checks` from importing
`rn_forge.kiln`, so the split cannot quietly collapse.

**Both distributions live in the kiln repository**, which is therefore a
`python-lib` workspace with two packages rather than the `python-cli` single
package it is a hand-copy of today. Two repositories would put a repo boundary
where a package boundary is what is needed, and the import contract above holds
inside one workspace at least as well as across two.

**What stays committed** is exactly what CI must be able to trust without
re-deriving it:

- `.rn-forge/kiln/state.json` — the baseline. Unchanged: generated, committed,
  carrying `schema_version` so a checker can refuse a state it does not
  understand.
- `.rn-forge/kiln/config.toml` — the inputs the per-repo lists derive from.
- `.rn-forge/kiln/standard.md` — the rendered canon.

**What stops being committed** is the checker logic. `scripts/` disappears from
a generated repo.

**Where each checker goes.** The split is by what the code is about, not by
convenience:

| Checker | Home | Why |
| -- | -- | -- |
| `check_docs`, `check_structure`, `gen_nav`, `_common` | `rn-forge-tooling` | validating a docs tree against a declared area model is a generic local-development mechanism; no rn-forge policy in it |
| `check_generated`, `check_rn_forge_deps`, `check_task_layout`, `check_ci_entrypoint` | `rn-forge-kiln-checks` | each encodes rn-forge repository policy — the state model, the dependency contract, the vocabulary, the entrypoint rule |

That is why this ADR must be settled before Phase C: the docs checkers are part
of what Phase C extracts into tooling, or they are not.

## Consequences

- A generated repo loses 1,454 lines it never reads. `scripts/` exists only for
  a repo's *own* lints, wired through `[tasks.extra_refs]`.
- `tests/support/assert_generated_bodies.py` and its test lose their subject and
  are deleted. The property they defended — one body everywhere — becomes true
  by construction rather than by assertion.
- Fixing a checker is a release and a pin bump, not ten commits. This is the
  propagation property ADR-0003 deliberately gives up for *workflows*; it is
  available here because a library is versioned and a workflow file is not.
- **`check_generated.py` stops being stdlib-only**, and the claim that a cold
  clone can run it with the pinned interpreter alone goes with it. The honest
  restatement: CI installs pinned *dev dependencies* and then runs committed
  configuration against them, and never runs a generator. State that plainly
  rather than quietly weakening the old sentence.
- Version skew becomes possible — a repo pinned to checks `1.2` while kiln `1.3`
  writes a state file it does not understand. `schema_version` already exists
  for this; the checks package must fail loudly on an unknown one rather than
  guessing.
- **kiln's own repo becomes `python-lib`**, since it ships two distributions.
  That is a real change to its skeleton and to which golden repo it is a copy
  of; it lands in Phase D, when kiln regenerates itself, and until then the
  hand-copied `python-cli` skeleton stays as it is.
- The bootstrap problem is the same one kiln already has: the checks package
  cannot check itself against a version that does not exist yet. It is solved
  the same way — an empty required list until the release exists.
