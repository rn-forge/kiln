# How a `python-lib` CI run flows

What the generated `.github/workflows/ci.yml` of a `python-lib` workspace does
on each event: which jobs run, what each one proves, and what is skipped. The
rules it must follow are in
[the standard, section 8](../reference/standard-repo.md#8-ci-shape); the work
that built it is
[F6.4](../specs/epics/E6-rebuild-the-repos/F6.4-workspace-pipeline.md), and the
`docs` job is
[S11.5.1](../specs/epics/E11-package-docs/F11.5-deploy-package-sites.md#s1151-ci-deploys-versioned-package-sites).
A `python-lib` renders no `docs.yml`; `docs` is its one Pages deploy.

Every step runs a `task`; no step calls `uv`, `pytest` or another wrapped tool
directly, so a laptop and CI run the same commands. The planner is the
`rn-forge-devops` console script, reached through `task ci:plan`.

## Triggers

| Event | Runs? |
| -- | -- |
| Pull request into `main` | yes |
| Push to `main` (a merge) | yes |
| `workflow_dispatch`, on any branch | yes |
| Push to any other branch | no, unless a pull request into `main` is open for it |

A newer push to the same pull request cancels the run in progress. Pushes to
`main` queue instead, so a release is never cut off midway.

## What the plan selects

| Event | Diffed against | Selected |
| -- | -- | -- |
| Pull request | the pull request's base commit | changed packages, plus every package that depends on one |
| Push to `main` | the head of the last green `ci.yml` push run on `main` | the same rule |
| Dispatch | nothing | every package |

- A file under a member's directory selects that member, then its dependents.
- A change only under `docs/` selects nothing.
- A change anywhere else (the root `pyproject.toml`, `uv.lock`, `.github/`)
  selects every package.
- An empty base, or one that is not an ancestor of `HEAD` (a dispatch, the first
  run after adoption, a force-push), selects every package.

## Jobs by event

| Job | What it proves | Pull request | Push to `main` | Dispatch |
| -- | -- | -- | -- | -- |
| `validate` | `task lint` (ruff and format, generated-file drift, rn-forge dependency pins, import contracts, task layout, `ci-entrypoint`, docs links, structure and derived regions, markdown), `task ci:adapters`, and the strict docs build of the root and every package site | runs | runs, with `kiln doctor --full` | runs, with `kiln doctor --full` |
| `plan` | the selection above | runs | runs | runs, every package |
| `verify`, one per selected package | ruff, pyright and pytest for that member | selected | selected | every package |
| `postgres`, one per selected package that declares `[tool.workspace-ci.postgres]` | that member's tests against a PostgreSQL 17 service | selected | selected | every declaring package |
| `smoke`, one per selected package with no extra, plus one per declared extra | the built wheel, with no extra or with that one extra, installs into a clean venv and imports | selected | selected | every package and declared extra |
| `suites` | the root `[tool.workspace-ci.suites]` pytest runs | always, all suites | always | always |
| `sonar` | whole-workspace coverage, then the scan, waiting on the quality gate | runs; skipped for a fork's pull request | runs, on branch `main` | runs, on the dispatched branch |
| `release` | each selected package whose checks passed is built with its SBOM (`task ci:release-build`), attested, then published (`task ci:release-publish`) as `<package>-v<version>`, after `sonar` passed | skipped | builds and publishes | skipped |
| `external-install` | each new tag installs from git, outside the workspace, and imports | skipped | runs | skipped |
| `docs` | each package tagged at this commit deployed with `mike`, then the root site plus `packages/` to Pages; `[ci.hooks] docs` actions run before the upload | skipped | runs | skipped |
| `ci-ok` | no job failed or was cancelled; a skipped job is not a failure | runs | runs | runs |

## Ordering and gating

```text
validate ─► plan ─┬─► verify ───┐
                  ├─► postgres ─┼─► sonar ─► release ─► external-install
                  ├─► smoke ────┘                 └───► docs
                  └─► suites
all of them ─► ci-ok
```

- Nothing runs unless `validate` passes.
- `sonar` waits for `verify`, `postgres` and `smoke`, and runs only if none
  failed.
- `release` waits for the same three and for `sonar`. It runs only on a push to
  `main`, when the selection is not empty and `sonar` succeeded (where
  `[ci] sonar` is off, `sonar` is not rendered and the condition is absent).
  Within a run it decides per package.
- `ci-ok` is the one check branch protection requires, because job names change
  as members come and go.

## How a release is decided

- Each passing `verify`, `postgres` and `smoke` leg uploads an `ok-<marker>`
  artifact. `release` publishes a package only when every one of its markers
  exists and every selected package it requires is releasable too. Because
  `release` waits for `sonar`, and `sonar` runs only if no check failed, any
  failed leg holds back the whole run's releases; the run is red through
  `ci-ok`. The markers still guard a leg that was skipped for a package that
  was not selected.
- Releases follow version bumps. A tag that is already published is skipped; a
  draft is rebuilt from its tag and replaced. A merge that changes a package
  without bumping its version re-verifies it and publishes nothing.
- Only a push to `main` publishes, and only after the quality gate. A pull
  request or a dispatch does not run `release`; its packaging proof is
  `smoke`, which installs every selected package's wheel with no extras and
  imports it.

## Worked example: a docs-only pull request

The selection is empty, so `verify`, `postgres`, `smoke` and `release` are
skipped. `validate`, which builds the docs strictly, `suites` and `sonar` still
run, and `ci-ok` passes.
