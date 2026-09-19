# E1 — The canon and the hand-authored golden repos

**Status:** done · **Shipped:** 2026-09-09 (`fe7bc70`, review `e1c4abb`) ·
**Phase:** B

New repo `rn-forge/kiln`, no generator code. Its own skeleton was bootstrapped
by **hand-copying the `python-cli` golden repo** once it existed; kiln
regenerates itself in [F4.8](../E4-generator/F4.8-self-hosting.md). Two
deliverables, both reviewed by the owner before Phase C started.

> The archetype names below are the revision-8 ones; `golden/python-cli` was
> renamed to `golden/python-tool` and joined by `golden/python-app` in
> [E2](../E2-layer-split-and-golden-rename/index.md). Left as written, as the
> record of what was built.

## Features

| ID | Feature | Status |
| -- | -- | -- |
| F1.1 | **Docs — the canon.** `docs/adr/0001…0008.md`, each ≤ 1 page, Context / Decision / Consequences, harvested from the donors (cite the donor ADR in Context). `docs/reference/standard-repo.md`. `docs/architecture/workspace.md`. `docs/runbooks/creating-a-repo.md`. Move the plan into kiln's `docs/plans/` and leave a one-line pointer at `rn-forge/STANDARDIZATION-PLAN.md` (the plan has since been retired; see [context](../../../plans/context.md)). | done |
| F1.2 | **Harvest inventory.** Before writing golden files, for each donor script or lint, one row — donor path, behaviour kept, behaviour dropped, target golden path. The review artifact for "everything common and worth carrying over". Now [context §6](../../../plans/context.md#6-harvest-inventory). | done |
| F1.3 | **Golden repos** under `tests/fixtures/golden/`: `python-cli/` (name `golden-cli`), `python-lib/` (`golden-lib`, two trivial packages), `python-django-ng/` and `python-fastapi-ng/` (`golden-web`; the web fixtures may ship in Phase E if they slow this phase). Each a complete repo with `docs.profile = mkdocs` and `ci.sonar = true`, hand-written provenance headers reading `kiln golden`, a hand-written `state.json`, a one-function package with one test, and a `.rn-forge/kiln/standard.md` rendered by hand from the spec. Scripts written **once**, in `python-cli`, and copied byte-identical (below the config header) into the others. | done (the web goldens moved to [E5](../E5-web-archetypes/index.md)) |
| F1.4 | `tests/support/assert_generated_bodies.py` — strips provenance and the `# BEGIN kiln config` … `# END kiln config` header, prints each body's SHA-256, fails unless all supplied files share one body. | done (deleted by [F4.1](../E4-generator/F4.1-checks-by-module.md)) |
| F1.5 | Review loop with the owner: read every golden file as if it were the finished repo. Changes go into the golden repo, never "later in the template". | done |

## Outcome

Reviewed by the owner and by codex; every item from both is addressed. What each
review changed is
[context §7.1–7.2](../../../plans/context.md#7-review-outcomes); the reviews
themselves are in [plans/reviews](../../../plans/reviews/index.md). The ADR set
was restructured and specifications moved to the reference (D48), archetypes
renamed (D47, since superseded), CI kept generated with a composite action
(D45), and shared CLI design proposed.

Risk carried by this epic, and its guard: *golden repos reviewed too lightly
because they look like fixtures* — the acceptance runs them as real repos, and
the owner review gate was explicit on the critical path.

## Acceptance (as run)

```bash
cd rn-forge/kiln
uv run --group docs mkdocs build --strict
test -f docs/adr/ADR-0006.md && test -f docs/reference/standard-repo.md && test -f docs/plans/harvest.md
for g in tests/fixtures/golden/python-cli tests/fixtures/golden/python-lib; do
  (cd "$g" && uv sync && task validate && uv run python scripts/standards/check_generated.py . \
     && python scripts/ci/check_ci_entrypoint.py . && python scripts/task/check_task_layout.py . \
     && uv run --group docs mkdocs build --strict) || echo "FAIL $g"
done
uv run python tests/support/assert_generated_bodies.py --relative-path scripts/ci/check_ci_entrypoint.py tests/fixtures/golden/*
uv run python tests/support/assert_generated_bodies.py --relative-path scripts/standards/check_generated.py tests/fixtures/golden/*
actionlint tests/fixtures/golden/*/.github/workflows/*.yml
```
