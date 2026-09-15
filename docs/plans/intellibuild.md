# intellibuild — standalone plan

**Date:** 2026-09-12 · **Status:** not started; built on its own schedule

intellibuild is built with kiln, but it is not part of kiln's releases and does
not gate them. This file holds everything the standardization plan said about
it, so the work can start without re-deriving it.

## What it is

intellibench is superseded by **intellibuild**, a fresh repo rather than a
migration (D41; [ADR-0006](../adr/ADR-0006.md)). intellibench is a donor, never
an adopt target.

**Archetype: `python-web-app`, `framework = fastapi`, `frontend = angular`** —
decided 2026-09-12 (was open question 16). It carries a separately built
frontend package, which is what separates it from `python-web-api`
([ADR-0005](../adr/ADR-0005.md)). pykit's `fastapi-library-plan.md` and its plan
index still say `python-web-api`; they need aligning, and kiln's pykit handoff
says so.

## Prerequisites

- kiln [release-2](../releases/release-2/index.md) has shipped — the
  `python-web-app` + fastapi + angular cell exists and is approved.
- intellibench's `docs2/REFACTOR_PLAN.md` reports complete.

## Steps

1. `kiln new` intellibuild as
   `python-web-app --framework fastapi --frontend angular --docs mkdocs`.
1. `docs2/` lands as `docs/`, with a `context` area added to its seeded
   `_areas.yml` (D44).
1. Repo-local lints stay repo-local and are wired via `[tasks.extra_refs]`:
   `check_brand`, `check_gate_tags`, `check_endpoints`, `check_db_url`,
   `check_e2e_budget`, `check_vocabulary`. Promote one to kiln only when a
   second repo needs it (D34).
1. Port source by hand; `kiln doctor` and `task validate` green; the fresh tree
   replaces the working tree on a branch.
1. Archive intellibench after intellibuild's first release.

What intellibench already contributed to kiln is recorded in
[context §3 and §6](context.md#3-rebuild-not-migrate-the-donors).

## Acceptance

```bash
kiln doctor --all walgreens/intellibuild --json | jq -e '.summary.errors == 0'
(cd walgreens/intellibuild && task validate && uv run lint-imports)
```

## Open questions

1. **Does intellibuild need `ci.provider = ado` from day one, or does it start
   on GitHub Actions and move?** (open question 5). If ADO from day one,
   kiln's deferred [E8](../specs/epics/E8-ado-provider/index.md) must be
   picked up first.
