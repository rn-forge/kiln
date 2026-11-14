# E17 — One task standard for every archetype

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-11-05 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F17.1 — The task surface says what it is](F17.1-task-surface.md) | Closed | release-1 | 6 Closed |
| [F17.2 — One grammar for the CI surface, and one home for check policy](F17.2-ci-task-grammar.md) | Closed | release-1 | 5 Closed |
| [F17.3 — A faster gate](F17.3-a-faster-gate.md) | Active | release-1 | 1 New · 7 Closed |

<!-- END derived features -->

What E15 does for the generated CI, E17 does for the generated task surface. It
covers one declared surface (the developer verbs, and `ci:*` as the CI surface),
one naming grammar, one rule for `command_overrides`, a gate that holds every
lint check that is on, task tables in the standard generated from the rendered
task files, and one home for check policy. The model is
[ADR-0007](../../../adr/ADR-0007.md), which F17.1 and F17.2 revise. What is
built is in [the task architecture](../../../architecture/tasks.md), the
counterpart of [the CI architecture page](../../../architecture/ci.md).

The epic is separate from E15 because E15's scope is the CI standard and it
closes on that scope. It is in release 1 because a public task name is a
compatibility surface ([ADR-0007](../../../adr/ADR-0007.md)): renaming is free
before the release-1 tag and the pykit cutover, and a breaking change after.

[F17.1](F17.1-task-surface.md) was built first, while E15 was still open, on the
branch `feature/task-standard` (the worktree `../kiln-task-standard`). It lands
on `feature/v1` as one commit, rebased onto E15's close.
[F17.2](F17.2-ci-task-grammar.md) renames tasks and restructures the templates
that [F15.8](../E15-ci-standard/F15.8-one-workflow-contract.md) rewrote, so it
is built on `feature/v1` after F17.1 lands.

**Reopened 2026-11-10** for [F17.3](F17.3-a-faster-gate.md): `task validate`
takes minutes, and the owner wants the gate faster before the cutovers rely on
it. F17.1 and F17.2 stay closed and keep their text. F17.3 changes no public
task name.
