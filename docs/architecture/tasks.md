# Tasks

The task surface kiln generates in every archetype it has, as built now. The
model is [ADR-0007](../adr/ADR-0007.md); the rules it must meet are in
[the standard, section 1](../reference/standard-repo.md#1-one-entrypoint).

## The model

- **`task` is the only entrypoint.** A human, an agent and a workflow step run
  the same `task` verbs, never `uv`, `pytest`, `pnpm` or another wrapped tool.
- **The root `Taskfile.yml` holds wrappers only.** Each `cmds:` entry is a
  `task:` call into a namespace file; the commands live in `tasks/<ns>.yml`.
- **A file belongs to whatever owns its tasks.** A toolchain (`python`, `node`,
  `kiln`) holds all of its primitives; a concern (`docs`, `ci`) holds the
  checks that are not kiln's; a service (`api`, `web`) holds how to run it.
- **Two public surfaces.** The developer surface is the ten root verbs, the
  `docs:` verbs, `kiln:diff`, `kiln:apply`, `api:*` and `web:dev`. The CI
  surface is every public `ci:` task. They are public only because a workflow
  step runs them from the command line, and go-task refuses to run an internal
  task that way. Each `desc:` starts `CI only:`. Every other task is
  `internal: true`.
- **A supply-chain check, or a check the registry switches, has no
  `command_overrides` key.** That is the dependency audits, the licences
  check, the secret scan and internal ranges: their switch and policy are the
  only ways to change them.
- **The gate is derived.** `required_validate` holds every lint check that is on
  for the repository, so `task-layout` fails when one stops being reachable
  from `validate`.
- **Descriptions say what runs.** A wrapper's `desc:` names every check it calls
  for this repository.
- **The standard's task tables are derived** from the rendered task files
  (`modules/tasks/surface.py`), not copied by hand.

## Files and namespaces

`modules/tasks/artifacts.py` renders `Taskfile.yml` and the files below from
templates in `modules/tasks/templates/`. Each namespace is included by the root
file under its own name.

| File | Namespace | Holds | Public tasks | Rendered for |
| -- | -- | -- | -- | -- |
| `Taskfile.yml` | none | The ten root verbs, as wrappers | all ten | every archetype |
| `tasks/python.yml` | `python` | install, lint, `lint:imports`, `lint:audit`, `lint:licenses`, format, typecheck, test, `test:coverage`, build, version | none | every archetype; `node-lib` keeps it for the docs tooling |
| `tasks/quality.yml` | `quality` | Markdown and TOML formatting checks and formatters | none | every archetype |
| `tasks/kiln.yml` | `kiln` | `doctor` (one internal task), `diff`, `apply` | `kiln:diff`, `kiln:apply` | every archetype |
| `tasks/workspace.yml` | `workspace` | `clean` | none | every archetype |
| `tasks/ci.yml` | `ci` | `lint:workflows` and `secrets:install` (internal); the CI surface | the CI surface | every archetype; the body differs |
| `tasks/docs.yml` | `docs` | `build`, `serve`, `generate` | all three | `[docs] profile = "mkdocs"` |
| `tasks/node.yml` | `node` | install, lint, `lint:audit` (`node-lib`), `lint:licenses` (`node-lib`), test, build, typecheck, e2e, `version` (`node-lib`; the internal primitive behind the root `version`) | none | `python-web-app`, `node-lib` |
| `tasks/api.yml` | `api` | `dev`, and `migrate` for Django | `api:dev`, `api:migrate` | `python-web-api`, `python-web-app` |
| `tasks/web.yml` | `web` | `dev` | `web:dev` | `python-web-app` |
| `<repo's own>` | `[tasks] includes` | whatever the repository puts there | its own | seeded once, then the repository's |

Each include of a repository's own is a seeded file: kiln writes it once and
never again.

## The developer surface

| Task | What it does | Archetypes |
| -- | -- | -- |
| `setup`, `validate`, `lint`, `format`, `typecheck`, `test`, `test:coverage`, `build`, `clean`, `version` | The ten root verbs | all |
| `docs:build`, `docs:serve`, `docs:generate` | Build, serve and regenerate the MkDocs site | all with the `mkdocs` profile |
| `kiln:diff`, `kiln:apply` | Show or apply the difference from a fresh render | all |
| `api:dev` (`api:migrate` for Django) | Run the API service | `python-web-api`, `python-web-app` |
| `web:dev` | Run the frontend dev server | `python-web-app` |

`validate` calls `lint`, `typecheck`, `test` and, with the `mkdocs` profile,
`docs:build`. In `python-lib`, `build` and `version` take a package name after
`--`. The rendered `.rn-forge/kiln/standard.md` carries the table for the
repository's own archetype, with each `desc:` read from the task files.

## The CI surface

Workflow steps call these. A developer has no reason to. Which archetypes render
a task is read from the golden cells' `task --list`.

| Task | Archetypes |
| -- | -- |
| `ci:sonar:target`, `ci:secret-scan` | all; `ci:secret-scan` unless `[ci.checks] secret-scan = false` |
| `ci:release:umbrella` | with the `umbrella-release` check on |
| `ci:plan`, `ci:test`, `ci:integration`, `ci:smoke`, `ci:suites`, `ci:verify-release`, `ci:release:publish` | every Python archetype |
| `ci:validate` | every Python archetype but `python-lib`, and `node-lib` |
| `ci:release:state`, `ci:release:source` | `python-tool`, `python-app`, `python-web-api`, `python-web-app` |
| `ci:adapters`, `ci:release:build` | `python-lib` |
| `ci:internal-ranges` | `python-lib`, with two or more members; always in `node-lib` |
| `ci:release:sign` | `python-lib`, with `[ci] release = "pypi"` |
| `ci:docs:publish` | `python-lib`, with the `mkdocs` profile |
| `ci:test`, `ci:test:has-e2e`, `ci:test:playwright`, `ci:test:playwright-deps`, `ci:smoke`, `ci:sonar:reports` | `node-lib` |
| `ci:release:state`, `:author`, `:tag`, `:verify`, `:push`, `:github`, `:publish`, `:finalize`, `:latest`, and `ci:verify-release` | `node-lib`, with `[ci] release = "nx-dispatch"` |
| `ci:docs:site` | `node-lib`, with the `mkdocs` profile |

Task names are one grammar: `<namespace>:<level>[:<level>]`, with colons between
levels and hyphens joining words inside a level. Under `ci:` it is
`ci:<stage>[:<step>]`. The first level is a stage of
[ADR-0016](../adr/ADR-0016.md) (`validate`, `plan`, `test`, `integration`,
`smoke`, `suites`, `sonar`, `release`, `verify-release`, `docs`) or the name of
a CI-only check (`secret-scan`, `internal-ranges`, `adapters`); a second level
is a step in that stage. Hyphens join words inside a level. One idea has one
name in every archetype, and an archetype renders only its own body. [CI](ci.md)
says which job runs each.

## The gate

`required_validate` is a list in each archetype's `archetype.toml`. The tasks
must stay reachable from `validate`; an archetype adds to the list and never
removes from it.

| Archetype | `required_validate` |
| -- | -- |
| Python (`python-lib`, `python-tool`, `python-app`, `python-web-api`) | `python:lint`, `kiln:doctor`, `python:lint:imports`, `ci:lint:workflows`, `python:lint:audit`, `quality:lint:markdown`, `quality:lint:toml`, `python:typecheck`, `python:test` |
| `python-web-app` | the Python list, plus `node:lint`, `node:typecheck`, `node:test` |
| `node-lib` | `kiln:doctor`, `ci:lint:workflows`, `quality:lint:markdown`, `quality:lint:toml`, `node:lint`, `node:lint:audit`, `node:typecheck`, `node:test` |

`archetypes.for_config` then adds `docs:build` under the `mkdocs` profile, and
the licences task (`python:lint:licenses`, or `node:lint:licenses` for
`node-lib`) when the `licenses` check is on. A concern module may not import a
sibling, so `for_config` learns the licences switch from
`KilnConfig.licenses_enabled`, which reads `[ci.checks]` through
`registry.enabled_names`.

## Extending the surface

A repository reaches the generated tasks only through `config.toml`.

| Key | Effect |
| -- | -- |
| `[tasks] includes` | Wires a repository-owned namespace file (`namespace`, `taskfile`) into the root file. The namespace may not be one kiln owns |
| `[tasks.extra_refs]` | Appends a call to a root verb, keyed by the verb |
| `[tasks.command_overrides]` | Replaces one toolchain primitive's command, keyed by the task name: install, ruff, `lint-imports`, format, pyright, pytest, build, version, the formatters, the workflow linters and the docs verbs. A key for a task the archetype does not render is an error that lists the keys it does |

Check policy lives in `[ci.checks]`, not in `[tasks]`, which holds wiring only:
the licences policy (`[ci.checks] licenses`) and the audit's accepted advisories
(`[ci.checks] pip-audit`, a table of `ignore` entries with `id` and `reason`;
never a boolean, because the audit is standard and stays on).

`command_overrides` has no key for the dependency audits, the licences check,
the secret scan or internal ranges. `python:lint:audit` took one until S17.1.2;
an override now fails with `unknown task`.

## What `task-layout` checks

`kiln doctor`'s `task-layout` check reads the rendered files, not the templates.
A repository-owned include is in the graph, so references into it resolve, and
is otherwise left alone.

| Finding | Means |
| -- | -- |
| `taskgraph.missing` | The root `Taskfile.yml` is not there |
| `taskgraph.surface` | A root task is not one of the ten verbs, or a verb is missing |
| `taskgraph.not-a-wrapper` | A root task has a `cmds:` entry that is not a `task:` call |
| `taskgraph.no-desc` | A task has no non-empty `desc:` |
| `taskgraph.not-internal` | A task in `python`, `node`, `quality`, `workspace` or `kiln` is public (only `kiln:diff` and `kiln:apply` may be) |
| `taskgraph.missing-include` | An include names a file that does not exist |
| `taskgraph.reserved-namespace` | A `[tasks] includes` namespace collides with one kiln owns |
| `taskgraph.unresolved` | A task calls a task that does not exist |
| `taskgraph.cycle` | Tasks call each other in a loop |
| `taskgraph.unresolved-ref` | `task <name>` in a managed workflow or block names no task |
| `taskgraph.no-gate` | There is no `validate` task |
| `gate.shrunk` | A `required_validate` task is not reachable from `validate` |

`ci` is not a reserved namespace, which is how its tasks may be public.
