# Release 2 — the architecture baseline, package-site deploys, and taskkit retired

|  |  |
| -- | -- |
| **Status** | planned |

kiln deploys `python-lib`'s package docs sites (F11.5); it adds the architecture
baseline records for Python and web (E12); and taskkit is retired (F6.2).

## Entry criteria

- [Release 1](../release-1/index.md) ships before this one does.

## Scope

<!-- BEGIN derived scope -->

| Feature | Epic | State |
| -- | -- | -- |
| [F6.2 — Retire taskkit](../../specs/epics/E6-rebuild-the-repos/F6.2-retire-taskkit.md) | E6 | New |
| [F6.4 — `python-lib` renders pykit's discovered workspace pipeline](../../specs/epics/E6-rebuild-the-repos/F6.4-workspace-pipeline.md) | E6 | New |
| [F11.5 — CI deploys versioned package sites](../../specs/epics/E11-package-docs/F11.5-deploy-package-sites.md) | E11 | New |
| [F12.1 — The baseline module, and the Python records](../../specs/epics/E12-architecture-baseline/F12.1-python-baseline.md) | E12 | New |
| [F12.2 — The web records](../../specs/epics/E12-architecture-baseline/F12.2-web-baseline.md) | E12 | New |

<!-- END derived scope -->

## Decisions

- [ADR-0010](../../adr/ADR-0010.md) — proposed 2026-09-28: the canon carries an
  architecture baseline, as managed records (E12).

## Progress

Nothing started. F12.1's S12.1.1 is an owner decision and comes first in E12.
F11.5 waits on its entry criterion and its open question.

## Commits

Commits whose subject names a scope ID, newest first:

```bash
git log --format='%h %ad %s' --date=short -E --grep='[FS](6\.2|11\.5|12\.[1-2])'
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
