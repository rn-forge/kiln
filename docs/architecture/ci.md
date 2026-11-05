# CI

What the generated CI does in every archetype kiln has, as built now. The model
it follows is [ADR-0016](../adr/ADR-0016.md); the rules it must meet are in
[the standard, section 8](../reference/standard-repo.md#8-ci-shape). Work not
yet built, including the target stage vocabulary, is in
[E15's design](../specs/epics/E15-ci-standard/design.md).

## The model

- **One workflow, one required check.** `ci.yml` is kiln's and a repository
  never edits it. `ci-ok` is the single check branch protection requires; a
  skipped job is not a failure.
- **Every check is a `task` verb first and a job second.** A step runs a `task`,
  never `uv`, `pytest` or another wrapped tool, so a laptop and CI run the
  same commands. The planner is the `kiln-devops` console script
  ([ADR-0017](../adr/ADR-0017.md)), reached through `task ci:*`. The tasks run
  it with `uvx` from the `[kiln] ref` pin, so it is not in the workspace's
  lock; kiln's own repository runs it with `uv run`.
- **A check gets its own job only when it needs** full git history, extra
  permissions, services, a schedule or a fork guard. Otherwise it folds into
  `task validate` or `task lint`.
- **Switches.** A check is *standard* (always on), *derived* (on when the tree
  calls for it, with no key) or *configured* (a key in `config.toml`, with a
  default).
- **One contract, one tool per stack.** Every archetype meets the same flow;
  only what runs under each `task` differs.

## Stages

Triggers are the same everywhere: a pull request into the default branch, a push
to it, and `workflow_dispatch`. A newer push to a pull request cancels its run;
default-branch runs queue. `validate` gates every other job.

The stages are not named alike yet: `node-lib` releases from `release.yml` and
has no `verify-release` in `ci.yml`. The target vocabulary, one for every
archetype, is in
[the design](../specs/epics/E15-ci-standard/design.md#stage-vocabulary).

| Archetype | `ci.yml` job order | Other workflows |
| -- | -- | -- |
| `python-lib` | `validate` > `dependency-review`, `secret-scan`, `plan` > `test`, `integration`, `smoke`, `suites` > `sonar` > `checks-ok` > `release` > `verify-release`, `docs` > `ci-ok` | none: `docs` is the one Pages deploy |
| `python-tool`, `python-app`, `python-web-api`, `python-web-app` | `validate` > `dependency-review`, `secret-scan`, `plan` > `test`, `integration`, `smoke`, `suites` > `sonar` > `checks-ok` > `release` > `verify-release` > `ci-ok` | `docs.yml` |
| `node-lib` | `validate` > `dependency-review`, `secret-scan`, `test-cloud` or `test-local` > `sonar`, `smoke` > `checks-ok`; `docs` > `ci-ok` | `release.yml` (dispatch) |

| Job | Runs | Task verb |
| -- | -- | -- |
| `validate` (`python-lib`) | repository-wide checks, once | `task lint`, `task ci:adapters`, `task docs:build` |
| `validate` (single-package Python) | lint, typecheck and the docs build, once | `task ci:validate` |
| `validate` (`node-lib`) | what Nx does not run | `task ci:validate` |
| `dependency-review` | pull requests only; fails on a new dependency with a known vulnerability | none: a pinned action |
| `secret-scan` | `task ci:lint:secrets`: gitleaks over the full git history; skipped for a fork's pull request | `[ci.checks] secret-scan`, on |
| `plan` | selects changed packages and their dependents | `task ci:plan` |
| `test` | one leg per selected package; for a single-package Python repository, `task test` | `task ci:test` |
| `integration` | one leg per selected package declaring a service in `[tool.workspace-ci.integration.<service>]`: the task starts the containers, runs the tests, removes them | `task ci:integration` |
| `smoke` | one leg per selected package, plus one per declared extra: the wheel installs and imports | `task ci:smoke` |
| `suites` | the root workspace-wide pytest suites | `task ci:suite` |
| `test-cloud`, `test-local` | `nx affected` on Nx Cloud agents, or on the runner; one runs per `USE_NX_CLOUD` | `task ci:affected` |
| `sonar` | coverage, then the scan, waiting on the quality gate | `task ci:sonar-target`, `task test:coverage` (`python-lib`: after the check legs; `node-lib`: `task ci:coverage`) |
| `release` | publishes from the default branch only, after `sonar` | `python-lib`: `task ci:release-build`, `task ci:release-publish`; single-package Python: `task ci:release-state`, `task build`, `task ci:release-publish`; `node-lib`: in `release.yml` (see below) |
| `verify-release` | installs what was published, from PyPI (`[ci] release = "pypi"`) or from its git tag, into a clean venv outside the repository and imports it; `python-lib` verifies every new tag, a single-package repository the tag `release` output | `task ci:verify-release` (`kiln-devops verify-release`) |
| `smoke` (`node-lib`) | packs and verifies publishable tarballs | `task ci:package` |
| `docs` | deploys Pages once | `python-lib`: `task ci:docs-publish`; `node-lib`: `task docs:build`, `task ci:docs:site` |
| `checks-ok` | the pre-release barrier: every job that runs before `release` passed or was skipped | none |
| `ci-ok` | `checks-ok`, and every job after it, passed or was skipped | none |

## Checks by archetype

Switch is S standard, D derived, C configured. Blank means the archetype does
not run the check. Defaults are on unless stated.

The matrix is generated from kiln's check registry
(`rn_forge/kiln/modules/cicd/registry.py`): adding a check is one registry row
plus its task. The same table, cut to the repository's archetype, is under "CI
checks" in `.rn-forge/kiln/standard.md`.

<!-- BEGIN derived ci-matrix -->

| Check | Verb | lib | tool | app | web-api | web-app | node-lib | Switch and key |
| -- | -- | -- | -- | -- | -- | -- | -- | -- |
| ruff check and format | `task lint` | yes | yes | yes | yes | yes |  | S |
| pyright strict | `task typecheck` | test | yes | yes | yes | yes |  | S |
| `lint-imports` | `task lint` | yes | yes | yes | yes | yes |  | S |
| Markdown and TOML formatting | `task lint` | yes | yes | yes | yes | yes | yes | S |
| `kiln doctor` | `task lint` | yes | yes | yes | yes | yes | yes | S; `--full` per `[ci] doctor_full`, default `default-branch` |
| zizmor, actionlint | `task lint` | yes | yes | yes | yes | yes | yes | S |
| `pip-audit` | `task lint` | yes | yes | yes | yes | yes |  | S; ignore list `[tasks.audit] ignore` |
| `pnpm-audit` | `task python:lint:audit` |  |  |  |  |  | yes | S |
| Nx lint, typecheck, test, build | `task node:*`, `task ci:affected` |  |  |  |  | yes | yes | S |
| pytest | `task test` | test | yes | yes | yes | yes |  | S |
| Services, smoke, suites | `task ci:*` | yes |  |  |  |  |  | D: a package declares them |
| Adapters check | `task ci:adapters` | yes |  |  |  |  |  | S |
| Docs strict build | `task docs:build` | yes | yes | yes | yes | yes | yes | D: `[docs] profile = "mkdocs"` |
| `dependency-review` | action | yes | yes | yes | yes | yes | yes | S |
| Sonar | `sonar` job | yes | yes | yes | yes | yes | yes | C: `[ci] sonar`, default `true` |
| Release | `release` job | yes | yes | yes | yes | yes | `release.yml` | C: `[ci] release`, default `tag-exists`; `pypi` for `python-lib`; `nx-dispatch` for `node-lib`; `none` |
| `verify-release` | `task ci:verify-release` | yes | yes | yes | yes | yes |  | D: a release mode other than `none` |
| Docs deploy | `docs` job or `docs.yml` | `ci.yml` | `docs.yml` | `docs.yml` | `docs.yml` | `docs.yml` | `ci.yml` | D: `[docs] profile = "mkdocs"` |
| Package tarballs | `task ci:package` |  |  |  |  |  | yes | S |
| `ci-ok` | none | yes | yes | yes | yes | yes | yes | S |
| `licenses` | `task python:lint:licenses` | yes | yes | yes | yes | yes | yes | C: `[ci.checks] licenses`, default `true`; a table sets `deny` and `ignore` |
| `secret-scan` | `task ci:lint:secrets` | yes | yes | yes | yes | yes | yes | C: `[ci.checks] secret-scan`, default `true` |
| `internal-ranges` | `task ci:requirements` | yes |  |  |  |  | yes | D: two or more workspace members |
| `umbrella-release` | `task ci:release:umbrella` | yes | yes | yes | yes | yes | yes | C: `[ci.checks] umbrella-release`, default `false` |
| `scorecard` | none | yes | yes | yes | yes | yes | yes | C: `[ci.checks] scorecard`, default `false`; public repositories only |

<!-- END derived ci-matrix -->

`kiln doctor --full` runs on a push to the default branch and on dispatch, or on
every run with `[ci] doctor_full = "every-run"`. Sonar is skipped for a fork's
pull request in every archetype, and for Dependabot in `node-lib`.

## Hooks

A repository reaches the generated CI only through `config.toml`, naming files
it owns.

| Tier | Key | What it does |
| -- | -- | -- |
| Switch a kiln check | `[ci]`: `sonar`, `release`, `doctor_full`, `sonar_exclusions`, `sonar_coverage_exclusions` | Turns a check on or off, or sets its policy |
| Steps inside kiln's jobs | `[ci.hooks] setup` | Local composite actions (`./.github/actions/<name>`) the generated setup action runs last, so every job using it gets them |
|  | `[ci.hooks] docs` | Local composite actions every Pages-uploading job runs before the upload, with `SITE_DIR` set |
| A repository's own job | `[[ci.jobs]]` | Renders a reusable-workflow call that needs `validate` and that `ci-ok` needs unless `required = false` |

A repository-owned workflow is allowed only for a scheduled or non-gating run;
it keeps its own action pins current through Dependabot, which ignores the
actions kiln pins.

A `[[ci.jobs]]` entry has `name` (kebab-case, not a job kiln generates), `uses`
(`./.github/workflows/<file>.yml`, not `ci.yml`), `events` (default all three of
`pull_request`, `push`, `workflow_dispatch`) and `contents` (`read`, or `write`
for a job that creates releases). Every entry gates `checks-ok` (hence
`release`) unless `required = false`. `ci-hooks` checks that each hook and job
names a file that exists and, for a job, can be called.

### `[ci.checks]`

```toml
[ci.checks]
licenses = { deny = ["GPL", "GPL-*", "AGPL", "AGPL-*", "UNKNOWN"], ignore = ["some-package"] }
secret-scan = true
umbrella-release = false
scorecard = false
```

- Keys are the registry's configured checks, the same for every archetype. A
  standard or derived check has no key; naming one is an error.
- `scorecard = true` renders `.github/workflows/scorecard.yml` for a public
  repository: a weekly and dispatchable OpenSSF Scorecard run that uploads its
  SARIF to Code scanning. It reports and does not gate, so `ci-ok` never waits
  for it.
- A value is a boolean or, for a check with a policy (`licenses`), a table.
- A switch outside the table stays where it is: `[ci] sonar`, `release`,
  `doctor_full`.
- `umbrella-release = true` with `[ci] release = "none"` is an error: there is
  no release job to hold the step.

### `[[ci.jobs]]` and `required`

```toml
[[ci.jobs]]
name = "broker-profile"
uses = "./.github/workflows/broker-profile.yml"
events = ["pull_request", "push", "workflow_dispatch"]
contents = "read"
required = true
```

`required` defaults to `true`: the job is in `checks-ok`'s `needs`. `false`
renders the job, still after `validate`, but nothing waits for it.

## Per-archetype detail

### Single-package Python

`python-tool`, `python-app`, `python-web-api` and `python-web-app` are a
workspace of one member, the root project, so they run the same `plan`, `test`,
`integration`, `smoke` and `suites` jobs as `python-lib`: `validate` > `plan` >
`test`, `integration`, `smoke`, `suites` > `sonar` > `checks-ok` > `release`.
`validate` runs `task ci:validate` (`task lint`, `task typecheck`, and
`task docs:build` with docs); `test` runs `task test`, which for
`python-web-app` includes the frontend. A change under `docs/` alone selects
nothing; any other change selects the one member. `release` waits for `plan` and
`checks-ok`, builds with `task build` and publishes with
`task ci:release-publish`, after `task ci:release-state` decides whether the
version is new. `python-web-api` and `python-web-app` run the same pipeline with
the API package under `api_dir`; `python-web-app` adds the frontend
(`task node:*`) to `lint`, `typecheck`, `test` and `build`. They deploy docs
from `docs.yml` (`task docs:build`, on a push to the default branch), which is
outside `ci-ok` and not gated on `release`.

### `node-lib`

`validate` runs `task ci:validate`; `test-cloud` or `test-local` runs
`task ci:affected` (Nx's lint, typecheck, test and build on the affected
projects); `sonar` waits for one of them; `smoke` packs and verifies the
publishable tarballs; `docs` builds the site. `checks-ok` and `ci-ok` share one
macro (no `jq`): a failed or cancelled need fails them, and the inactive one of
`test-cloud` and `test-local` is skipped, which passes. Sonar is skipped for
Dependabot's pull requests.

`release.yml` is dispatched (`task ci:release:*`): a gate on a green CI run,
version, verify, push, publish and a rolling `latest` release, then
`published-install`. [ADR-0015](../adr/ADR-0015.md) records it.

### `python-lib`, event by event

What the workspace pipeline does on each event, and how a release is decided.
The `docs` job is
[S11.5.1](../specs/epics/E11-package-docs/F11.5-deploy-package-sites.md#s1151-ci-deploys-versioned-package-sites);
the pipeline was built in
[F6.4](../specs/epics/E6-rebuild-the-repos/F6.4-workspace-pipeline.md).

#### Triggers

| Event | Runs? |
| -- | -- |
| Pull request into `main` | yes |
| Push to `main` (a merge) | yes |
| `workflow_dispatch`, on any branch | yes |
| Push to any other branch | no, unless a pull request into `main` is open for it |

A newer push to the same pull request cancels the run in progress. Pushes to
`main` queue instead, so a release is never cut off midway.

#### What the plan selects

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

#### Jobs by event

| Job | What it proves | Pull request | Push to `main` | Dispatch |
| -- | -- | -- | -- | -- |
| `validate` | `task lint` (ruff and format, generated-file drift, rn-forge dependency pins, import contracts, task layout, `ci-entrypoint`, docs links, structure and derived regions, markdown), `task ci:adapters`, and the strict docs build of the root and every package site | runs | runs, with `kiln doctor --full` | runs, with `kiln doctor --full` |
| `plan` | the selection above | runs | runs | runs, every package |
| `test`, one per selected package | ruff, pyright and pytest for that member | selected | selected | every package |
| `integration`, one per selected package that declares `[tool.workspace-ci.integration.<service>]` | that member's tests against the service containers it declares | selected | selected | every declaring package |
| `smoke`, one per selected package with no extra, plus one per declared extra | the built wheel, with no extra or with that one extra, installs into a clean venv and imports | selected | selected | every package and declared extra |
| `suites` | the root `[tool.workspace-ci.suites]` pytest runs | always, all suites | always | always |
| `sonar` | whole-workspace coverage, then the scan, waiting on the quality gate | runs; skipped for a fork's pull request | runs, on branch `main` | runs, on the dispatched branch |
| `release` | each selected package whose checks passed is built with its SBOM (`task ci:release-build`), attested, then published (`task ci:release-publish`) as `<package>-v<version>`, after `sonar` passed | skipped | builds and publishes | skipped |
| `verify-release` | each new release installs from PyPI or its git tag, outside the repository, and imports; a single-package repository runs it only when `release` published (its `tag` output is not empty) | skipped | runs | skipped |
| `docs` | each package tagged at this commit deployed with `mike`, then the root site plus `packages/` to Pages; `[ci.hooks] docs` actions run before the upload | skipped | runs | skipped |
| `checks-ok` | the pre-release barrier: `validate`, `dependency-review`, `plan`, `test`, `integration`, `smoke`, `suites`, `sonar`, `secret-scan`, and the checks and required jobs, none failed or cancelled | runs | runs | runs |
| `ci-ok` | `checks-ok`, `release`, `verify-release`, `docs`: none failed or cancelled; a skipped job is not a failure | runs | runs | runs |

#### Ordering and gating

```text
validate ─► plan ─┬─► test ────────┐
                  ├─► integration ─┼─► sonar ─► release ─► verify-release
                  ├─► smoke ───────┘                 └───► docs
                  └─► suites
`validate` .. `sonar` ─► checks-ok ─► release
`checks-ok`, `release`, `verify-release`, `docs` ─► ci-ok
```

- Nothing runs unless `validate` passes.
- `sonar` waits for `test`, `integration` and `smoke`, and runs only if none
  failed.
- `checks-ok` waits for every job above it (and the declared checks) and fails
  when any failed or was cancelled; a skipped job passes.
- `release` waits for `plan` and `checks-ok`. It runs only on a push to `main`,
  when the selection is not empty and `checks-ok` succeeded, so a failed check
  of any kind blocks every package. Within a run it decides per package.
- `ci-ok` is the one check branch protection requires, because job names change
  as members come and go.

#### How a release is decided

- Each passing `test`, `integration` and `smoke` leg uploads an `ok-<marker>`
  artifact. `release` publishes a package only when every one of its markers
  exists and every selected package it requires is releasable too. Because
  `release` waits for `checks-ok`, any failed leg holds back the whole run's
  releases; the run is red through `ci-ok`. The markers still guard a leg that
  was skipped for a package that was not selected.
- Releases follow version bumps. A tag that is already published is skipped; a
  draft is rebuilt from its tag and replaced. A merge that changes a package
  without bumping its version re-verifies it and publishes nothing.
- With `[ci] release = "pypi"`, `release-publish` uploads a package's wheel and
  sdist, with their PEP 740 attestations, to PyPI before it creates that
  package's GitHub release, unless PyPI already has the version. A rerun
  resumes: what PyPI and GitHub have is skipped. A dispatch with `testpypi`
  set builds every releasable package from `HEAD`, uploads each to TestPyPI,
  and creates no tag or release.
- Only a push to `main` publishes, and only after the quality gate. A pull
  request or a dispatch (other than a `testpypi` one) does not run `release`;
  its packaging proof is `smoke`, which installs every selected package's
  wheel with no extras and imports it.

#### Worked example: a docs-only pull request

The selection is empty, so `test`, `integration`, `smoke` and `release` are
skipped. `validate`, which builds the docs strictly, `suites` and `sonar` still
run, and `ci-ok` passes.
