# ADR-0006 — Archetypes, golden repos, and the docs profile

**Status:** accepted

## Context

Repo shape varies along two independent axes: what the repo *is* (one CLI
package, a workspace of libraries, an API plus a frontend) and whether it
publishes a docs site. Encoding both in one dimension would multiply the
template set; encoding neither leaves every repo hand-shaped, which is where the
fleet started.

Templates also have a review problem. A template is reviewed as a diff of
placeholders, which is exactly the form in which a missing gate or a wrong pin is
hardest to see — the fleet's four divergent pipelines were all reviewed as
templates or as diffs at some point.

## Decision

**Three archetypes for v1**, asserted in config:

| Archetype | Shape | Prior art | Golden fixture | Release tag |
| --- | --- | --- | --- | --- |
| `python-cli` | one uv package, `src/` layout, pytest/ruff/pyright at root | agentkit | `golden/python-cli` | `v<version>` |
| `python-lib` | uv workspace of published packages; per-package verify and release | pykit | `golden/python-lib` | `<package>-v<version>` |
| `python-web` | uv workspace + FastAPI or Django + pnpm frontend (`web_runner = nx \| pnpm`), one MkDocs site over both | intellibench, apollo | `golden/python-web-nx`, `-pnpm` | `v<version>` |

**Docs profile is orthogonal to archetype**: `mkdocs` seeds the full area model
(architecture, guides, runbooks, reference, releases, specs, adr — from
agentkit's `_areas.yml`, E17); `external` generates nothing and records
`external_url` in the instructions block; `none` generates nothing. Repos extend
their own `_areas.yml` ([ADR-0002](0002-the-ownership-table.md)).

**Golden repos are the source of truth for templates.** Each golden fixture is a
complete, hand-authored, *runnable* repo: `uv sync` and `task validate` pass in
it standalone, its workflows lint, its docs site builds `--strict`, and its
committed checkers run. They are reviewed as if they were the finished product
*before* any generator code exists. The templates are then the golden output
parameterized, and the snapshot tests assert `render(golden config) == golden
bytes`, with the provenance version rendered as the literal `golden`.

**A template change that is not first made in the golden repo is a bug.**

**Scaffolding shells out.** `kiln new` runs `uv init`, `pnpm create`, `nx g` and
then reconciles the result. kiln never templates another tool's scaffold output.

## Consequences

- Review happens on real files, in a repo a reviewer can run.
- Adding an archetype is a template set plus a golden repo — real work, but
  bounded, and reviewable the same way.
- The golden repos must be kept green, which costs a `uv sync` per fixture in
  kiln's own CI. That cost is the point: it is the only proof that the templates
  produce a working repo.
- Snapshot tests are byte-exact, so a whitespace change in a template is a
  failing test until the golden repo agrees. That is the intended pressure.
