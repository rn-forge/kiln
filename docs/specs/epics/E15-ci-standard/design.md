# E15 — Design: the target CI

[Back to the epic](index.md)

The to-be state of the generated CI, which E15's features build. The decisions
are in [ADR-0016](../../../adr/ADR-0016.md) and are final; this page spells them
out so a feature can be built against it. What exists today is in
[the CI architecture page](../../../architecture/ci.md).

**Rows move as features land.** When a feature closes, its rows move from this
page to `ci.md`, and the feature's closing step says so. When E15 closes, this
page is deleted, with the pointers to it in `ci.md`, the epic index and the
features. F15.8's rows (the stage vocabulary, the archetype by stage table, the
pre-release barrier, `node-lib`'s versioning, integration and the reusable
layout) have moved.

## Checks by archetype

Switch is S standard, D derived, C configured. A blank cell means the archetype
does not run the check. "Built" rows are in
[`ci.md`](../../../architecture/ci.md); the others name the feature that builds
them.

| Check | Stage | lib | tool | app | web-api | web-app | node-lib | Switch and default | Feature |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| ruff, pyright, `lint-imports` | `validate`, `test` | yes | yes | yes | yes | yes |  | S | built |
| Markdown and TOML formatting, `kiln doctor`, zizmor, actionlint | `validate` | yes | yes | yes | yes | yes | yes | S | built |
| `pip-audit` | `validate` | yes | yes | yes | yes | yes |  | S; ignore list `[tasks.audit] ignore` | built |
| `pnpm audit` | `validate` |  |  |  |  |  | yes | S | built |
| Licences | `validate` | yes | yes | yes | yes | yes | yes | C: `[ci.checks] licenses`, on | built |
| Secret scan | `secret-scan` job | yes | yes | yes | yes | yes | yes | C: `[ci.checks] secret-scan`, on | built |
| Internal ranges | `plan` (lib), `validate` (node-lib) | yes |  |  |  |  | yes | D: a workspace with two or more members | built |
| `dependency-review` | `dependency-review` job | yes | yes | yes | yes | yes | yes | S | built |
| Nx lint, typecheck, test, build | `test` |  |  |  |  | yes | yes | S | built |
| pytest | `test` | yes | yes | yes | yes | yes |  | S | built |
| Integration | `integration` | yes | yes | yes | yes | yes |  | D: a package declares a service | [F15.8](F15.8-one-workflow-contract.md) |
| Smoke | `smoke` | yes | yes | yes | yes | yes | yes | S | [F15.8](F15.8-one-workflow-contract.md) (built for `lib`, `node-lib`) |
| Suites | `suites` | yes | yes | yes | yes | yes |  | D: `[tool.workspace-ci.suites]` declared | [F15.8](F15.8-one-workflow-contract.md) (built for `lib`) |
| Adapters check | `validate` | yes |  |  |  |  |  | S | built |
| Docs strict build | `validate` | yes | yes | yes | yes | yes | yes | D: `[docs] profile = "mkdocs"` | built |
| Sonar | `sonar` | yes | yes | yes | yes | yes | yes | C: `[ci] sonar`, on | built; one guard in [F15.8](F15.8-one-workflow-contract.md) |
| Release | `release` | yes | yes | yes | yes | yes | yes | C: `[ci] release`, `tag-exists` | built; `node-lib` in [F15.8](F15.8-one-workflow-contract.md) |
| `verify-release` | `verify-release` | yes | yes | yes | yes | yes | yes | D: a release mode other than `none` | [F15.8](F15.8-one-workflow-contract.md) (built for `lib` as `external-install`) |
| Docs deploy | `docs` | yes | yes | yes | yes | yes | yes | D: `[docs] profile = "mkdocs"` | [F15.8](F15.8-one-workflow-contract.md) |
| Scorecard | `scorecard.yml` | yes | yes | yes | yes | yes | yes | C: `[ci.checks] scorecard`, off; public repositories | built |
| `ci-ok` | `ci-ok` | yes | yes | yes | yes | yes | yes | S | built; one logic in [F15.8](F15.8-one-workflow-contract.md) |

## Hook tiers

All declared in `.rn-forge/kiln/config.toml`, naming files the repository owns.

| Tier | Key | Does |
| -- | -- | -- |
| 1 | `[ci.checks]` | Switches a configured check or sets its policy |
| 2 | `[ci.hooks]` `setup`, `docs` | Runs local composite actions inside kiln's jobs at a named anchor |
| 3 | `[[ci.jobs]]` | A reusable-workflow call after `validate`; `required` says whether `checks-ok` needs it |
| 4 | a repository-owned workflow | Non-gating or scheduled runs only; its action pins are kept current by Dependabot, which ignores the actions kiln pins |

## Moving rows to `ci.md`

Each feature ends with a closing step: move its rows from this page to
[`ci.md`](../../../architecture/ci.md), in the section that fits (stages,
checks, hooks, per-archetype detail). A row is moved only when its acceptance
holds.
