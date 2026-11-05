# E15 — One CI standard for every archetype

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-11-05 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F15.1 — The check model](F15.1-check-model.md) | Closed | release-1 | 4 Closed |
| [F15.2 — The licences check](F15.2-licences-check.md) | New | release-1 | 4 New |
| [F15.3 — The secret scan](F15.3-secret-scan.md) | New | release-1 | 3 New |
| [F15.4 — Internal ranges](F15.4-internal-ranges.md) | New | release-1 | 3 New |
| [F15.5 — The umbrella release](F15.5-umbrella-release.md) | New | release-1 | 3 New |
| [F15.6 — OpenSSF Scorecard](F15.6-scorecard.md) | New | release-1 | 1 New |
| [F15.7 — Repository-owned workflows](F15.7-repo-owned-workflows.md) | New | release-1 | 2 New |
| [F15.8 — Every archetype on the one-workflow contract](F15.8-one-workflow-contract.md) | New | release-1 | 9 New |

<!-- END derived features -->

Every archetype's CI follows one model: one workflow, `ci.yml`, one required
check, `ci-ok`, and a registry of checks, each with a switch, a default, a
`task` verb and, where it needs one, a job. Every archetype runs the same nine
stages. The target state is [the epic's design](design.md); what is built is
[the CI architecture page](../../../architecture/ci.md); the model is
[ADR-0016](../../../adr/ADR-0016.md), revised 2026-11-04.

The epic spans releases and closes once its scope is done. A CI need found later
goes to [the ideas](../../ideas/index.md) and then to a feature under whichever
epic owns that archetype's work. `ci.md` stays the one living document, and its
check matrix is derived from the registry ([F15.1](F15.1-check-model.md)). Each
feature moves its rows from `design.md` to `ci.md` as it closes, and `design.md`
is deleted, with the pointers to it, when the epic closes.

Release 1 carries every feature (owner decision, 2026-11-04). pykit's absorbed
checks ([F15.2](F15.2-licences-check.md)–[F15.6](F15.6-scorecard.md)) must land
before the cutover rehearsal
([S7.2.4](../E7-pykit-release-pin-flip/F7.2-kiln-release-and-config-upgrade.md#s724-run-the-cutover-sop-on-pykit-then-ngkit)),
so pykit's cutover pull request declares no `[[ci.jobs]]` for them.

## Folded-in ideas

Taken from [the ideas](../../ideas/index.md) on 2026-11-04, and their rows
deleted:

| Idea | Taken by |
| -- | -- |
| `ci-security-jobs` | [F15.2](F15.2-licences-check.md), [F15.3](F15.3-secret-scan.md) (the audit already exists) |
| `node-lib-ci-security` | The `node-lib` halves of [F15.2](F15.2-licences-check.md) and [F15.3](F15.3-secret-scan.md); Dependabot `npm` and the `zizmor`/`actionlint` runs already exist (S4.11.3, S4.11.4, S9.1.x). `pnpm audit` is [S15.2.4](F15.2-licences-check.md#s1524-node-lib-runs-pnpm-audit-in-lint); only npm build provenance is deferred |
| `openssf-scorecard` | [F15.6](F15.6-scorecard.md) |
