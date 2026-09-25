# Release 1 — kiln generates and self-hosts the Python archetypes

**Status:** in progress

kiln renders `python-app`, `python-app` + `lifecycle` (the `python-tool` alias)
and `python-lib` from authored templates, regenerates its own repo, and rebuilds
pykit's skeleton. The web archetypes are [release-2](../release-2/index.md).

## Entry criteria

- [Release 0](../release-0/index.md) ships before this one does — **met**
  2026-09-12.
- Before
  [F3.3](../../specs/epics/E3-realign-goldens-and-canon/F3.3-python-tool-is-a-tool.md):
  pykit's lifecycle surface has landed
  ([upstream work](../../specs/index.md#upstream-work-owned-by-pykit)).
- Order inside the release follows each feature's **Depends on** line.
  [S4.1.4](../../specs/epics/E4-generator/F4.1-checks-by-module.md#s414-the-ci-shape-is-decided)
  — the checks-shape decision — came first and is done
  ([ADR-0006](../../adr/ADR-0006.md)).

## Scope

| Epic | Stories |
| -- | -- |
| [E3 — Realign the goldens and the canon](../../specs/epics/E3-realign-goldens-and-canon/index.md) | [S3.1.1–S3.1.3](../../specs/epics/E3-realign-goldens-and-canon/F3.1-goldens-on-part-e-api.md), [S3.2.1–S3.2.2](../../specs/epics/E3-realign-goldens-and-canon/F3.2-branch-pins.md), [S3.3.1–S3.3.2](../../specs/epics/E3-realign-goldens-and-canon/F3.3-python-tool-is-a-tool.md), [S3.4.1–S3.4.4](../../specs/epics/E3-realign-goldens-and-canon/F3.4-canon-catches-up.md) |
| [E4 — The generator](../../specs/epics/E4-generator/index.md) | [S4.1.1–S4.1.4](../../specs/epics/E4-generator/F4.1-checks-by-module.md), [S4.2.1–S4.2.3](../../specs/epics/E4-generator/F4.2-core-module.md), [S4.3.1–S4.3.7](../../specs/epics/E4-generator/F4.3-concern-modules.md), [S4.4.1–S4.4.3](../../specs/epics/E4-generator/F4.4-render-matrix.md), [S4.5.1–S4.5.9](../../specs/epics/E4-generator/F4.5-cli.md), [S4.6.1–S4.6.4](../../specs/epics/E4-generator/F4.6-doctor.md), [S4.7.1](../../specs/epics/E4-generator/F4.7-import-contracts.md), [S4.8.1](../../specs/epics/E4-generator/F4.8-self-hosting.md) |
| [E6 — Rebuild the repos](../../specs/epics/E6-rebuild-the-repos/index.md) | [S6.1.1–S6.1.2](../../specs/epics/E6-rebuild-the-repos/F6.1-pykit-skeleton.md) |

## Exit criteria

- E3's acceptance block passes.
- E4's acceptance block passes.
- `kiln doctor --all rn-forge/pykit rn-forge/kiln --json` reports zero errors,
  and `task validate` passes in both.
- Every open question on an in-scope feature is answered, as an ADR or as a
  rejected option recorded on the feature.
