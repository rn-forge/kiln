# Release 0 — the canon and the hand-authored goldens

|  |  |
| -- | -- |
| **Status** | shipped |
| **Finish Date** | 2026-09-12 |

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
story taxonomy: their features are rows in each epic's index, not files.

<!-- BEGIN derived scope -->

| Feature | Epic | State |
| -- | -- | -- |

<!-- END derived scope -->

### Done before this release

| Epic | Delivered | Implemented |
| -- | -- | -- |
| [E1](../../specs/epics/E1-canon-and-golden-repos/index.md) | F1.1 The canon; F1.2 Harvest inventory; F1.3 Golden repos; F1.4 Generated-body assertion; F1.5 Owner review loop | 2026-09-09 |
| [E2](../../specs/epics/E2-layer-split-and-golden-rename/index.md) | F2.8 Rename the goldens and add the missing ones; F2.10 Prove declarative CLI construction | 2026-09-12 |

F2.1–F2.7 are pykit's, tracked as
[upstream work](../../specs/index.md#upstream-pins). F2.9, the pin flip to
released tags, was deferred out of this release and is now
[E7](../../specs/epics/E7-pykit-release-pin-flip/index.md).

## Decisions

The decision log this release wrote was renumbered on 2026-09-15 (`9d96478`),
after it shipped: its records became today's
[ADR-0001–ADR-0007](../../adr/index.md), which release-1 lists. The original
records are in git history before that commit.

## Progress

Shipped. Nothing remains.

## Commits

Commits whose subject names a scope ID, newest first:

```bash
git log --format='%h %ad %s' --date=short -E --grep='[FS](1|2)\.[0-9]'
```

None: this release's commits predate subjects that name IDs. They are `6c3f70f`
to `afcfa07`, 2026-09-09 to 2026-09-12 (`initial commit` through `Phase C.2`).

## Exit criteria

- E1's acceptance block passes — **met** 2026-09-09.
- E2's acceptance block passes — **met** 2026-09-12.
- The owner has read every golden file as if it were the finished repo (F1.5).

## Shipped

- E1 shipped 2026-09-09 at `fe7bc70`, reviewed at `e1c4abb`.
- E2 shipped 2026-09-12 at `afcfa07`.
- No tag was cut: this release carried no generator code to version.
