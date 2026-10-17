# E5 — The web archetypes

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-09-26 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F5.1 — Library sets, and the modules gain the web shapes](F5.1-web-library-sets-and-modules.md) | Closed | release-1 | 3 Closed |
| [F5.2 — `kiln new` end to end for the web archetypes](F5.2-kiln-new-web-end-to-end.md) | Closed | release-1 | 3 Closed |
| [F5.3 — Prove and ship the FastAPI cells](F5.3-shipped-web-cells.md) | Active | release-1 | 1 Active · 2 New · 4 Closed |
| [F5.4 — The Django scaffold](F5.4-django-scaffold.md) | New | deferred | 1 New |

<!-- END derived features -->

Release: [release-1](../../../releases/release-1/index.md) · Phase: E ·
Estimate: 2 weeks

Repo `rn-forge/kiln`. There are no hand-authored goldens: templates are written
directly and approved through the render matrix
([F4.4](../E4-generator/F4.4-render-matrix.md)). The two `fastapi` cells are the
shape the owner's next repositories take, so E5 is built as soon as its
**Depends on** lines hold — with S5.3.1 also before
[F4.4](../E4-generator/F4.4-render-matrix.md),
[F4.6](../E4-generator/F4.6-doctor.md),
[F4.7](../E4-generator/F4.7-import-contracts.md) and
[F4.8](../E4-generator/F4.8-self-hosting.md). The owner reviews the first
rendered web repo before the rest of E4 resumes.

**Dependencies.** F5.1 needs the three remaining concern modules
([S4.3.3–S4.3.5](../E4-generator/F4.3-concern-modules.md)), the scaffold's
dependency lines
([S4.3.7](../E4-generator/F4.3-concern-modules.md#s437-the-scaffold-completes-pyprojecttoml))
and the thin CLI ([S4.5.1, S4.5.2](../E4-generator/F4.5-cli.md)) — not the whole
of E4. F5.3's shipped-cell stories need only the render matrix's
[S4.4.1](../E4-generator/F4.4-render-matrix.md#s441-render-and-validate-every-cell),
which is closed. They do not wait for the goldens to leave, and they do not wait
for `kiln doctor --full` (S4.6.1).

**Upstream.** A web cell's `uv sync` needs every pykit package it renders to
resolve outside the pykit workspace. That is a pin on
[the board](../../index.md#upstream-pins), not pykit work tracked here
([ADR-0009](../../../adr/ADR-0009.md)), and it held on 2026-10-04: the cells
resolve pykit `main` and kiln `feature/v1` remotely. pykit's `FastApiApp` is
adopted in the seeded README by
[S5.3.7](F5.3-shipped-web-cells.md#s537-the-seeded-readme-shows-the-standard-fastapi-module).
The minimal wired FastAPI application — `FastApiApp(AppConfig())`, a router and
a test — is seeded once at `kiln new` by
[S4.9.2](../E4-generator/F4.9-seeded-starter-source.md#s492-fastapi-backend-starter),
and is repo-owned from then on; kiln never renders or re-checks it. A real
product's further code stays repo-owned, and ongoing generation is
[E10](../E10-kiln-generators/index.md). The owner's first `python-web-app` +
`fastapi` repo is that proof, not a kiln cell.

**`[codegen]` is not here.** Neither framework package ships the extra yet (both
have the import fence and nothing behind it). Nothing in E5 renders it; the
dependency check accepts a framework's `[codegen]` extra in a dev group only,
when one appears.

## Acceptance

E5 is done when every feature's acceptance block passes. This block re-proves
the epic end to end afterwards.

```bash
set -euo pipefail
cd rn-forge/kiln
task self:golden:render && task self:golden:validate   # all web cells pass
scratch=$(mktemp -d)
uv run kiln new "$scratch/web" --archetype python-web-app --backend fastapi --frontend angular --docs mkdocs --yes </dev/null
(cd "$scratch/web" && uv sync && pnpm install --frozen-lockfile && task validate && uv run --project "$OLDPWD" kiln doctor .)
```
