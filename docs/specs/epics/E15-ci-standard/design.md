# E15 — Design: the target CI

[Back to the epic](index.md)

The to-be state of the generated CI, which E15's features build. The decisions
are in [ADR-0016](../../../adr/ADR-0016.md) and are final; this page spells them
out so a feature can be built against it. What exists today is in
[the CI architecture page](../../../architecture/ci.md).

**Rows move as features land.** When a feature closes, its rows move from this
page to `ci.md`, and the feature's closing step says so. When E15 closes, this
page is deleted, with the pointers to it in `ci.md`, the epic index and the
features.

## Stage vocabulary

Every archetype's `ci.yml` runs the same stages, in this order, then `ci-ok`. An
archetype maps each stage to a stack-specific `task`, or marks it n/a.

| Stage | Means |
| -- | -- |
| `validate` | repository-wide checks, once; gates everything |
| `plan` | selects the units to run. A single-package archetype is a plan of one unit |
| `test` | unit tests (with lint and typecheck where the stack runs them per unit), per selected unit. `python-lib`'s `verify` is renamed `test` |
| `integration` | tests against declared service containers. Replaces the `postgres` and `redis` jobs |
| `smoke` | the built artifact installs and starts or imports |
| `suites` | end-to-end or cross-unit tests |
| `sonar` | coverage and the quality gate |
| `release` | publish, from the default branch only, after `sonar` |
| `verify-release` | install the published release from its registry. Replaces `external-install` and `node-lib`'s `published-install` |
| `docs` | deploy Pages once, after the release stages |

Job names other than `ci-ok` are not required checks, so renaming is safe.

## Archetype by stage

| Stage | `python-lib` | `python-tool`, `python-app` | `python-web-api`, `python-web-app` | `node-lib` |
| -- | -- | -- | -- | -- |
| `validate` | `task lint`, `task ci:adapters`, `task docs:build` | `task validate` | `task validate` | `task ci:validate` |
| `plan` | `task ci:plan` | `task ci:plan` (one unit) | `task ci:plan` (one unit) | n/a: Nx computes the affected graph inside `ci:affected` |
| `test` | `task ci:test`, a leg per package | `task ci:test` | `task ci:test`; `python-web-app` adds `task node:*` | `task ci:affected` (`test-cloud` or `test-local`) |
| `integration` | `task ci:integration`, a leg per package with services | `task ci:integration` when declared | `task ci:integration` when declared | n/a |
| `smoke` | `task ci:smoke`, a leg per package and declared extra | `task ci:smoke` | `task ci:smoke` | `task ci:package` |
| `suites` | `task ci:suite` | `task ci:suite` when declared | `task ci:suite` when declared | n/a |
| `sonar` | `task ci:sonar-target`, `task test:coverage` | the same | the same | `task ci:sonar-target`, `task ci:coverage` |
| `release` | `task ci:release-build`, `task ci:release-publish` | `task ci:release-state`, `task build`, `task ci:release-publish` | the same | `task ci:release:*` |
| `verify-release` | `task ci:verify-release` | `task ci:verify-release` | `task ci:verify-release` | `task ci:verify-release` |
| `docs` | `task ci:docs-publish` | `task docs:build`, then the Pages deploy | the same | `task docs:build`, `task ci:docs:site`, then the Pages deploy |

- `verify-release` installs from the registry the release went to (PyPI with
  `[ci] release = "pypi"`, the git tag with `tag-exists`, the release tarballs
  with `nx-dispatch`). It is not rendered with `[ci] release = "none"`.
- `docs` runs on a push to the default branch, after the last of `release` and
  `verify-release` that is rendered has succeeded; `[ci.hooks] docs` actions
  run before the upload.
- One `ci-ok` logic and one Sonar guard serve every archetype: `ci-ok` fails
  when any needed job failed or was cancelled; Sonar is skipped for a fork's
  pull request and for Dependabot's.

## Integration: services as data

A package declares the service containers its tests need in its own
`pyproject.toml`. Nothing in kiln names a database.

```toml
[tool.workspace-ci.integration.postgres]
image = "postgres:17"
ports = ["5432:5432"]
health-cmd = "pg_isready -U ci"

[tool.workspace-ci.integration.postgres.env]
POSTGRES_USER = "ci"
POSTGRES_PASSWORD = "ci"
POSTGRES_DB = "ci"

[tool.workspace-ci.integration.postgres.expose]
DATABASE_URL = "postgresql://ci:ci@localhost:5432/ci"
```

`plan` emits one `integration` entry per selected package with a non-empty set;
one matrix job runs a leg per entry. The leg's `task ci:integration` starts the
package's containers, waits for their health, runs the package's tests with the
`expose` variables set, and removes the containers.

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
| `pnpm audit` | `validate` |  |  |  |  |  | yes | S | [F15.2](F15.2-licences-check.md) |
| Licences | `validate` | yes | yes | yes | yes | yes | yes | C: `[ci.checks] licenses`, on | [F15.2](F15.2-licences-check.md) |
| Secret scan | `secret-scan` job | yes | yes | yes | yes | yes | yes | C: `[ci.checks] secret-scan`, on | [F15.3](F15.3-secret-scan.md) |
| Internal ranges | `plan` (lib), `validate` (node-lib) | yes |  |  |  |  | yes | D: a workspace with two or more members | [F15.4](F15.4-internal-ranges.md) |
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
| Umbrella release | `release` | yes | yes | yes | yes | yes | yes | C: `[ci.checks] umbrella-release`, off | [F15.5](F15.5-umbrella-release.md) |
| `verify-release` | `verify-release` | yes | yes | yes | yes | yes | yes | D: a release mode other than `none` | [F15.8](F15.8-one-workflow-contract.md) (built for `lib` as `external-install`) |
| Docs deploy | `docs` | yes | yes | yes | yes | yes | yes | D: `[docs] profile = "mkdocs"` | [F15.8](F15.8-one-workflow-contract.md) |
| Scorecard | `scorecard.yml` | yes | yes | yes | yes | yes | yes | C: `[ci.checks] scorecard`, off; public repositories | [F15.6](F15.6-scorecard.md) |
| `ci-ok` | `ci-ok` | yes | yes | yes | yes | yes | yes | S | built; one logic in [F15.8](F15.8-one-workflow-contract.md) |

## `[ci.checks]`

```toml
[ci.checks]
licenses = { deny = ["GPL-*", "AGPL-*", "UNKNOWN"], ignore = ["some-package"] }
secret-scan = true
umbrella-release = false
scorecard = false
```

- Keys are the registry's configured checks, the same for every archetype. A
  standard or derived check has no key; naming one is an error.
- A value is a boolean or, for a check with a policy (`licenses`), a table.
- A switch outside the table stays where it is: `[ci] sonar`, `release`,
  `doctor_full`.
- `umbrella-release = true` with `[ci] release = "none"` is an error: there is
  no release job to hold the step.

## `[[ci.jobs]]`

```toml
[[ci.jobs]]
name = "broker-profile"
uses = "./.github/workflows/broker-profile.yml"
events = ["pull_request", "push", "workflow_dispatch"]
contents = "read"
required = true
```

`required` defaults to `true`: the job is in `ci-ok`'s `needs`. `false` renders
the job, still after `validate`, but `ci-ok` does not wait for it.

## Hook tiers

All declared in `.rn-forge/kiln/config.toml`, naming files the repository owns.

| Tier | Key | Does |
| -- | -- | -- |
| 1 | `[ci.checks]` | Switches a configured check or sets its policy |
| 2 | `[ci.hooks]` `setup`, `docs` | Runs local composite actions inside kiln's jobs at a named anchor |
| 3 | `[[ci.jobs]]` | A reusable-workflow call after `validate`; `required` says whether `ci-ok` needs it |
| 4 | a repository-owned workflow | Non-gating or scheduled runs only; its action pins are kept current by Dependabot, which ignores the actions kiln pins |

## Reusable workflow layout

`ci.yml` stays the one entry workflow and `ci-ok` the one required check. kiln
splits a stage into a reusable workflow, `.github/workflows/_<stage>.yml`
(`on: workflow_call`), when the stage's YAML is large or shared across
archetypes. All of them are rendered by kiln, carry its provenance header, and
are read-only to the repository.

| File | Stage | Why split |
| -- | -- | -- |
| `_integration.yml` | `integration` | a matrix leg with containers; Python archetypes |
| `_smoke.yml` | `smoke` | a matrix leg; Python archetypes |
| `_sonar.yml` | `sonar` | one body, one guard, every archetype |
| `_release.yml` | `release` | the largest stage; one body per release mode |
| `_verify-release.yml` | `verify-release` | every archetype |
| `_docs.yml` | `docs` | every archetype; Pages permissions in one place |

`validate`, `plan`, `test`, `suites`, `dependency-review`, `secret-scan` and
`ci-ok` stay in `ci.yml`: each is short or needs `ci.yml`'s outputs.

- The caller job in `ci.yml` grants the permissions; a called workflow can only
  narrow them. Secrets are passed by name, never `secrets: inherit`.
- A reusable workflow's checks appear as `<caller job> / <job>`. Only `ci-ok` is
  required, so no ruleset changes.
- `[[ci.jobs]] uses` may not name a `_<stage>.yml` file kiln renders.

## Moving rows to `ci.md`

Each feature ends with a closing step: move its rows from this page to
[`ci.md`](../../../architecture/ci.md), in the section that fits (stages,
checks, hooks, per-archetype detail). A row is moved only when its acceptance
holds.
