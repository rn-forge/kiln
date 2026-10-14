# E4 — The generator

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-09-16 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F4.1 — The checks, organized by module](F4.1-checks-by-module.md) | Closed | release-1 | 4 Closed |
| [F4.2 — The `core` module, the config manager and the module contract](F4.2-core-module.md) | Closed | release-1 | 3 Closed |
| [F4.3 — The concern modules, with templates](F4.3-concern-modules.md) | Closed | release-1 | 7 Closed |
| [F4.4 — The render matrix, and the goldens leave git](F4.4-render-matrix.md) | Closed | release-1 | 9 Closed |
| [F4.5 — CLI](F4.5-cli.md) | Closed | release-1 | 10 Closed |
| [F4.6 — doctor](F4.6-doctor.md) | New | release-1 | 5 New |
| [F4.7 — Import contracts](F4.7-import-contracts.md) | New | release-1 | 3 Closed |
| [F4.8 — Self-hosting](F4.8-self-hosting.md) | New | release-1 | 1 New |
| [F4.9 — Seeded starter source](F4.9-seeded-starter-source.md) | Active | release-1 | 5 Closed |

<!-- END derived features -->

Release: [release-1](../../../releases/release-1/index.md) · Phase: D ·
Estimate: 2–3 weeks

Repo `rn-forge/kiln`, **one distribution**: `rn-forge-kiln` (module
`rn_forge.kiln`), which every generated repo takes as a pinned dev dependency
([ADR-0006](../../../adr/ADR-0006.md)). rn-forge dependencies are branch-pinned
([E7](../E7-pykit-release-pin-flip/index.md)).

**Dependencies.** S4.1.4, the checks-shape decision, is done. Every other story
depends on [E3](../E3-realign-goldens-and-canon/index.md). Features follow their
`Predecessors` rows, and each ends green on `task validate` and its own
acceptance block — except that [E5](../E5-web-archetypes/index.md)'s F5.1 and
F5.2 are built after S4.5.2 and before F4.4, and
[E11](../E11-package-docs/index.md)'s F11.1–F11.3 before F4.4, whose
`python-lib` cell needs `kiln generate package` ([board](../../index.md#order)).

**Where it stands (2026-10-13).** F4.1, F4.2 and F4.3 are done — S4.3.6, the
owner's Sonar decisions, closed on 2026-10-13. F4.6–F4.9 have not started.

**F4.5 (closed 2026-10-13).** Every command is on the declared app: `new`
(staged, seeded, from a path or a `git+` config source), `apply`, `diff`,
`version`, `config update`/`upgrade`, `prompt`, the `self` lifecycle verbs, and
`init`, which brings an existing standard repository under kiln without a
scaffold.

**F4.4 (closed 2026-10-13).** Every cell renders and validates, and CI renders
them all. The owner approved the rendered output at `fbfbae1` (S4.4.3). The
standard docs pages are seeded (S4.4.7), the scaffold divergences are settled
(S4.4.8), and the hand-authored goldens have left git (S4.4.9).
`task self:golden:compare BASE=<ref>` now diffs two rendered refs.

Decisions this epic builds on: [ADR-0001](../../../adr/ADR-0001.md),
[ADR-0003](../../../adr/ADR-0003.md), [ADR-0004](../../../adr/ADR-0004.md),
[ADR-0005](../../../adr/ADR-0005.md), [ADR-0006](../../../adr/ADR-0006.md),
[ADR-0007](../../../adr/ADR-0007.md). The design shared across features —
layout, commands, the artifact cycle, apply order, doctor checks, template
inventory, config lifecycle, module contract — is [design.md](design.md).

## Features

**Out of scope:** `kiln generate package` is
[E11](../E11-package-docs/F11.3-generate-package.md) for `python-lib`, and
[E10](../E10-kiln-generators/index.md) backlog for the application archetypes
and framework code generators.

## Risks

- **kiln becoming a god-kit.** Guard: every module is `artifacts()` +
  `checks()`, nothing else; `init` preflights only a fixed standard topology,
  never detects or transforms application code; the archetype is always
  supplied by config; no general adopt.
- **A template change reaching repos unreviewed** (no committed goldens means no
  diff in the pull request). Guard: a template change is not done until the
  owner has approved `task self:golden:render` output, and kiln's CI renders
  every cell so a broken template cannot merge.
- **Engine built before kiln needs it** (the framework-before-app trap). Guard:
  the engine was scoped to artifact kinds that have a golden example;
  `generation.py` tests are written from kiln's `cycle.py` needs.
- **Interactive-only CLI.** Guard: the acceptance runs `new` with stdin closed.
- **Generated-file drift accumulating in repos.** Guard: the committed-state
  checker runs in `task lint`; local `doctor` also detects fresh-render
  staleness; `apply` refuses unapproved paths.

## Acceptance

E4 is done when every feature's acceptance block passes. This block re-proves
the epic end to end afterwards.

```bash
set -euo pipefail
fails_with() { local out rc=0; out=$("${@:2}" 2>&1) || rc=$?; [ "$rc" -ne 0 ] && grep -qF -- "$1" <<<"$out"; }
cd rn-forge/kiln
kiln_dir=$PWD
task validate
uv run lint-imports
task self:golden:render
task self:golden:validate
test ! -e tests/fixtures/golden
scratch=$(mktemp -d)
uv run kiln new "$scratch/demo" --archetype python-tool --docs mkdocs --yes --json </dev/null \
  | jq -e '.artifacts | length > 0'
cd "$scratch/demo"
uv sync
task validate
uv run --project "$kiln_dir" kiln apply --dry-run --json \
  | jq -e '(.artifacts | length > 0) and all(.artifacts[]; .action == "unchanged")'
printf '\n# edit\n' >> Taskfile.yml
fails_with Taskfile.yml uv run kiln doctor .
fails_with Taskfile.yml uv run --project "$kiln_dir" kiln apply
uv run --project "$kiln_dir" kiln apply --force Taskfile.yml
uv run kiln doctor .
cd "$kiln_dir"
uv run kiln doctor --full
uv run kiln apply --dry-run --json \
  | jq -e '(.artifacts | length > 0) and all(.artifacts[]; .action == "unchanged")'
```
