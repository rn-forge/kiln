# Release 2 — the architecture baseline, and repositories on kiln's `main`

|  |  |
| -- | -- |
| **Status** | planned |

kiln adds the architecture baseline records for Python and web (E12), and every
repository on kiln tracks its `main` (F7.9). Retiring taskkit (F6.2) was removed
on 2026-11-19: taskkit is deleted, and kiln does not track it. Package-site
deploys (F11.5) moved to [release-1](../release-1/index.md) on 2026-10-18.

## Entry criteria

- [Release 1](../release-1/index.md) ships before this one does.

## Scope

<!-- BEGIN derived scope -->

| Feature | Epic | State |
| -- | -- | -- |
| [F6.2 — Retire taskkit](../../specs/epics/E6-rebuild-the-repos/F6.2-retire-taskkit.md) | E6 | Removed |
| [F7.9 — Repositories follow kiln's `main` after release 1](../../specs/epics/E7-pykit-release-pin-flip/F7.9-repos-follow-main.md) | E7 | New |
| [F12.1 — The baseline module, and the Python records](../../specs/epics/E12-architecture-baseline/F12.1-python-baseline.md) | E12 | New |
| [F12.2 — The web records](../../specs/epics/E12-architecture-baseline/F12.2-web-baseline.md) | E12 | New |
| [F18.10 — The defects the reviews confirmed](../../specs/epics/E18-kiln-simplification/F18.10-review-defects.md) | E18 | New |
| [F18.11 — Checks police the repository, not kiln's output](../../specs/epics/E18-kiln-simplification/F18.11-checks-police-repository-content.md) | E18 | New |

<!-- END derived scope -->

## Decisions

- [ADR-0010](../../adr/ADR-0010.md) — proposed 2026-09-28: the canon carries an
  architecture baseline, as managed records (E12).

## Progress

As of 2026-11-19, E12 has not started; its first step is an owner decision. F7.9
waits on release 1, and F18.10 and F18.11 are new.

## Commits

Commits whose subject names a scope ID, newest first:

```bash
git log --format='%h %ad %s' --date=short -E --grep='[FS](7\.9|12\.[1-2])'
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
