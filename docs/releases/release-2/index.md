# Release 2 — the architecture baseline and taskkit retired

|  |  |
| -- | -- |
| **Status** | planned |

kiln adds the architecture baseline records for Python and web (E12), and
taskkit is retired (F6.2). Package-site deploys (F11.5) moved to
[release-1](../release-1/index.md) on 2026-10-18.

## Entry criteria

- [Release 1](../release-1/index.md) ships before this one does.

## Scope

<!-- BEGIN derived scope -->

| Feature | Epic | State |
| -- | -- | -- |
| [F6.2 — Retire taskkit](../../specs/epics/E6-rebuild-the-repos/F6.2-retire-taskkit.md) | E6 | New |
| [F12.1 — The baseline module, and the Python records](../../specs/epics/E12-architecture-baseline/F12.1-python-baseline.md) | E12 | New |
| [F12.2 — The web records](../../specs/epics/E12-architecture-baseline/F12.2-web-baseline.md) | E12 | New |
| [F18.10 — The defects the reviews confirmed](../../specs/epics/E18-kiln-simplification/F18.10-review-defects.md) | E18 | New |
| [F18.11 — Checks police the repository, not kiln's output](../../specs/epics/E18-kiln-simplification/F18.11-checks-police-repository-content.md) | E18 | New |

<!-- END derived scope -->

## Decisions

- [ADR-0010](../../adr/ADR-0010.md) — proposed 2026-09-28: the canon carries an
  architecture baseline, as managed records (E12).

## Progress

As of 2026-11-17, E12 has not started; its first step is an owner decision. F6.2
is new, and so are F18.10 and F18.11.

## Commits

Commits whose subject names a scope ID, newest first:

```bash
git log --format='%h %ad %s' --date=short -E --grep='[FS](6\.2|12\.[1-2])'
```

## Exit criteria

- E5's acceptance block passes.
- F12.2's acceptance holds.
- taskkit is archived.

intellibuild is not in this release; it is built on its own schedule from the
intellibuild plan once this release has shipped.

## Shipped

Filled at the cut: the kiln commit each exit criterion was proved at, and the
kiln and Nx refs the release records.
