# E5 — The web archetypes

**Status:** in progress · **Release:**
[release-2](../../../releases/release-2/index.md) · **Phase:** E · **Estimate:**
2 weeks

Repo `rn-forge/kiln`. There are no hand-authored goldens: templates are written
directly and approved through the render matrix
([ADR-0005](../../../adr/ADR-0005.md)). The two `fastapi` cells are the shape
the owner's next repositories take, so E5 is built as soon as its **Depends on**
lines hold — with S5.3.1 also before
[F4.4](../E4-generator/F4.4-render-matrix.md),
[F4.6](../E4-generator/F4.6-doctor.md),
[F4.7](../E4-generator/F4.7-import-contracts.md) and
[F4.8](../E4-generator/F4.8-self-hosting.md) — while release-2 still ships after
release-1. The owner reviews the first rendered web repo before the rest of E4
resumes.

**Dependencies.** F5.1 needs the three remaining concern modules
([S4.3.3–S4.3.5](../E4-generator/F4.3-concern-modules.md)), the scaffold's
dependency lines
([S4.3.7](../E4-generator/F4.3-concern-modules.md#s437-the-scaffold-completes-pyprojecttoml))
and the thin CLI ([S4.5.1, S4.5.2](../E4-generator/F4.5-cli.md)) — not the whole
of E4. F5.3's scaffold-gate fixes can follow F5.2 immediately; its shipped-cell
stories need the render matrix (F4.4).

**Upstream.** `rn-forge-fastapi` is implemented in pykit (`3e80dbd`). Its plan's
Phase 8 acceptance is a *wired application* — problem handlers, a paginated
route, the health router — which is repo-owned code under `src/**` that kiln
never renders ([ADR-0011](../../../adr/ADR-0011.md)); the owner's first
`python-web-app` + `fastapi` repo is that proof, not a kiln cell. What does gate
a web cell's `uv sync` is resolvable pins: `rn-forge-web`, `rn-forge-django` and
`rn-forge-fastapi` pin `rn-forge-commons-v0.5.0` and `rn-forge-web-v0.1.0`, and
neither tag exists (checked 2026-09-16; pykit's tags stop at
`rn-forge-commons-v0.2.2` and `rn-forge-django-v0.2.2`). Until pykit cuts those
tags, or pins those three packages to `feature/upgrade` as `rn-forge-cli` and
`rn-forge-tooling` do, S5.1.1's rendered set cannot be synced outside the pykit
workspace. This is on the
[board's upstream table](../../index.md#upstream-work-owned-by-pykit).

**`[codegen]` is not here.** Neither framework package ships the extra yet (both
have the import fence and nothing behind it). Nothing in E5 renders it; the
dependency check accepts a framework's `[codegen]` extra in a dev group only,
when one appears.

## Features

| ID | Feature | Depends on |
| -- | -- | -- |
| [F5.1](F5.1-web-library-sets-and-modules.md) | Library sets, and the modules gain the web shapes | S4.3.3–S4.3.5, S4.3.7, S4.5.1, S4.5.2; resolvable pykit pins |
| [F5.2](F5.2-kiln-new-web-end-to-end.md) | `kiln new` end to end for the web archetypes | F5.1; S5.2.1 on S5.2.2; Django deferred |
| [F5.3](F5.3-shipped-web-cells.md) | Prove and ship the FastAPI cells | S5.3.1 on F5.2; S5.3.2–S5.3.3 on F4.4; S5.3.4 on S5.3.3 |

## Acceptance

E5 is done when every feature's acceptance block passes. This block re-proves
the epic end to end afterwards.

```bash
set -euo pipefail
cd rn-forge/kiln
task self:golden:render && task self:golden:validate   # all web cells pass
scratch=$(mktemp -d)
uv run kiln new "$scratch/web" --archetype python-web-app --backend fastapi --frontend angular --docs mkdocs --yes </dev/null
(cd "$scratch/web" && uv sync && pnpm install --frozen-lockfile && task validate && uv run --project "$OLDPWD" kiln doctor)
```
