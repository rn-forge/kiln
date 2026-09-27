# E6 — Rebuild the repos, retire the old

**Status:** planned · **Releases:**
[release-1](../../../releases/release-1/index.md),
[release-2](../../../releases/release-2/index.md) · **Phase:** F

Each repository's cutover onto kiln is that repository's own work, accepted by
its own specs ([ADR-0009](../../../adr/ADR-0009.md)). kiln's part is to prove,
inside kiln, that an archetype can host the repository: for pykit, a
pykit-shaped `python-lib` repository built in a scratch directory
([F6.1](F6.1-pykit-skeleton.md)). Retiring taskkit
([F6.2](F6.2-retire-taskkit.md)) is kiln's because taskkit's job moves into
kiln.

## Features

| ID | Feature | Depends on |
| -- | -- | -- |
| [F6.1](F6.1-pykit-skeleton.md) | `python-lib` can host pykit | S5.3.1; E11's F11.1–F11.3 |
| [F6.2](F6.2-retire-taskkit.md) | Retire taskkit | S4.6.2, S5.2.2 |

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
