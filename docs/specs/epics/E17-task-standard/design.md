# E17 — Design: the target task surface

[Back to the epic](index.md)

The to-be state of the generated task surface, which E17's features build. The
decisions below were made by the owner on 2026-11-05. F17.1 writes them into
[ADR-0007](../../../adr/ADR-0007.md). When E17 closes, this page is deleted,
along with the links to it from the epic and the features. What exists then is
in `docs/architecture/tasks.md`.

## Decisions

1. **`ci:` is the declared CI surface.** Its tasks are public only because a
   workflow step runs them from the command line, and go-task refuses to run
   an internal task that way. They are CI's, not a developer's: each `desc:`
   starts `CI only:`, and the standard lists them in a table of their own. The
   ten root verbs, the `docs:` verbs, `kiln:diff`, `kiln:apply`, `api:*` and
   `web:dev` are the developer surface. Every other task is `internal: true`.
1. **One naming grammar.** A task name is `<namespace>:<level>[:<level>]`.
   Colons separate levels; hyphens join words inside a level. Under `ci:`, the
   first level is a stage from [ADR-0016](../../../adr/ADR-0016.md)'s
   vocabulary (`validate`, `plan`, `test`, `integration`, `smoke`, `suites`,
   `sonar`, `release`, `verify-release`, `docs`) or a CI-only check's registry
   name (`secret-scan`, `internal-ranges`, `adapters`). A second level is a
   step in that stage (`ci:release:state`, `ci:sonar:target`). One idea has
   one name in every archetype, and an archetype renders only its own body.
1. **A supply-chain check, or a check the registry switches, has no
   `command_overrides` key.** That means the dependency audits (pip-audit,
   pnpm audit), the licences check, the secret scan and internal ranges. Their
   switch and their policy are the only ways to change them. Overriding one
   would turn it off without the config saying so. `command_overrides` keeps
   replacing a toolchain primitive: install, ruff, `lint-imports`, format,
   pyright, pytest, build, version, the formatters, the workflow linters and
   the docs verbs. Today only `python:lint:audit` breaks the rule.
1. **The gate holds every lint check that is on.** `required_validate` includes
   each registry check folded into `task lint` that is enabled for the
   repository, so `task-layout` fails when one stops being reachable from
   `validate`.
1. **Descriptions say what runs.** A wrapper's `desc:` names every check it
   calls for this repository, and a workspace's descriptions say "each
   package".
1. **The standard's task tables are generated from the rendered task files**
   ([ADR-0004](../../../adr/ADR-0004.md)'s one source), as the CI check matrix
   is generated from the registry.
1. **Check policy lives in `[ci.checks]`.** `[tasks]` holds task wiring only:
   `includes`, `extra_refs` and `command_overrides`. The pip-audit ignore list
   moves from `[tasks.audit] ignore` to `[ci.checks] pip-audit`. That key
   takes a table and never a boolean, because the audit is a standard check
   and stays on.
1. **One coverage task per archetype for Sonar.** The `sonar` job runs the root
   `task test:coverage` in every archetype. `node-lib` then runs
   `task ci:sonar:reports` to print the lcov list, and its duplicate
   `ci:coverage` goes.

## Findings

From the review of 2026-11-05 and the owner's `task <tab>` capture of each
golden cell (`.goldens/tasks/*.out`, gitignored), re-checked on 2026-11-06
against `feature/v1` at `8202297` (E15 closed). Rows 1–7 were fixed by F17.1.

| # | Finding | Fixed by |
| -- | -- | -- |
| 8 | Two naming styles in `ci:` (`ci:release-state` and `ci:release:state` for one idea; `sonar-target`, `docs-publish`, `release-build` against `docs:site`, `lint:secrets`); `ci:lint:secrets` is named as a lint but is CI-only and not in `lint` | S17.2.1 |
| 9 | `node-lib`'s `_sonar.yml` runs `task ci:coverage`, which repeats the tests `task test:coverage` runs; the Python branch of the same file runs the root verb | S17.2.2 |
| 10 | A switched check costs a lookup and an `*_enabled` context key in `tasks/artifacts.py` (licences, secret scan, internal ranges, umbrella release) and again in `cicd/artifacts.py` (umbrella release, internal ranges, scorecard), and an `{% if %}` in each template, not "one registry row plus its task" | S17.2.3 |
| 11 | Check policy has two homes: the licences policy is under `[ci.checks]`, the pip-audit ignore list under `[tasks.audit]` | S17.2.4 |
| 12 | `node-lib`'s `version` printed the docs tooling's version | Fixed by F15.8: root `version` runs `ci:version` (`nx release version`) |
| 13 | Three shapes of `validate` in CI | Accepted: ADR-0016's per-archetype stage mapping |
| 14 | `ci:version` (internal) is the pnpm/Nx toolchain's version primitive, but lives in `tasks/ci.yml`; ADR-0007 puts a toolchain's primitives in its own file | S17.2.1: it moves to `node:version` in `tasks/node.yml` |

## The `ci:` names after F17.2

"Now" is `feature/v1` at `8202297`, after E15. S17.2.1 still re-lists the tree
before it renames anything, and adds any name this table misses.

| Now | After F17.2 | Rendered for |
| -- | -- | -- |
| `ci:sonar-target` | `ci:sonar:target` | all |
| `ci:release-state` | `ci:release:state` | single-package Python |
| `ci:release-source` | `ci:release:source` | single-package Python |
| `ci:release-publish` | `ci:release:publish` | Python |
| `ci:release-build` | `ci:release:build` | `python-lib` |
| `ci:release-sign` | `ci:release:sign` | `python-lib`, `[ci] release = "pypi"` |
| `ci:docs-publish` | `ci:docs:publish` | `python-lib`, `mkdocs` |
| `ci:suite` | `ci:suites` | Python |
| `ci:lint:secrets` | `ci:secret-scan` | all, unless `[ci.checks] secret-scan = false` |
| `ci:requirements` | `ci:internal-ranges` | `python-lib` (two or more members), `node-lib` |
| `ci:affected` | `ci:test` | `node-lib` |
| `ci:has-e2e` | `ci:test:has-e2e` | `node-lib` |
| `ci:playwright` | `ci:test:playwright` | `node-lib` |
| `ci:playwright:deps` | `ci:test:playwright-deps` | `node-lib` |
| `ci:package` | `ci:smoke` | `node-lib` |
| `ci:coverage` | `ci:sonar:reports` (S17.2.2) | `node-lib` |
| `ci:version` (internal) | `node:version` (internal, `tasks/node.yml`) | `node-lib` |
| `ci:validate`, `ci:plan`, `ci:test`, `ci:integration`, `ci:smoke`, `ci:verify-release`, `ci:adapters`, `ci:docs:site`, `ci:release:umbrella`, and `node-lib`'s `ci:release:state`, `:author`, `:tag`, `:verify`, `:push`, `:github`, `:publish`, `:finalize`, `:latest` | unchanged | — |

## ADR-0007's revision

S17.1.6 added decisions 1, 3, 4 and 6 to ADR-0007, with a dated line under
`## Background`. S17.2.5 adds decisions 2 and 7 the same way, and the
consequence that renaming a `ci:` task breaks only kiln's own generated
workflows, which are re-rendered in the same commit.
