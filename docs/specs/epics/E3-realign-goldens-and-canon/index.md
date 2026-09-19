# E3 — Realign the goldens and the canon with pykit

**Status:** done · **Shipped:** 2026-09-15 · **Release:**
[release-1](../../../releases/release-1/index.md) · **Phase:** C.4 ·
**Estimate:** 3 days

Repo `rn-forge/kiln`, branch `feature/v1`. The hand-authored goldens are the
reference [E4](../E4-generator/index.md) writes templates from
([F4.4](../E4-generator/F4.4-render-matrix.md)), so they must match pykit as it
is, not as it was. F3.2 and S3.4.1 can start now. F3.1 follows F3.2, and F3.3
follows F3.1 and pykit's lifecycle work. S3.4.4 waits on E4's checks-shape
decision (S4.1.4), which is a decision only and waits on nothing in E3.

## Shared CLI design

The goldens consume pykit's shared CLI implementation instead of generating
copies of app construction, flag plumbing and exit handling.
`CliApp.from_config` builds the app from its declaration; repository code
supplies command functions. The console script targets the app object directly,
with no handwritten `main()`. [F3.1](F3.1-goldens-on-part-e-api.md) proves this
integration against pykit's Part E API.

pykit owns this library design and its package boundaries: commons supplies
process-wide console and logging facilities; cli supplies the Typer layer;
tooling supplies generation and lifecycle mechanisms. kiln seeds the declaration
and dependency wiring, but does not own pykit's internal dependency graph.
Applications may use the library primitives directly when a declarative surface
does not fit. Generating copies would require a fix in every consumer;
implementing an application framework in kiln would couple runtime applications
to their repository generator.

## Features

| ID | Feature | Depends on |
| -- | -- | -- |
| [F3.1](F3.1-goldens-on-part-e-api.md) | Port `golden/python-app` and `golden/python-tool` to the Part E API | F3.2 |
| [F3.2](F3.2-branch-pins.md) | Branch pins during pykit stabilization | — |
| [F3.3](F3.3-python-tool-is-a-tool.md) | Make `golden/python-tool` a tool | F3.1; pykit C.3 (lifecycle surface) |
| [F3.4](F3.4-canon-catches-up.md) | The canon catches up; re-seed state; README | S3.4.1: —; S3.4.4: [S4.1.4](../E4-generator/F4.1-checks-by-module.md#s414-the-ci-shape-is-decided) (decision); S3.4.2: F3.1–F3.3, S3.4.1, S3.4.4 |

The instruction-file split (the old C.3 step 4, D57) is the one piece already
done.

## Starting state (verified 2026-09-12)

What is true on disk that the older ADRs and the reference do not say. Verify
with `git status` before acting; it goes stale.

- **The goldens are behind pykit.** `golden/python-app` and `golden/python-tool`
  still import `rn_forge.cli.declare` (deleted in pykit Part E) and
  `from rn_forge.cli import console` (moved to `rn_forge.commons`), and still
  define `main()`. Their `uv.lock` pins an older `feature/upgrade` commit,
  which is the only reason they still pass. The same stale names appear in
  their `README.md`, `docs/architecture/repository-shape.md`,
  `docs/adr/ADR-0001.md` and `config.toml` comments.
- **`golden/python-lib`'s two packages pin `rn-forge-commons-v0.2.2`**, a tag
  from before the layer split; the other goldens pin `@feature/upgrade`.
- **`docs/reference/standard-repo.md`'s dependency-set table omits
  `rn-forge-web`** beneath django and fastapi, and its ownership table still
  lists `scripts/**` as generated.
- **pykit gained `rn-forge-web`** (framework-free inbound HTTP primitives,
  depends on commons only) and is building **`rn-forge-fastapi`** over it.
  `rn-forge-django` does not depend on web yet; pykit's django plan aligns it.
- kiln itself has no generator source (`src/rn_forge/kiln/` is an empty package)
  and still carries a hand-copied `scripts/**`.

| Repo | Branch | State (2026-09-12) |
| -- | -- | -- |
| `rn-forge/kiln` | `feature/v1` | three hand-authored goldens; kiln's own config is `python-tool` |
| `rn-forge/pykit` | `feature/upgrade` | commons, cli, tooling, web, django; fastapi in progress. Executable form: `docs/plans/commons-upgrade-plan.md`, `web-library-plan.md`, `fastapi-library-plan.md`, indexed by `docs/plans/README.md` |

## Acceptance

E3 is done when every feature's acceptance block passes. This block re-proves
the epic as a whole afterwards.

```bash
set -euo pipefail
absent() { local rc=0; rg -q --hidden --glob '!.git' "$@" || rc=$?; [ "$rc" -eq 1 ]; }
cd rn-forge/kiln
G=tests/fixtures/golden
absent 'rn_forge\.cli\.declare|build_app|from rn_forge\.cli import console' "$G"      # F3.1
absent 'def main' "$G/python-app/src" "$G/python-tool/src"                            # F3.1
absent 'rn-forge-commons-v0\.2\.2' "$G"                                               # F3.2
for g in "$G/python-app" "$G/python-tool" "$G/python-lib"; do
  (cd "$g" && uv sync && task validate) || { echo "FAIL $g" >&2; exit 1; }
done
(cd "$G/python-tool" && uv run golden-tool doctor)                                    # F3.3
(cd "$G/python-tool" && uv run golden-tool --json status) | jq -e '.version'          # F3.3
absent 'RNF_HOME|lifecycle' "$G/python-app"                                           # F3.3
rg -q 'rn-forge-web' docs/reference/standard-repo.md                                  # F3.4
task lint                                                                             # F3.4
```

Run on 2026-09-15 against `feature/v1`: every feature block passes (F3.1, F3.2,
F3.3, F3.4) and this block passes after them. Two things it caught and that were
fixed rather than waived: S3.3.2's normalized diff carried a `TemplateEngine`
render, an `$RNF_HOME` docstring aside and a dropped shared CLI design sentence,
none on the approved list; and `scripts/standards/check_rn_forge_deps.py`
illustrated a pin with the pre-layer-split `rn-forge-commons-v0.2.2` tag, which
the F3.2 line reads as a stale pin — the example now shows the branch pin F3.2
specifies, in kiln and in all three goldens, with `state.json` re-seeded for
each.
