# ADR-0008 — Type-check with pyright in strict mode, not mypy

**Status:** accepted

## Context

Promoted from agentkit ADR-0008, which decided this for one repo. It is a fleet
decision in practice — no repo in `rn-forge` or `rn-tools` runs mypy, and the
`python-cli` and `python-lib` templates both generate a `pyright` task — but it
had never been written down anywhere a new repo would find it. A standard that
lives only in the repos that already follow it is not a standard.

The codebases lean on untyped libraries (`tomlkit`, `ruamel.yaml`, Jinja) at a
handful of choke points, which is where the strict/basic distinction bites.

### Alternatives considered

- **mypy**, as several original specs named. Diverges from what every repo
  actually does, for no gain in these codebases.
- **pyright at `basic`.** Would have accepted the 84 errors agentkit found
  rather than forcing them to be typed at the boundary — which is where the
  untyped libraries are, and therefore where the types are worth having.
- **Both.** Two type checkers disagreeing is a standing tax on every repo.

## Decision

`pyright` in **strict** mode, at zero errors, is the type gate for every Python
archetype. It runs as `quality:typecheck:python`, is reachable from `validate`,
and appears in every archetype's `required_validate` list.

`mypy` is not configured, not installed, and not a permitted alternative — a
repo that wants it needs an ADR of its own.

Typing is fixed at the boundary: where an untyped library enters, the value is
typed once, and the rest of the codebase is typed normally.

## Consequences

- One type checker, one configuration shape, one failure format across the
  fleet.
- Strict mode makes untyped third-party libraries visible at the point they are
  used, which is the intended pressure.
- A repo adopting a library with no stubs pays for it at the boundary rather
  than by lowering the gate.
- Published packages carry `py.typed`, because strict checking inside a repo
  says nothing to a consumer installing the wheel.
