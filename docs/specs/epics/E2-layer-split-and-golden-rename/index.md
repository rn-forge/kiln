# E2 — The layer split lands in the goldens

**Status:** done · **Shipped:** 2026-09-12 (`afcfa07`) · **Phase:** C.2 (kiln
half)

Repos `rn-forge/pykit` (`feature/upgrade`) and `rn-forge/kiln` (`feature/v1`).
This is what the Phase C review produced
([context §7.3](../../../plans/context.md#73-what-the-phase-c-review-changed)).
The executable form of the pykit half lived in pykit's
`docs/plans/commons-upgrade-plan.md`, at the **"Part D — resume here"** marker;
pykit's Phase A, Phase C and the pykit steps of C.2 are pykit's own record — see
[upstream work owned by pykit](../../index.md#upstream-work-owned-by-pykit).

**Order mattered.** Correctness first, because the defects were in the code
about to be moved; then the split; then the re-layout; then the consumers.

## Features

| ID | Feature | Owner | Status |
| -- | -- | -- | -- |
| F2.1 | Defect fixes F1–F6 in pykit, before anything moves | pykit | done |
| F2.2 | Split the development layer: `rn-forge-cli` + `rn-forge-tooling` (D52; [shared CLI integration](../E3-realign-goldens-and-canon/index.md#shared-cli-design)) | pykit | done |
| F2.3 | Extract the docs policy from tooling (A2) — the policy object is supplied by [F4.1](../E4-generator/F4.1-checks-by-module.md) | pykit | done |
| F2.4 | Re-layout all three packages (D55) | pykit | done |
| F2.5 | F10–F13 while the code is open | pykit | done |
| F2.6 | F7 — CI: cli and tooling in pykit's package verification, `lint-imports` as a required gate | pykit | done |
| F2.7 | F9 + F14 — release contract and instructions | pykit | done |
| F2.8 | **Rename the golden repos and add the missing ones (D53).** `golden/python-cli` → `golden/python-tool`; a new `golden/python-app`. `golden/python-lib` unchanged. Update kiln's own `.rn-forge/kiln/config.toml` to `python-tool`, re-render `.rn-forge/kiln/standard.md`, and **re-seed `state.json`**. | kiln | done |
| F2.9 | **Close Phase C's addendum (F8)** — cut the first `rn-forge-cli` and `rn-forge-tooling` releases and re-point every pin at a tag | kiln + pykit | **deferred**; now [E7](../E7-pykit-release-pin-flip/index.md) |
| F2.10 | **Prove declarative CLI construction.** `golden/python-app` contains a working CLI with **zero hand-written app construction** | kiln | done |

### F2.9 — as it stood when deferred

The `REQUIRED`/`ALLOWED` headers and the dependency lines were already in place,
and the golden repos already exercised all three libraries. What was not done,
and was held back on purpose, is the *pin*: every rn-forge requirement names
pykit's published `feature/upgrade` branch rather than a tag, so that upgrades
found while exercising the golden repos land without re-cutting a release. A
branch pin satisfies `check_rn_forge_deps.py` — `git+…@<ref>` is a ref — and
`uv.lock` records the resolved commit, so the build is reproducible meanwhile.

### F2.10 — outcome

`src/golden_app/cli.py` is one line — `app = CliApp.from_config(...)` — with
`[project.scripts]` pointing at it and no `main()`; the surface is the `[cli]`
table in `.rn-forge/kiln/config.toml`; `commands.py` holds one function with no
Typer import, which `.importlinter` enforces. `golden/python-tool` is built the
same way, and additionally exercises `rn-forge-tooling` by rendering its
greeting through `TemplateEngine`. This supplied the initial D49 proof;
[E3](../E3-realign-goldens-and-canon/index.md#shared-cli-design) records the
subsequent API integration.

Since then pykit plan Part E reshaped `rn-forge-cli` (deleted `declare()`, moved
`console` to commons), which put the goldens behind pykit — that is
[E3](../E3-realign-goldens-and-canon/index.md).

## Acceptance (as run)

```bash
cd rn-forge/pykit
uv sync --all-extras
uv run pytest -q                      # including the new tests for F1–F6
uv run ruff check . && uv run ruff format --check . && uv run pyright
uv run lint-imports                   # commons ⊅ cli ⊅ tooling, + the codegen fence
! rg -q 'rn_forge\.(cli|tooling)' packages/rn-forge-commons/src
! rg -q 'rn_forge\.tooling' packages/rn-forge-cli/src
! rg -q "'adr'|'releases'|specs/epics" packages/rn-forge-tooling/src/rn_forge/tooling/docs/structure.py

cd ../kiln
for g in tests/fixtures/golden/python-app tests/fixtures/golden/python-tool tests/fixtures/golden/python-lib; do
  (cd "$g" && uv sync && task validate) || echo "FAIL $g"
done
rg -q 'rn-forge-cli' tests/fixtures/golden/python-app/pyproject.toml
rg -q 'rn-forge-tooling' tests/fixtures/golden/python-tool/pyproject.toml
task lint                             # state baseline agrees after the re-seed
```
