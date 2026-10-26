# Release 1 — kiln generates and self-hosts the Python and web archetypes

|  |  |
| -- | -- |
| **Status** | in progress |

kiln renders `python-app`, `python-app` + `lifecycle` (the `python-tool` alias)
and `python-lib` from authored templates, creates and ships the FastAPI web
cells (`python-web-api`, and `python-web-app` with an Angular frontend), and
regenerates its own repo. It proves that `python-lib`, with its package docs
sites, can host pykit (F6.1): adopting pykit exercises the scaffolding, seeding,
CI, docs and tasks end to end. The architecture baseline and retiring taskkit
are [release-2](../release-2/index.md).

## Entry criteria

- [Release 0](../release-0/index.md) ships before this one does — **met**
  2026-09-12.
- Before
  [F3.3](../../specs/epics/E3-realign-goldens-and-canon/F3.3-python-tool-is-a-tool.md):
  pykit's lifecycle surface has landed
  ([upstream work](../../specs/index.md#upstream-pins)).
- Order inside the release follows each feature's **Depends on** line.
  [S4.1.4](../../specs/epics/E4-generator/F4.1-checks-by-module.md#s414-the-ci-shape-is-decided)
  — the checks-shape decision — came first and is done
  ([ADR-0006](../../adr/ADR-0006.md)).
- `rn-forge-fastapi` is implemented in pykit, and the web packages resolve from
  outside the pykit workspace (2026-10-04,
  [board](../../specs/index.md#upstream-pins)).
- Django is deferred for both web archetypes; FastAPI is the default and the
  only shipped backend ([ADR-0005](../../adr/ADR-0005.md)).

## Scope

<!-- BEGIN derived scope -->

| Feature | Epic | State |
| -- | -- | -- |
| [F3.1 — Port `golden/python-app` and `golden/python-tool` to the Part E API](../../specs/epics/E3-realign-goldens-and-canon/F3.1-goldens-on-part-e-api.md) | E3 | Closed |
| [F3.2 — Branch pins during pykit stabilization](../../specs/epics/E3-realign-goldens-and-canon/F3.2-branch-pins.md) | E3 | Closed |
| [F3.3 — Make `golden/python-tool` a tool](../../specs/epics/E3-realign-goldens-and-canon/F3.3-python-tool-is-a-tool.md) | E3 | Closed |
| [F3.4 — The canon catches up](../../specs/epics/E3-realign-goldens-and-canon/F3.4-canon-catches-up.md) | E3 | Closed |
| [F4.1 — The checks, organized by module](../../specs/epics/E4-generator/F4.1-checks-by-module.md) | E4 | Closed |
| [F4.2 — The `core` module, the config manager and the module contract](../../specs/epics/E4-generator/F4.2-core-module.md) | E4 | Closed |
| [F4.3 — The concern modules, with templates](../../specs/epics/E4-generator/F4.3-concern-modules.md) | E4 | Closed |
| [F4.4 — The render matrix, and the goldens leave git](../../specs/epics/E4-generator/F4.4-render-matrix.md) | E4 | Closed |
| [F4.5 — CLI](../../specs/epics/E4-generator/F4.5-cli.md) | E4 | Closed |
| [F4.6 — doctor](../../specs/epics/E4-generator/F4.6-doctor.md) | E4 | Closed |
| [F4.7 — Import contracts](../../specs/epics/E4-generator/F4.7-import-contracts.md) | E4 | Closed |
| [F4.8 — Self-hosting](../../specs/epics/E4-generator/F4.8-self-hosting.md) | E4 | Closed |
| [F4.9 — Seeded starter source](../../specs/epics/E4-generator/F4.9-seeded-starter-source.md) | E4 | Closed |
| [F4.10 — TOML formatting](../../specs/epics/E4-generator/F4.10-toml-formatting.md) | E4 | Closed |
| [F4.11 — Generated CI enhancements](../../specs/epics/E4-generator/F4.11-ci-enhancements.md) | E4 | Closed |
| [F4.12 — The task files follow their owners](../../specs/epics/E4-generator/F4.12-task-files-by-owner.md) | E4 | Closed |
| [F5.1 — Library sets, and the modules gain the web shapes](../../specs/epics/E5-web-archetypes/F5.1-web-library-sets-and-modules.md) | E5 | Closed |
| [F5.2 — `kiln new` end to end for the web archetypes](../../specs/epics/E5-web-archetypes/F5.2-kiln-new-web-end-to-end.md) | E5 | Closed |
| [F5.3 — Prove and ship the FastAPI cells](../../specs/epics/E5-web-archetypes/F5.3-shipped-web-cells.md) | E5 | Closed |
| [F6.1 — `python-lib` can host pykit](../../specs/epics/E6-rebuild-the-repos/F6.1-pykit-skeleton.md) | E6 | Closed |
| [F6.3 — The generated CI matches the hardened upstream CI](../../specs/epics/E6-rebuild-the-repos/F6.3-hardened-ci.md) | E6 | Closed |
| [F6.4 — `python-lib` renders pykit's discovered workspace pipeline](../../specs/epics/E6-rebuild-the-repos/F6.4-workspace-pipeline.md) | E6 | Active |
| [F6.6 — `kiln init` leaves the gate runnable](../../specs/epics/E6-rebuild-the-repos/F6.6-init-leaves-gate-runnable.md) | E6 | Active |
| [F6.7 — kiln ships the CI planner as `kiln-devops`](../../specs/epics/E6-rebuild-the-repos/F6.7-kiln-devops.md) | E6 | New |
| [F7.1 — kiln renders and takes pykit by release tag](../../specs/epics/E7-pykit-release-pin-flip/F7.1-tag-pins.md) | E7 | Closed |
| [F7.2 — A tagged kiln release, taken by each repository](../../specs/epics/E7-pykit-release-pin-flip/F7.2-kiln-release-and-config-upgrade.md) | E7 | New |
| [F7.3 — kiln takes pykit's document, template and Markdown helpers](../../specs/epics/E7-pykit-release-pin-flip/F7.3-adopt-pykit-extraction.md) | E7 | New |
| [F7.4 — kiln runs beside a repository, not inside its lock](../../specs/epics/E7-pykit-release-pin-flip/F7.4-kiln-runs-beside-the-repository.md) | E7 | Active |
| [F9.1 — `node-lib` renders ngkit's CI](../../specs/epics/E9-node-archetypes/F9.1-node-lib-hosts-ngkit-ci.md) | E9 | New |
| [F11.1 — The docs checks learn package sites](../../specs/epics/E11-package-docs/F11.1-checks-learn-package-sites.md) | E11 | Closed |
| [F11.2 — `python-lib` repositories carry package docs sites](../../specs/epics/E11-package-docs/F11.2-python-lib-package-sites.md) | E11 | Closed |
| [F11.3 — `kiln generate package`](../../specs/epics/E11-package-docs/F11.3-generate-package.md) | E11 | Closed |
| [F11.4 — The docs rules are one standard, and kiln owns them](../../specs/epics/E11-package-docs/F11.4-cross-repository-rule.md) | E11 | Closed |
| [F11.5 — CI deploys versioned package sites](../../specs/epics/E11-package-docs/F11.5-deploy-package-sites.md) | E11 | Closed |
| [F13.1 — Derived regions, starting with the nav](../../specs/epics/E13-docs-work-model/F13.1-derived-regions.md) | E13 | Closed |
| [F13.2 — The board and Scope regions, and metadata checks](../../specs/epics/E13-docs-work-model/F13.2-board-and-scope.md) | E13 | Closed |
| [F13.3 — The seeded rules and kiln's own docs adopt the model](../../specs/epics/E13-docs-work-model/F13.3-adopt-the-model.md) | E13 | Closed |
| [F13.4 — Ideas live in a folder, one page per large idea](../../specs/epics/E13-docs-work-model/F13.4-ideas-folder.md) | E13 | Closed |
| [F14.1 — Area tabs, the epic ranges and the epic list](../../specs/epics/E14-site-navigation/F14.1-tabbed-navigation.md) | E14 | Closed |
| [F14.2 — Epic and feature summary tables](../../specs/epics/E14-site-navigation/F14.2-work-summaries.md) | E14 | Closed |

<!-- END derived scope -->

## Decisions

- [ADR-0001–ADR-0007](../../adr/index.md) — added 2026-09-13 to 2026-09-15: the
  decision log renumbered and consolidated (`9d96478`). ADR-0006 records
  S4.1.4's CI shape.
- [ADR-0005](../../adr/ADR-0005.md) — updated 2026-09-17: the web selectors are
  `--backend` and `--frontend`, and the shipped web cells are FastAPI and
  FastAPI + Angular, with Django untested (F5.1, F5.3).
- [ADR-0008](../../adr/ADR-0008.md) — added 2026-09-26: only published packages
  get their own docs site (E11).
- [ADR-0009](../../adr/ADR-0009.md) — added 2026-09-26: a repository's specs are
  accepted inside that repository (E11, F11.4).
- [ADR-0003](../../adr/ADR-0003.md) — revision proposed 2026-10-01: generated
  regions, derived from the repository's inputs and never hashed (E13).
- [ADR-0011](../../adr/ADR-0011.md) — accepted 2026-10-01: work is tracked as
  Azure DevOps-shaped work items (E13).
- [ADR-0012](../../adr/ADR-0012.md) — accepted 2026-10-01: every repository
  publishes one MkDocs site, whatever its language (E13).
- [ADR-0013](../../adr/ADR-0013.md) — accepted 2026-10-14: the docs site
  navigates by area tabs, and work pages open with derived summaries (F14.1,
  F14.2).
- [ADR-0014](../../adr/ADR-0014.md) — added 2026-10-14, revised 2026-10-16: a
  library workspace's CI is planned by rn-forge-devops, and its own members
  are exempt from the rn-forge dependency contract (F6.1, F6.4).
- [ADR-0015](../../adr/ADR-0015.md) — added 2026-10-14: `node-lib` renders
  ngkit's CI (E9).
- [ADR-0018](../../adr/ADR-0018.md) — accepted 2026-10-25: rn-forge dependencies
  are version ranges from pykit's package index (F7.3).

## Progress

As of 2026-10-16. E3 shipped 2026-09-15; F4.1–F4.7, F5.1, F5.2, F6.3, F7.1,
F11.1–F11.4, F13.1–F13.3 and F14.1–F14.2 are closed, the last eight on
2026-10-16 when their acceptance blocks passed. F6.3's and F11.2's blocks were
corrected for goldens that now render into `.goldens/working`, and F14.1's
sidebar check found E1 missing from its range until S14.1.3 was corrected. F4.9
closed on 2026-10-24, when its acceptance block passed. F4.8 closed on
2026-10-25, when its pull-request CI run passed, and F4.11, F6.3 and F11.5 the
same day, when their acceptance blocks passed. F6.1 has S6.1.1 open: its fifth
run, after the script was corrected and pykit landed its F16.4, fails only
because pykit's `rn-forge-devops` has no `docs/guides/`; it stays open for
in-place adoption. S6.1.5 is closed, and run 1 of adopting pykit in place, on an
unmerged pykit branch, wrote S6.1.6–S6.1.13: `init` fixes, the shipped `adopt`
prompt proved by a second pykit run, a decision on kiln's area rules, and
S6.1.14's rules taken from pykit's. Rebuilding a far-off repository and porting
it is F6.5, not yet scheduled. F6.4's planner pin was met 2026-10-16
(`rn-forge-devops-v0.1.0`); S6.4.6 and S11.5.1 were added 2026-10-18 to retire
pykit's `main.yml`. S6.4.7 was added the same day, to bring `python-lib`'s
release to [ADR-0016](../../adr/ADR-0016.md)'s rule (default branch only, after
Sonar); it waits on a pykit change to `rn-forge-devops`. F5.3 closed 2026-10-21
on its two shipped cells, approved at kiln `c62d4e2`; its real-application proof
moved to F6.5 (S6.5.3, apollo), which is not in this release. F9.1 has no
stories written ([board](../../specs/index.md#order)).

## Commits

Commits whose subject names a scope ID, newest first:

```bash
git log --format='%h %ad %s' --date=short -E --grep='[FS](3\.[1-4]|4\.[1-9]|5\.[1-3]|6\.[134]|7\.1|9\.1|11\.[1-5]|13\.[1-3]|14\.[12])'
```

- `6feaf37` 2026-09-26 S4.5.9 kiln new assembles in persistent staging
- `c337851` 2026-09-26 E11 package docs sites, ADR-0008/0009, pykit alignment
- `1b31e64` 2026-09-26 F4.5
- `bddc88b` 2026-09-24 release-0 F4.5 - cli
- `a33a795` 2026-09-16 S4.3.2 + Docs refined
- `894bcf8` 2026-09-16 Merge E4 F4.3 S4.3.1: the python module
- `fa876c1` 2026-09-16 E4 (F4.3 S4.3.1): the python module — uv init scaffold,
  .importlinter, check 8a
- `6b2a643` 2026-09-16 E1, E2, E3, E4 (F4.2)

Earlier release-1 work also landed in commits whose subjects name no ID:
`8a64762` and `9d96478` (E3 and the decision log), `873ad47` and `a4a3541`.

## Exit criteria

- E3's acceptance block passes.
- E4's acceptance block passes.
- F11.1–F11.5's acceptance blocks pass. F11.5 was moved here 2026-10-18: it is
  the last blocker to retiring pykit's hand-written `main.yml`.
- E5's acceptance block passes: the FastAPI cells are proved and shipped.
- F6.3's acceptance block passes.
- F7.1's acceptance block passes: kiln pins pykit by release tag.
- F13.1–F13.3's acceptance blocks pass. E12 (F12.1, F12.2) is release-2.
- F14.1–F14.2's acceptance blocks pass.
- F6.1's acceptance block passes: a pykit-shaped repository passes its own gate.
  Nothing in this release is checked inside pykit
  ([ADR-0009](../../adr/ADR-0009.md)).
- F6.4's acceptance block passes: the pykit-shaped repository runs pykit's
  workspace pipeline, and `python-lib` publishes only from the default branch
  after the quality gate (S6.4.7, [ADR-0016](../../adr/ADR-0016.md)). Added
  2026-10-14, when the owner chose to have pykit and ngkit able to adopt kiln
  before release-1 ships.
- E9's `node-lib` features pass their acceptance blocks: an ngkit-shaped
  repository passes its own gate and renders ngkit's CI. Added 2026-10-14.
- Every open question on an in-scope feature is answered, as an ADR or as a
  rejected option recorded on the feature.

## Shipped

Filled at the cut: the kiln commit each exit criterion was proved at, and the
run of each acceptance block.
