# E6 — Rebuild the repos, retire the old

|  |  |
| -- | -- |
| **State** | New |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F6.1 — `python-lib` can host pykit](F6.1-pykit-skeleton.md) | New | release-1 | 1 Active · 5 New · 8 Closed |
| [F6.2 — Retire taskkit](F6.2-retire-taskkit.md) | New | release-2 | 1 New |
| [F6.3 — The generated CI matches the hardened upstream CI](F6.3-hardened-ci.md) | Closed | release-1 | 6 Closed |
| [F6.4 — `python-lib` renders pykit's discovered workspace pipeline](F6.4-workspace-pipeline.md) | New | release-1 | — |
| [F6.5 — Rebuild an existing repository on kiln, and port it](F6.5-rebuild-and-port.md) | New | — | 3 New |

<!-- END derived features -->

Releases: [release-1](../../../releases/release-1/index.md),
[release-2](../../../releases/release-2/index.md) · Phase: F

Each repository's cutover onto kiln is that repository's own work, accepted by
its own specs ([ADR-0009](../../../adr/ADR-0009.md)). kiln's part is to prove,
inside kiln, that an archetype can host the repository: for pykit, a
pykit-shaped `python-lib` repository built in a scratch directory
([F6.1](F6.1-pykit-skeleton.md)), whose CI carries what pykit's and ngkit's own
CI already does ([F6.3](F6.3-hardened-ci.md),
[F6.4](F6.4-workspace-pipeline.md)), so adopting kiln takes nothing out of their
pipelines. Retiring taskkit ([F6.2](F6.2-retire-taskkit.md)) is kiln's because
taskkit's job moves into kiln.

## Features

**Out of scope here:** kiln itself is already self-hosted by
[F4.8](../E4-generator/F4.8-self-hosting.md). intellibuild is built on its own
schedule by a [standalone plan](../../../plans/intellibuild.md), and does not
gate kiln. apollo stays parked — its broken working tree is not repaired, and
when it returns it is `kiln new` + port (D40, open question 10).

## Acceptance

E6 is done when every feature's acceptance block passes. This block re-proves
the pykit-shaped repository and kiln together afterwards.

```bash
set -euo pipefail
cd rn-forge/kiln
s=$(mktemp -d)
tests/e2e/pykit_shape.sh "$s/pykit-shape" "$PWD"
(cd "$s/pykit-shape" && uv sync && task validate)
uv run kiln doctor --all "$s/pykit-shape" . --json | jq -e '.summary.repos == 2 and .summary.errors == 0'
task validate
uv run lint-imports
```
