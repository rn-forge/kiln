# Ideas

Ideas not yet agreed as this repository's work. An entry takes no ID and no
state, and does not authorize starting anything. An idea that needs more than
its row has a page in this folder, named after the row and linked from its
**Idea** cell. Promoting one moves its page, or its row's summary, into a new
epic or feature and deletes both; a dropped idea's row and page are deleted too.

[Back to the specs](../index.md)

| Idea | Summary | Source |
| -- | -- | -- |
| node-docs-site-assembly | The Node archetypes build their MkDocs site and assemble Compodoc and Storybook under it, as E13's design describes | ADR-0012, 2026-10-01 |
| java-archetype | A Java archetype on the same docs model, with Javadoc assembled under `api/` | ADR-0012, 2026-10-01 |
| local-sonar-scan | A task verb that runs the workspace coverage tests and scans the checked-out branch with the gate awaited, as pykit's `sonar_local.py` does | F6.3, 2026-10-13 |
| rn-forge-devops-non-python | rn-forge-devops plans non-Python workspaces (Nx, Maven) | [ADR-0016](../../adr/ADR-0016.md), 2026-10-18 |
| init-workflow-findings-per-file | `kiln init` and `doctor` report one finding per hand-written workflow beside the generated `ci.yml` ("retire once its jobs are covered"), instead of one `ci.entrypoint` error per line; pykit's adoption trial reported 27 for `main.yml` | pykit adoption trial, 2026-10-18 |
| install-before-tag | `release` installs each package from `git+…@$GITHUB_SHA` in a clean venv and imports it before tagging, in dependency order, and holds back a failure and its dependents; `external-install` then goes away. Today it runs after publishing, so a broken tag is caught but stays published. Worth it once packages have consumers outside the owner's repos, pins move automatically, or a broken tag reaches a consumer | Review of S6.4.7, 2026-10-19 |
| python-lib-version-matrix | A Python-version test matrix for published `python-lib` libraries, as a config key (`[ci] python_versions`) | CI best-practices review, 2026-10-20 |
| merge-group-trigger | A `merge_group` trigger in `ci.yml`, for repositories that use GitHub merge queues | CI best-practices review, 2026-10-20 |
| openssf-scorecard | An OpenSSF Scorecard workflow in generated repositories | CI best-practices review, 2026-10-20 |
| node-lib-ci-security | `node-lib` ([F9.1](../epics/E9-node-archetypes/F9.1-node-lib-hosts-ngkit-ci.md)) equivalents of S4.11.3–S4.11.6: `zizmor` and `actionlint` run without a Python dev group, Dependabot `npm`, `pnpm audit`, build provenance | CI best-practices review, 2026-10-20 |
| kiln-pins-freshness | Keep `cicd/pins.toml` current in kiln, which Dependabot cannot read: a Renovate regex manager, or a `self:pins` check task | CI best-practices review, 2026-10-20 |
| [kiln-simplification](kiln-simplification.md) | Simplify kiln: work-item model out of the enforced standard, self-host before new scope, freeze archetypes until an adopter, slim the specs and ADRs, drop redundant doctor rules | Impartial review, 2026-10-20 |
| pykit-direct-url-pin-check | A pykit-side check of the direct-URL pin rule for repositories that consume rn-forge without kiln; kiln's `rn-forge-deps` covers only repositories built with it. Not a release-1 dependency | [F4.12](../epics/E4-generator/F4.12-task-files-by-owner.md), 2026-10-21 |
