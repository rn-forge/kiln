# E4 — The generator

**Status:** in progress · **Release:**
[release-1](../../../releases/release-1/index.md) · **Phase:** D · **Estimate:**
2–3 weeks

Repo `rn-forge/kiln`, **one distribution**: `rn-forge-kiln` (module
`rn_forge.kiln`), which every generated repo takes as a pinned dev dependency
([ADR-0010](../../../adr/ADR-0010.md)). rn-forge dependencies are branch-pinned
([ADR-0005](../../../adr/ADR-0005.md)).

**Dependencies.** S4.1.4, the checks-shape decision, is done. Every other story
depends on [E3](../E3-realign-goldens-and-canon/index.md), and S4.5.5 also on
pykit's lifecycle surface. Features follow the column below, and each ends green
on `task validate` and its own acceptance block — except that
[E5](../E5-web-archetypes/index.md)'s F5.1 and F5.2 are built after S4.5.2 and
before F4.4 ([board](../../index.md#order)).

Decisions this epic builds on: [ADR-0005](../../../adr/ADR-0005.md),
[ADR-0004](../../../adr/ADR-0004.md), [ADR-0011](../../../adr/ADR-0011.md),
[ADR-0003](../../../adr/ADR-0003.md), [ADR-0010](../../../adr/ADR-0010.md). The
design shared across features — layout, commands, the artifact cycle, apply
order, doctor checks, template inventory, config lifecycle, module contract — is
[design.md](design.md).

## Features

| ID | Feature | Phase step | Depends on |
| -- | -- | -- | -- |
| [F4.1](F4.1-checks-by-module.md) | The checks, organized by module | D.1 | S4.1.4: done; the rest: E3 |
| [F4.2](F4.2-core-module.md) | The `core` module, the config manager and the module contract | D.2 | F4.1 |
| [F4.3](F4.3-concern-modules.md) | The concern modules, with templates | D.3 | F4.2; E3 goldens |
| [F4.4](F4.4-render-matrix.md) | The render matrix, and the goldens leave git | D.4 | F4.3 |
| [F4.5](F4.5-cli.md) | CLI | D.5 | F4.3; S4.5.5 also pykit C.3 and its open question |
| [F4.6](F4.6-doctor.md) | doctor | D.6 | F4.3, S4.5.1 |
| [F4.7](F4.7-import-contracts.md) | Import contracts | D.7 | F4.3, S4.1.2 |
| [F4.8](F4.8-self-hosting.md) | Self-hosting | D.8 | F4.4, F4.5, F4.6, F4.7 |

**Out of scope:** `kiln generate package` and framework code generators are
backlog, [E10](../E10-kiln-generators/index.md).

## Risks

- **kiln becoming a god-kit.** Guard: every module is `artifacts()` +
  `checks()`, nothing else; no detection code anywhere; the archetype is
  always asserted by config; no adopt.
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
