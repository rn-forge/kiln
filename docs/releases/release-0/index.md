# Release 0 — the canon and the hand-authored goldens

**Status:** shipped 2026-09-12

The foundation the generator renders against: the canon (ADRs, the reference
standard, the architecture and the runbook) and the hand-authored golden repos
that every later render is diffed against. No generator code — kiln's own
skeleton was hand-copied from the first golden, and it regenerates itself in
[F4.8](../../specs/epics/E4-generator/F4.8-self-hosting.md), in
[release-1](../release-1/index.md).

## Entry criteria

None — this is the first release.

## Scope

[E1](../../specs/epics/E1-canon-and-golden-repos/index.md) and
[E2](../../specs/epics/E2-layer-split-and-golden-rename/index.md) predate the
story taxonomy, so their scope is named by feature ID rather than story ID.

| Epic | Features |
| -- | -- |
| [E1 — The canon and the hand-authored golden repos](../../specs/epics/E1-canon-and-golden-repos/index.md) | F1.1–F1.5 |
| [E2 — The layer split lands in the goldens](../../specs/epics/E2-layer-split-and-golden-rename/index.md) | F2.8 and F2.10, kiln's half; F2.1–F2.7 are pykit's, tracked as [upstream work](../../specs/index.md#upstream-work-owned-by-pykit) |

F2.9 — the pin flip to released tags — was deferred out of this release and is
now [E7](../../specs/epics/E7-pykit-release-pin-flip/index.md).

## Exit criteria

- E1's acceptance block passes — **met** 2026-09-09.
- E2's acceptance block passes — **met** 2026-09-12.
- The owner has read every golden file as if it were the finished repo (F1.5).
