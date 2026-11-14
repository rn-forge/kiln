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
| [F6.4 — `python-lib` renders pykit's discovered workspace pipeline](../../specs/epics/E6-rebuild-the-repos/F6.4-workspace-pipeline.md) | E6 | Closed |
| [F6.6 — `kiln init` leaves the gate runnable](../../specs/epics/E6-rebuild-the-repos/F6.6-init-leaves-gate-runnable.md) | E6 | Closed |
| [F6.7 — kiln ships the CI planner as `kiln-devops`](../../specs/epics/E6-rebuild-the-repos/F6.7-kiln-devops.md) | E6 | Closed |
| [F6.8 — The generated CI takes pykit's Release 7](../../specs/epics/E6-rebuild-the-repos/F6.8-pykit-release-7-ci.md) | E6 | Closed |
| [F6.9 — `init` and `config-update` leave an adopted repository alone](../../specs/epics/E6-rebuild-the-repos/F6.9-init-leaves-adopted-repo-alone.md) | E6 | Closed |
| [F6.10 — A task verb scans the checked-out branch on SonarCloud](../../specs/epics/E6-rebuild-the-repos/F6.10-local-sonar-scan.md) | E6 | Closed |
| [F6.11 — The library-workspace release job runs in `ci.yml`](../../specs/epics/E6-rebuild-the-repos/F6.11-pypi-release-in-ci-yml.md) | E6 | Closed |
| [F6.12 — `umbrella` releases only the newest shipped release](../../specs/epics/E6-rebuild-the-repos/F6.12-umbrella-releases-only-the-newest.md) | E6 | New |
| [F7.1 — kiln renders and takes pykit by release tag](../../specs/epics/E7-pykit-release-pin-flip/F7.1-tag-pins.md) | E7 | Closed |
| [F7.2 — A tagged kiln release, taken by each repository](../../specs/epics/E7-pykit-release-pin-flip/F7.2-kiln-release-and-config-upgrade.md) | E7 | Active |
| [F7.3 — kiln takes pykit's document, template and Markdown helpers](../../specs/epics/E7-pykit-release-pin-flip/F7.3-adopt-pykit-extraction.md) | E7 | Closed |
| [F7.4 — kiln runs beside a repository, not inside its lock](../../specs/epics/E7-pykit-release-pin-flip/F7.4-kiln-runs-beside-the-repository.md) | E7 | Closed |
| [F7.5 — kiln takes pykit from PyPI](../../specs/epics/E7-pykit-release-pin-flip/F7.5-pykit-from-pypi.md) | E7 | Closed |
| [F7.6 — The `python-lib` release job publishes to PyPI](../../specs/epics/E7-pykit-release-pin-flip/F7.6-release-to-pypi.md) | E7 | Closed |
| [F9.1 — `node-lib` renders ngkit's CI](../../specs/epics/E9-node-archetypes/F9.1-node-lib-hosts-ngkit-ci.md) | E9 | Closed |
| [F9.2 — One node scaffold](../../specs/epics/E9-node-archetypes/F9.2-one-node-scaffold.md) | E9 | Closed |
| [F9.3 — Node CI holds for ngkit and for every `node-lib`](../../specs/epics/E9-node-archetypes/F9.3-node-ci-holds-for-every-node-lib.md) | E9 | Closed |
| [F9.4 — The node CI helpers run from `kiln-devops`](../../specs/epics/E9-node-archetypes/F9.4-node-helpers-in-kiln-devops.md) | E9 | Closed |
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
| [F16.6 — What the cutover rehearsals found](../../specs/epics/E16-init-adopts-by-overwrite/F16.6-cutover-rehearsal-findings.md) | E16 | Closed |
| [F16.7 — What the cutover found](../../specs/epics/E16-init-adopts-by-overwrite/F16.7-cutover-findings.md) | E16 | Closed |
| [F16.8 — Retire `kiln init`](../../specs/epics/E16-init-adopts-by-overwrite/F16.8-retire-kiln-init.md) | E16 | Closed |
| [F16.9 — What the overlay cutovers found](../../specs/epics/E16-init-adopts-by-overwrite/F16.9-overlay-cutover-findings.md) | E16 | Closed |
| [F16.10 — Agent instructions live in AGENTS.md](../../specs/epics/E16-init-adopts-by-overwrite/F16.10-agent-instructions-in-agents-md.md) | E16 | Closed |
| [F17.1 — The task surface says what it is](../../specs/epics/E17-task-standard/F17.1-task-surface.md) | E17 | Closed |
| [F17.2 — One grammar for the CI surface, and one home for check policy](../../specs/epics/E17-task-standard/F17.2-ci-task-grammar.md) | E17 | Closed |
| [F17.3 — A faster gate](../../specs/epics/E17-task-standard/F17.3-a-faster-gate.md) | E17 | Active |
| [F18.1 — Tests named by behaviour](../../specs/epics/E18-kiln-simplification/F18.1-tests-named-by-behaviour.md) | E18 | New |
| [F18.2 — Spec IDs out of the code and the docs outside the specs](../../specs/epics/E18-kiln-simplification/F18.2-ids-out-of-code-and-docs.md) | E18 | New |
| [F18.3 — One epic per area](../../specs/epics/E18-kiln-simplification/F18.3-area-epics.md) | E18 | New |
| [F18.4 — `feature/v1` lands on `main` as one commit](../../specs/epics/E18-kiln-simplification/F18.4-one-commit-on-main.md) | E18 | New |
| [F18.5 — Tests that survive a refactor](../../specs/epics/E18-kiln-simplification/F18.5-tests-survive-a-refactor.md) | E18 | New |
| [F18.6 — `commands` is a package, one module per command](../../specs/epics/E18-kiln-simplification/F18.6-commands-package.md) | E18 | New |
| [F18.7 — One owner per concept](../../specs/epics/E18-kiln-simplification/F18.7-one-owner-per-concept.md) | E18 | New |
| [F18.8 — Modules meet only through composition](../../specs/epics/E18-kiln-simplification/F18.8-modules-meet-through-composition.md) | E18 | New |
| [F18.9 — Large files split by job](../../specs/epics/E18-kiln-simplification/F18.9-large-files-split.md) | E18 | New |
| [F18.12 — The review defects release 1 takes](../../specs/epics/E18-kiln-simplification/F18.12-release-1-review-defects.md) | E18 | New |
| [F18.13 — Build briefs outside the record](../../specs/epics/E18-kiln-simplification/F18.13-build-briefs-outside-the-record.md) | E18 | New |
| [F18.14 — A kiln pin is a commit](../../specs/epics/E18-kiln-simplification/F18.14-a-pin-is-a-commit.md) | E18 | New |
| [F19.1 — YAML has a formatter, and kiln's own files pass it](../../specs/epics/E19-formatting-standard/F19.1-yaml-formatter.md) | E19 | Closed |
| [F19.2 — The nav block is a plain `ManagedBlock`](../../specs/epics/E19-formatting-standard/F19.2-nav-block-end-indent.md) | E19 | New |

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
- [ADR-0017](../../adr/ADR-0017.md) — added 2026-10-22, revised 2026-10-26: the
  CI planner ships inside kiln as `kiln-devops`, reached through the
  `[kiln] ref` pin and not the repository's lock (F6.7, F7.4).
- [ADR-0018](../../adr/ADR-0018.md) — accepted 2026-10-25, revised 2026-10-31:
  rn-forge dependencies are version ranges from PyPI (F7.3, F7.5).
- [ADR-0016](../../adr/ADR-0016.md) — revised 2026-11-04: one CI standard for
  every archetype, with a check registry and `[ci.checks]` (E15).
- Owner decisions, 2026-11-04: E15 and E16 are release-1 scope; the tag stays
  held until they land and S7.2.4's cutover runs on them.
- Owner decisions, 2026-10-31, after pykit's Release 7: F7.5 moves here from
  release 2, and F6.8 is added; pykit keeps its security jobs as `[[ci.jobs]]`
  entries; the web archetypes allow `rn-forge-auth`; F7.6's two run checks
  follow the cut; the tag is `v0.1.0`, distributed by git.

## Progress

As of 2026-11-07, F16.6 (what the cutover rehearsals found) has 8 stories closed
and 5 new, S16.6.9 to S16.6.13, from S7.2.4's rehearsal run 4 on pykit and
ngkit. Owner decision: pykit and ngkit cut over on `feature/v1` before the tag,
so that kiln keeps being refined from their findings; the `v0.1.0` tag follows.
E18 is not yet re-sequenced; the owner question, whether to move E18 after the
tag, is open.

As of 2026-11-04, E15 (one CI standard) and E16 (`init` adopts by overwrite)
joined the scope; the tag waits for both and for S7.2.4 run on them. As of
2026-11-03, every in-scope feature was closed except F7.2: S7.2.1 is done
([Shipped](#shipped)), and S7.2.4's cutover rehearsals hold the tag (S7.2.2).
E4, E9 and E11 closed the same day. The rest of this section is the record as of
2026-10-16.

As of 2026-10-16. E3 shipped 2026-09-15; F4.1–F4.7, F5.1, F5.2, F6.3, F7.1,
F11.1–F11.4, F13.1–F13.3 and F14.1–F14.2 are closed, the last eight on
2026-10-16 when their acceptance blocks passed. F6.3's and F11.2's blocks were
corrected for goldens that now render into `.goldens/working`, and F14.1's
sidebar check found E1 missing from its range until S14.1.3 was corrected. F4.9
closed on 2026-10-24, when its acceptance block passed. F4.8 closed on
2026-10-25, when its pull-request CI run passed, and F4.11, F6.3 and F11.5 the
same day, when their acceptance blocks passed. F7.3 and F7.4 closed on
2026-10-26, when their acceptance blocks passed. F6.1 has S6.1.1 open: its fifth
run, after the script was corrected and pykit landed its F16.4, fails only
because pykit's `rn-forge-devops` has no `docs/guides/`; it stays open for
in-place adoption. S6.1.5 is closed, and run 1 of adopting pykit in place, on an
unmerged pykit branch, wrote S6.1.6–S6.1.13: `init` fixes, the shipped `adopt`
prompt proved by a second pykit run, a decision on kiln's area rules, and
S6.1.14's rules taken from pykit's. Rebuilding a far-off repository and porting
it is F16.5 (was F6.5), not yet scheduled. F6.4's planner pin was met 2026-10-16
(`rn-forge-devops-v0.1.0`); S6.4.6 and S11.5.1 were added 2026-10-18 to retire
pykit's `main.yml`. S6.4.7 was added the same day, to bring `python-lib`'s
release to [ADR-0016](../../adr/ADR-0016.md)'s rule (default branch only, after
Sonar); it waits on a pykit change to `rn-forge-devops`. F5.3 closed 2026-10-21
on its two shipped cells, approved at kiln `c62d4e2`; its real-application proof
moved to F16.5 (was F6.5; S16.5.3, apollo), which is not in this release. F9.1
has no stories written ([board](../../specs/index.md#order)).

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
- F6.7, F6.8, F7.5 and F7.6's acceptance blocks pass, F7.6's two run checks
  excepted: they need pykit's cutover and follow the cut. Added 2026-10-31.
- F6.9's acceptance block passes: `init` and `apply` write no starter source
  into a repository kiln adopts, which pykit's cutover requires of the tag.
  Added 2026-11-01.
- Every open question on an in-scope feature is answered, as an ADR or as a
  rejected option recorded on the feature.
- [S7.2.4](../../specs/epics/E7-pykit-release-pin-flip/F7.2-kiln-release-and-config-upgrade.md#s724-run-the-cutover-sop-on-pykit-then-ngkit):
  the cutover SOP, run on pykit and then ngkit, leaves no open absorb row. The
  owner holds the tag until then. Added 2026-11-02, rewritten 2026-11-04.
- [E15](../../specs/epics/E15-ci-standard/index.md)'s acceptance blocks pass,
  F15.8's included: every archetype runs the one stage vocabulary from
  `ci.yml`. Added 2026-11-04: pykit's cutover declares no `[[ci.jobs]]` for a
  check E15 covers.
- [E16](../../specs/epics/E16-init-adopts-by-overwrite/index.md)'s acceptance
  blocks pass: `init` adopts by overwrite and the cutover SOP exists. Added
  2026-11-04. Revised 2026-11-09: `init` is retired and the SOP is the overlay
  ([ADR-0019](../../adr/ADR-0019.md),
  [F16.8](../../specs/epics/E16-init-adopts-by-overwrite/F16.8-retire-kiln-init.md)).

## Shipped

Proved 2026-11-03 at `be9429e` on `feature/v1`
([S7.2.1](../../specs/epics/E7-pykit-release-pin-flip/F7.2-kiln-release-and-config-upgrade.md#s721-the-release-1-exit-criteria-hold)).
kiln's CI at that commit:
[run 41590472355](https://github.com/rn-forge/kiln/actions/runs/41590472355),
green with Sonar's quality gate. The tag is held for S7.2.4.

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

These blocks first failed on a line that later work had made stale: E3, E4,
F4.3, F4.5, F5.2, F6.1, and earlier in the run F4.4, F4.7, F4.12, F5.1, F6.3,
F11.1, F11.4, F13.1–F13.3, F14.1, F14.2. Each line was corrected with an
*Updated (S7.2.1)* note on its page, and the block re-run to exit `0`. The real
defects the runs found became stories and closed before the final run:
[S4.5.11](../../specs/epics/E4-generator/F4.5-cli.md) (`kiln new` runs
`git init`), [S4.5.12](../../specs/epics/E4-generator/F4.5-cli.md) (no `main()`
stub in app packages) and
[S6.7.7](../../specs/epics/E6-rebuild-the-repos/F6.7-kiln-devops.md)
(`kiln-devops` checks its arguments, which cleared Sonar's security gate).

**Not re-run, superseded:** F3.1–F3.4 by E3's block; F4.1 by E4's block; F7.3 by
F7.5's. F4.10, F7.2 and F13.4 have no block.

**GitHub runs the shaped repositories ask for:**

- S6.4.5, pykit-shape:
  [run 41549190853](https://github.com/rn-forge/pykit-shape/actions/runs/41549190853).
- S9.1.6, ngkit-shape:
  [run 41564051289](https://github.com/rn-forge/ngkit-shape/actions/runs/41564051289),
  attempt 2.

**Checked after the cut:**

- F6.7, S6.7.5: on kiln's first default-branch push after the merge, the
  `release` job's `release-state` step reports the version's state.
- F7.6: pykit's cutover dispatches a `testpypi` run, and its next push to `main`
  uploads to pypi.org (owner decision, 2026-10-31).
