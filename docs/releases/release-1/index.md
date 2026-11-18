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

- [Release 0](../release-0/index.md) shipped — **met** 2026-09-12.
- pykit's lifecycle surface has landed
  ([upstream work](../../specs/index.md#upstream-pins)) — before
  [F3.3](../../specs/epics/E3-realign-goldens-and-canon/F3.3-python-tool-is-a-tool.md).
- The CI shape is decided ([ADR-0006](../../adr/ADR-0006.md)).
- `rn-forge-fastapi` is implemented in pykit, and the web packages resolve from
  outside the pykit workspace.
- Django is deferred; FastAPI is the only shipped backend
  ([ADR-0005](../../adr/ADR-0005.md)).

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
| [F6.4 — `python-lib` renders pykit's discovered workspace pipeline](../../specs/epics/E6-rebuild-the-repos/F6.4-workspace-pipeline.md) | E6 | Closed |
| [F6.6 — `kiln init` leaves the gate runnable](../../specs/epics/E6-rebuild-the-repos/F6.6-init-leaves-gate-runnable.md) | E6 | Closed |
| [F6.7 — kiln ships the CI planner as `kiln-devops`](../../specs/epics/E6-rebuild-the-repos/F6.7-kiln-devops.md) | E6 | Closed |
| [F6.8 — The generated CI takes pykit's Release 7](../../specs/epics/E6-rebuild-the-repos/F6.8-pykit-release-7-ci.md) | E6 | Closed |
| [F6.9 — `init` and `config-update` leave an adopted repository alone](../../specs/epics/E6-rebuild-the-repos/F6.9-init-leaves-adopted-repo-alone.md) | E6 | Closed |
| [F6.10 — A task verb scans the checked-out branch on SonarCloud](../../specs/epics/E6-rebuild-the-repos/F6.10-local-sonar-scan.md) | E6 | Closed |
| [F6.11 — The library-workspace release job runs in `ci.yml`](../../specs/epics/E6-rebuild-the-repos/F6.11-pypi-release-in-ci-yml.md) | E6 | Closed |
| [F6.12 — `umbrella` releases only the newest shipped release](../../specs/epics/E6-rebuild-the-repos/F6.12-umbrella-releases-only-the-newest.md) | E6 | Closed |
| [F7.1 — kiln renders and takes pykit by release tag](../../specs/epics/E7-pykit-release-pin-flip/F7.1-tag-pins.md) | E7 | Closed |
| [F7.2 — A tagged kiln release, taken by each repository](../../specs/epics/E7-pykit-release-pin-flip/F7.2-kiln-release-and-config-upgrade.md) | E7 | Active |
| [F7.3 — kiln takes pykit's document, template and Markdown helpers](../../specs/epics/E7-pykit-release-pin-flip/F7.3-adopt-pykit-extraction.md) | E7 | Closed |
| [F7.4 — kiln runs beside a repository, not inside its lock](../../specs/epics/E7-pykit-release-pin-flip/F7.4-kiln-runs-beside-the-repository.md) | E7 | Closed |
| [F7.5 — kiln takes pykit from PyPI](../../specs/epics/E7-pykit-release-pin-flip/F7.5-pykit-from-pypi.md) | E7 | Closed |
| [F7.6 — The `python-lib` release job publishes to PyPI](../../specs/epics/E7-pykit-release-pin-flip/F7.6-release-to-pypi.md) | E7 | Closed |
| [F7.7 — kiln installs as a standalone tool, from any ref](../../specs/epics/E7-pykit-release-pin-flip/F7.7-kiln-installs-as-a-tool.md) | E7 | New |
| [F9.1 — `node-lib` renders ngkit's CI](../../specs/epics/E9-node-archetypes/F9.1-node-lib-hosts-ngkit-ci.md) | E9 | Closed |
| [F9.2 — One node scaffold](../../specs/epics/E9-node-archetypes/F9.2-one-node-scaffold.md) | E9 | Closed |
| [F9.3 — Node CI holds for ngkit and for every `node-lib`](../../specs/epics/E9-node-archetypes/F9.3-node-ci-holds-for-every-node-lib.md) | E9 | Closed |
| [F9.4 — The node CI helpers run from `kiln-devops`](../../specs/epics/E9-node-archetypes/F9.4-node-helpers-in-kiln-devops.md) | E9 | Closed |
| [F9.5 — What ngkit's cutover found about node-lib releases](../../specs/epics/E9-node-archetypes/F9.5-node-lib-release-findings.md) | E9 | Closed |
| [F9.6 — Nx Cloud agents can run `task`](../../specs/epics/E9-node-archetypes/F9.6-nx-cloud-agents-run-task.md) | E9 | Closed |
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
| [F15.1 — The check model](../../specs/epics/E15-ci-standard/F15.1-check-model.md) | E15 | Closed |
| [F15.2 — The licences check](../../specs/epics/E15-ci-standard/F15.2-licences-check.md) | E15 | Closed |
| [F15.3 — The secret scan](../../specs/epics/E15-ci-standard/F15.3-secret-scan.md) | E15 | Closed |
| [F15.4 — Internal ranges](../../specs/epics/E15-ci-standard/F15.4-internal-ranges.md) | E15 | Closed |
| [F15.5 — The umbrella release](../../specs/epics/E15-ci-standard/F15.5-umbrella-release.md) | E15 | Closed |
| [F15.6 — OpenSSF Scorecard](../../specs/epics/E15-ci-standard/F15.6-scorecard.md) | E15 | Closed |
| [F15.7 — Repository-owned workflows](../../specs/epics/E15-ci-standard/F15.7-repo-owned-workflows.md) | E15 | Closed |
| [F15.8 — Every archetype on the one-workflow contract](../../specs/epics/E15-ci-standard/F15.8-one-workflow-contract.md) | E15 | Closed |
| [F16.1 — Opinionated `init`](../../specs/epics/E16-init-adopts-by-overwrite/F16.1-opinionated-init.md) | E16 | Closed |
| [F16.2 — kiln owns `mkdocs.yml`](../../specs/epics/E16-init-adopts-by-overwrite/F16.2-kiln-owns-mkdocs.md) | E16 | Closed |
| [F16.3 — The cutover SOP](../../specs/epics/E16-init-adopts-by-overwrite/F16.3-cutover-sop.md) | E16 | Closed |
| [F16.4 — Generated-file hygiene](../../specs/epics/E16-init-adopts-by-overwrite/F16.4-generated-file-hygiene.md) | E16 | Closed |
| [F16.5 — Rebuild an existing repository on kiln, and port it](../../specs/epics/E16-init-adopts-by-overwrite/F16.5-rebuild-and-port.md) | E16 | Active |
| [F16.6 — What the cutover rehearsals found](../../specs/epics/E16-init-adopts-by-overwrite/F16.6-cutover-rehearsal-findings.md) | E16 | Closed |
| [F16.7 — What the cutover found](../../specs/epics/E16-init-adopts-by-overwrite/F16.7-cutover-findings.md) | E16 | Closed |
| [F16.8 — Retire `kiln init`](../../specs/epics/E16-init-adopts-by-overwrite/F16.8-retire-kiln-init.md) | E16 | Closed |
| [F16.9 — What the overlay cutovers found](../../specs/epics/E16-init-adopts-by-overwrite/F16.9-overlay-cutover-findings.md) | E16 | Closed |
| [F16.10 — Agent instructions live in AGENTS.md](../../specs/epics/E16-init-adopts-by-overwrite/F16.10-agent-instructions-in-agents-md.md) | E16 | Closed |
| [F17.1 — The task surface says what it is](../../specs/epics/E17-task-standard/F17.1-task-surface.md) | E17 | Closed |
| [F17.2 — One grammar for the CI surface, and one home for check policy](../../specs/epics/E17-task-standard/F17.2-ci-task-grammar.md) | E17 | Closed |
| [F17.3 — A faster gate](../../specs/epics/E17-task-standard/F17.3-a-faster-gate.md) | E17 | Closed |
| [F18.1 — Tests named by behaviour](../../specs/epics/E18-kiln-simplification/F18.1-tests-named-by-behaviour.md) | E18 | Closed |
| [F18.2 — Spec IDs out of the code and the docs outside the specs](../../specs/epics/E18-kiln-simplification/F18.2-ids-out-of-code-and-docs.md) | E18 | Closed |
| [F18.3 — One epic per area](../../specs/epics/E18-kiln-simplification/F18.3-area-epics.md) | E18 | New |
| [F18.4 — `feature/v1` lands on `main` as one commit](../../specs/epics/E18-kiln-simplification/F18.4-one-commit-on-main.md) | E18 | New |
| [F18.5 — Tests that survive a refactor](../../specs/epics/E18-kiln-simplification/F18.5-tests-survive-a-refactor.md) | E18 | Closed |
| [F18.6 — `commands` is a package, one module per command](../../specs/epics/E18-kiln-simplification/F18.6-commands-package.md) | E18 | Closed |
| [F18.7 — One owner per concept](../../specs/epics/E18-kiln-simplification/F18.7-one-owner-per-concept.md) | E18 | Closed |
| [F18.8 — Modules meet only through composition](../../specs/epics/E18-kiln-simplification/F18.8-modules-meet-through-composition.md) | E18 | Closed |
| [F18.9 — Large files split by job](../../specs/epics/E18-kiln-simplification/F18.9-large-files-split.md) | E18 | Closed |
| [F18.12 — The review defects release 1 takes](../../specs/epics/E18-kiln-simplification/F18.12-release-1-review-defects.md) | E18 | Closed |
| [F18.13 — Build briefs outside the record](../../specs/epics/E18-kiln-simplification/F18.13-build-briefs-outside-the-record.md) | E18 | Closed |
| [F18.14 — A kiln pin is a commit](../../specs/epics/E18-kiln-simplification/F18.14-a-pin-is-a-commit.md) | E18 | Closed |
| [F19.1 — YAML has a formatter, and kiln's own files pass it](../../specs/epics/E19-formatting-standard/F19.1-yaml-formatter.md) | E19 | Closed |
| [F19.2 — The nav block is a plain `ManagedBlock`](../../specs/epics/E19-formatting-standard/F19.2-nav-block-end-indent.md) | E19 | Closed |

<!-- END derived scope -->

## Decisions

- [ADR-0001–ADR-0007](../../adr/index.md) — 2026-09-13 to 2026-09-15: the
  decision log renumbered and consolidated.
- [ADR-0005](../../adr/ADR-0005.md) — 2026-09-17: the web selectors are
  `--backend` and `--frontend`; the shipped cells are FastAPI and FastAPI +
  Angular.
- [ADR-0008](../../adr/ADR-0008.md) — 2026-09-26: only published packages get
  their own docs site.
- [ADR-0009](../../adr/ADR-0009.md) — 2026-09-26: a repository's specs are
  accepted inside that repository.
- [ADR-0003](../../adr/ADR-0003.md) — 2026-10-01: generated regions, derived
  from the repository's inputs and never hashed.
- [ADR-0011](../../adr/ADR-0011.md) — 2026-10-01: work is tracked as Azure
  DevOps-shaped work items.
- [ADR-0012](../../adr/ADR-0012.md) — 2026-10-01: every repository publishes one
  MkDocs site.
- [ADR-0013](../../adr/ADR-0013.md) — 2026-10-14: the docs site navigates by
  area tabs, and work pages open with derived summaries.
- [ADR-0014](../../adr/ADR-0014.md) — 2026-10-14, revised 2026-10-16: a library
  workspace's CI is planned by rn-forge-devops.
- [ADR-0015](../../adr/ADR-0015.md) — 2026-10-14: `node-lib` renders ngkit's CI.
- [ADR-0017](../../adr/ADR-0017.md) — 2026-10-22, revised 2026-10-26: the CI
  planner ships inside kiln as `kiln-devops`.
- [ADR-0018](../../adr/ADR-0018.md) — 2026-10-25, revised 2026-10-31: rn-forge
  dependencies are version ranges from PyPI.
- [ADR-0016](../../adr/ADR-0016.md) — revised 2026-11-04: one CI standard for
  every archetype, with a check registry.

## Progress

As of 2026-11-17, every feature in scope is closed except F7.2 (the tagged
release), F16.5 and the open E18 features. The `v0.1.0` tag is held until pykit
and ngkit have cut over on `feature/v1` and the E18 features land. Next: the
remaining E18 features, then the cutover and the tag.

## Commits

Commits whose subject names a scope ID, newest first:

```bash
git log --format='%h %ad %s' --date=short -E --grep='[FS](3\.[1-4]|4\.[1-9]|5\.[1-3]|6\.[134]|7\.1|9\.1|11\.[1-5]|13\.[1-3]|14\.[12])'
```

## Exit criteria

- E3, E4 and E5 acceptance blocks pass: the FastAPI cells are proved and
  shipped.
- F11.1–F11.5, F13.1–F13.3 and F14.1–F14.2 acceptance blocks pass.
- F6.1's acceptance block passes: a pykit-shaped repository passes its own gate
  ([ADR-0009](../../adr/ADR-0009.md)).
- F6.3, F6.4, F6.7, F6.8 and F6.9 acceptance blocks pass: the generated CI is
  pykit's workspace pipeline, and `init` and `apply` write no starter source
  into an adopted repository.
- F7.1, F7.5 and F7.6 acceptance blocks pass, F7.6's two run checks excepted:
  they follow the cut.
- E9's `node-lib` features pass their acceptance blocks: an ngkit-shaped
  repository passes its own gate and renders ngkit's CI.
- Every open question on an in-scope feature is answered, as an ADR or as a
  rejected option recorded on the feature.
- The cutover SOP, run on pykit and then ngkit, leaves no open absorb row. The
  owner holds the tag until then.
- [E15](../../specs/epics/E15-ci-standard/index.md)'s acceptance blocks pass:
  every archetype runs the one stage vocabulary from `ci.yml`.
- [E16](../../specs/epics/E16-init-adopts-by-overwrite/index.md)'s acceptance
  blocks pass: `init` is retired and the cutover SOP is the overlay
  ([ADR-0019](../../adr/ADR-0019.md)).

## Shipped

Proved 2026-11-03 at `be9429e` on `feature/v1`. kiln's CI at that commit:
[run 41590472355](https://github.com/rn-forge/kiln/actions/runs/41590472355),
green with Sonar's quality gate. The tag is held for the cutover.

Each block ran locally in a clean worktree after `task setup`. F6.1 and F6.7 ran
with pykit's `feature/release-8`, which carries the rn-forge-devops guides page.
Exit `0` for every block:

| Exit criterion | Blocks |
| -- | -- |
| E3, E4, E5 | E3, E4, E5 |
| E4's features | F4.2–F4.9, F4.11, F4.12 |
| E5's features | F5.1–F5.3 |
| F6.1, F6.3, F6.4, F6.6–F6.9 | F6.1, F6.3, F6.4, F6.6, F6.7, F6.8, F6.9 |
| F7.1, F7.4–F7.6 | F7.1, F7.4, F7.5, F7.6 |
| E9's `node-lib` features | F9.1, F9.2, F9.3 |
| F11.1–F11.5, and E11 | F11.1–F11.5, E11 |
| F13.1–F13.3 | F13.1, F13.2, F13.3 |
| F14.1–F14.2 | F14.1, F14.2 |

**Not re-run, superseded:** F3.1–F3.4 by E3's block; F4.1 by E4's block; F7.3 by
F7.5's. F4.10, F7.2 and F13.4 have no block.

**GitHub runs the shaped repositories ask for:**

- pykit-shape:
  [run 41549190853](https://github.com/rn-forge/pykit-shape/actions/runs/41549190853).
- ngkit-shape:
  [run 41564051289](https://github.com/rn-forge/ngkit-shape/actions/runs/41564051289),
  attempt 2.

**Checked after the cut:**

- On kiln's first default-branch push after the merge, the `release` job's
  `release-state` step reports the version's state.
- pykit's cutover dispatches a `testpypi` run, and its next push to `main`
  uploads to pypi.org.
