# Release 2 — the web archetypes

**Status:** planned

## Entry criteria

- [Release 1](../release-1/index.md) has shipped.
- `rn-forge-fastapi` has reached its plan's acceptance in pykit.
- [F5.3's open question](../../specs/epics/E5-web-archetypes/F5.3-shipped-web-cells.md#open-questions)
  is answered: `python-web-app --framework django` ships, or is marked
  `untested`. This is a decision gate, and E5 does not start without it.

## Scope

| Epic | Stories |
| -- | -- |
| [E5 — The web archetypes](../../specs/epics/E5-web-archetypes/index.md) | [S5.1.1–S5.1.3](../../specs/epics/E5-web-archetypes/F5.1-web-library-sets-and-modules.md), [S5.2.1–S5.2.2](../../specs/epics/E5-web-archetypes/F5.2-kiln-new-web-end-to-end.md), [S5.3.1](../../specs/epics/E5-web-archetypes/F5.3-shipped-web-cells.md) |
| [E6 — Rebuild the repos](../../specs/epics/E6-rebuild-the-repos/index.md) | [S6.2.1](../../specs/epics/E6-rebuild-the-repos/F6.2-retire-taskkit.md) |

## Exit criteria

- E5's acceptance block passes.
- taskkit is archived.

intellibuild is not in this release; it is built on its own schedule from the
[intellibuild plan](../../plans/intellibuild.md) once this release has shipped.
