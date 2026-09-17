# E6 — Rebuild the repos, retire the old

**Status:** planned · **Releases:** F6.1 in
[release-1](../../../releases/release-1/index.md); F6.2 in
[release-2](../../../releases/release-2/index.md) · **Phase:** F

Per repo: `kiln new` into a fresh directory, port source and docs by hand,
`kiln doctor` and `task validate` green, then the fresh tree replaces the repo's
working tree on a branch. History before the replacement is not preserved
([ADR-0006](../../../adr/ADR-0006.md)).

## Features

| ID | Feature | Depends on |
| -- | -- | -- |
| [F6.1](F6.1-pykit-skeleton.md) | Prove, then replace pykit's `python-lib` skeleton | S6.1.1 on S5.3.1; S6.1.2 on E4 (F4.8) |
| [F6.2](F6.2-retire-taskkit.md) | Retire taskkit | S4.6.2, S5.2.2 |

**Out of scope here:** kiln itself is already self-hosted by
[F4.8](../E4-generator/F4.8-self-hosting.md). intellibuild is built on its own
schedule by a [standalone plan](../../../plans/intellibuild.md), and does not
gate kiln. apollo stays parked — its broken working tree is not repaired, and
when it returns it is `kiln new` + port (D40, open question 10).

## Acceptance

E6 is done when every feature's acceptance block passes. This block re-proves
the rebuilt repos together afterwards.

```bash
set -euo pipefail
kiln doctor --all rn-forge/pykit rn-forge/kiln --json | jq -e '.summary.repos == 2 and .summary.errors == 0'
for r in rn-forge/pykit rn-forge/kiln; do
  (cd "$r" && task validate && uv run lint-imports) || { echo "FAIL $r" >&2; exit 1; }
done
```
