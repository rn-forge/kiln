# Release 2 — the web archetypes

**Status:** in progress

kiln creates and ships the FastAPI web cells: `python-web-api` and
`python-web-app` with an Angular frontend. It also deploys `python-lib`'s
package docs sites, and taskkit is retired.

## Entry criteria

- [Release 1](../release-1/index.md) ships before this one does. E5's *build*
  starts earlier, once its **Depends on** lines hold (S4.3.3–S4.3.7 and
  S4.5.1–S4.5.2): the owner's next repositories are web repositories, and F5.1
  and F5.2 need neither the render matrix nor self-hosting.
- `rn-forge-fastapi` is implemented in pykit; what remains upstream is
  resolvable pins for the web packages
  ([board](../../specs/index.md#upstream-pins)).
- Django is deferred for both web archetypes; FastAPI is the default and the
  only shipped backend ([ADR-0005](../../adr/ADR-0005.md)).

## Scope

| Feature | Epic | Status |
| -- | -- | -- |
| [F5.1 — Library sets, and the modules gain the web shapes](../../specs/epics/E5-web-archetypes/F5.1-web-library-sets-and-modules.md) | E5 | done |
| [F5.2 — `kiln new` end to end for the web archetypes](../../specs/epics/E5-web-archetypes/F5.2-kiln-new-web-end-to-end.md) | E5 | done; S5.2.3 (Django) deferred |
| [F5.3 — Prove and ship the FastAPI cells](../../specs/epics/E5-web-archetypes/F5.3-shipped-web-cells.md) | E5 | in progress |
| [F6.2 — Retire taskkit](../../specs/epics/E6-rebuild-the-repos/F6.2-retire-taskkit.md) | E6 | planned |
| [F11.5 — CI deploys versioned package sites](../../specs/epics/E11-package-docs/F11.5-deploy-package-sites.md) | E11 | planned; waits on its entry criterion |
| [F12.2 — The web records](../../specs/epics/E12-architecture-baseline/F12.2-web-baseline.md) | E12 | planned |

## Decisions

- [ADR-0005](../../adr/ADR-0005.md) — updated 2026-09-17: the web selectors are
  `--backend` and `--frontend`, and the shipped web cells are FastAPI and
  FastAPI + Angular, with Django untested (F5.1, F5.3).

## Progress

F5.1 is done, and F5.2 apart from the deferred Django scaffold. In F5.3, S5.3.1,
S5.3.5 and S5.3.6 are done. S5.3.2–S5.3.3 wait on F4.4 and on a web cell's
`uv sync` resolving pykit's pins; S5.3.4 follows them. F11.5 waits on its entry
criterion and its open question.

## Commits

Commits whose subject names a scope ID, newest first:

```bash
git log --format='%h %ad %s' --date=short -E --grep='[FS](5\.[1-3]|6\.2|11\.5|12\.2)'
```

- `a31d739` 2026-09-27 S5.3.6 complete the repository setup experience
- `863963f` 2026-09-27 S5.3.5
- `376b1ff` 2026-09-26 S5.2.4 frontend scaffolding has its own module
- `e143f37` 2026-09-17 F5.3 Story Split + S5.3.1 Implemented
- `e605ed4` 2026-09-17 F5.2
- `6d13d06` 2026-09-17 F5.1

## Exit criteria

- E5's acceptance block passes.
- F11.5's acceptance holds.
- F12.2's acceptance holds.
- taskkit is archived.

intellibuild is not in this release; it is built on its own schedule from the
[intellibuild plan](../../plans/intellibuild.md) once this release has shipped.

## Shipped

Filled at the cut: the kiln commit each exit criterion was proved at, and the
kiln and Nx refs S5.3.2–S5.3.3 record.
