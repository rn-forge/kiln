# Release 1 — kiln generates and self-hosts the Python and web archetypes

|  |  |
| -- | -- |
| **Status** | in progress |

kiln renders `python-app`, `python-app` + `lifecycle` (the `python-tool` alias)
and `python-lib` from authored templates, creates and ships the FastAPI web
cells (`python-web-api`, and `python-web-app` with an Angular frontend), and
regenerates its own repo. It proves that `python-lib`, with its package docs
sites, can host pykit (F6.1): adopting pykit exercises the scaffolding, seeding,
CI, docs and tasks end to end. The architecture baseline, package-site deploys
and retiring taskkit are [release-2](../release-2/index.md).

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
| [F4.6 — doctor](../../specs/epics/E4-generator/F4.6-doctor.md) | E4 | New |
| [F4.7 — Import contracts](../../specs/epics/E4-generator/F4.7-import-contracts.md) | E4 | New |
| [F4.8 — Self-hosting](../../specs/epics/E4-generator/F4.8-self-hosting.md) | E4 | New |
| [F4.9 — Seeded starter source](../../specs/epics/E4-generator/F4.9-seeded-starter-source.md) | E4 | Active |
| [F5.1 — Library sets, and the modules gain the web shapes](../../specs/epics/E5-web-archetypes/F5.1-web-library-sets-and-modules.md) | E5 | Closed |
| [F5.2 — `kiln new` end to end for the web archetypes](../../specs/epics/E5-web-archetypes/F5.2-kiln-new-web-end-to-end.md) | E5 | Closed |
| [F5.3 — Prove and ship the FastAPI cells](../../specs/epics/E5-web-archetypes/F5.3-shipped-web-cells.md) | E5 | Active |
| [F6.1 — `python-lib` can host pykit](../../specs/epics/E6-rebuild-the-repos/F6.1-pykit-skeleton.md) | E6 | New |
| [F6.3 — The generated CI matches the hardened upstream CI](../../specs/epics/E6-rebuild-the-repos/F6.3-hardened-ci.md) | E6 | New |
| [F6.4 — `python-lib` renders pykit's discovered workspace pipeline](../../specs/epics/E6-rebuild-the-repos/F6.4-workspace-pipeline.md) | E6 | New |
| [F7.1 — kiln renders and takes pykit by release tag](../../specs/epics/E7-pykit-release-pin-flip/F7.1-tag-pins.md) | E7 | New |
| [F9.1 — `node-lib` renders ngkit's CI](../../specs/epics/E9-node-archetypes/F9.1-node-lib-hosts-ngkit-ci.md) | E9 | New |
| [F11.1 — The docs checks learn package sites](../../specs/epics/E11-package-docs/F11.1-checks-learn-package-sites.md) | E11 | Closed |
| [F11.2 — `python-lib` repositories carry package docs sites](../../specs/epics/E11-package-docs/F11.2-python-lib-package-sites.md) | E11 | New |
| [F11.3 — `kiln generate package`](../../specs/epics/E11-package-docs/F11.3-generate-package.md) | E11 | New |
| [F11.4 — The docs rules are one standard, and kiln owns them](../../specs/epics/E11-package-docs/F11.4-cross-repository-rule.md) | E11 | Closed |
| [F13.1 — Derived regions, starting with the nav](../../specs/epics/E13-docs-work-model/F13.1-derived-regions.md) | E13 | Closed |
| [F13.2 — The board and Scope regions, and metadata checks](../../specs/epics/E13-docs-work-model/F13.2-board-and-scope.md) | E13 | Closed |
| [F13.3 — The seeded rules and kiln's own docs adopt the model](../../specs/epics/E13-docs-work-model/F13.3-adopt-the-model.md) | E13 | Closed |
| [F14.1 — Area tabs, the epic ranges and the epic list](../../specs/epics/E14-site-navigation/F14.1-tabbed-navigation.md) | E14 | New |
| [F14.2 — Epic and feature summary tables](../../specs/epics/E14-site-navigation/F14.2-work-summaries.md) | E14 | New |

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
- [ADR-0011](../../adr/ADR-0011.md) — proposed 2026-10-01: work is tracked as
  Azure DevOps-shaped work items (E13).
- [ADR-0012](../../adr/ADR-0012.md) — proposed 2026-10-01: every repository
  publishes one MkDocs site, whatever its language (E13).
- [ADR-0014](../../adr/ADR-0014.md) — added 2026-10-14, revised 2026-10-16: a
  library workspace's CI is planned by rn-forge-devops, and its own members
  are exempt from the rn-forge dependency contract (F6.1, F6.4).
- [ADR-0015](../../adr/ADR-0015.md) — added 2026-10-14: `node-lib` renders
  ngkit's CI (E9).

## Progress

E3 shipped 2026-09-15. F4.1, F4.2, F5.1 and F5.2 are done (F5.2 apart from the
deferred Django scaffold); F4.9 closed on 2026-10-13. F4.3 waits only on S4.3.6,
the owner's Sonar decisions; F4.5 closed on 2026-10-13; F5.3 has S5.3.7,
S5.3.2–S5.3.4 left. Next are F11.2–F11.3 (F4.4's `python-lib` cell needs
S11.3.1), then F4.4, then F4.6–F4.8. F6.1 follows F11.1–F11.3
([board](../../specs/index.md#order)).

## Commits

Commits whose subject names a scope ID, newest first:

```bash
git log --format='%h %ad %s' --date=short -E --grep='[FS](3\.[1-4]|4\.[1-9]|5\.[1-3]|6\.1|11\.[1-4])'
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
- F11.1–F11.4's acceptance blocks pass. F11.5 is release-2.
- F12.1's acceptance block passes. F12.2 is release-2.
- F6.1's acceptance block passes: a pykit-shaped repository passes its own gate.
  Nothing in this release is checked inside pykit
  ([ADR-0009](../../adr/ADR-0009.md)).
- F6.4's acceptance block passes: the pykit-shaped repository runs pykit's
  workspace pipeline. Added 2026-10-14, when the owner chose to have pykit and
  ngkit able to adopt kiln before release-1 ships.
- E9's `node-lib` features pass their acceptance blocks: an ngkit-shaped
  repository passes its own gate and renders ngkit's CI. Added 2026-10-14.
- Every open question on an in-scope feature is answered, as an ADR or as a
  rejected option recorded on the feature.

## Shipped

Filled at the cut: the kiln commit each exit criterion was proved at, and the
run of each acceptance block.
