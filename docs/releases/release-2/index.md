# Release 2 — repositories on kiln's `main`

|  |  |
| -- | -- |
| **Status** | planned |

Every repository on kiln tracks its `main` (F7.9). The architecture baseline
(E12) and the web app's generated API client (F5.5) moved to
[release-1](../release-1/index.md) on 2026-11-19. Retiring taskkit (F6.2) was
removed on 2026-11-19: taskkit is deleted, and kiln does not track it.
Package-site deploys (F11.5) moved to [release-1](../release-1/index.md) on
2026-10-18.

## Entry criteria

- [Release 1](../release-1/index.md) ships before this one does.

## Scope

<!-- BEGIN derived scope -->

| Feature | Epic | State |
| -- | -- | -- |
| [F6.2 — Retire taskkit](../../specs/epics/E6-rebuild-the-repos/F6.2-retire-taskkit.md) | E6 | Removed |
| [F7.10 — An installed kiln, and every `python-tool`, completes on `<TAB>`](../../specs/epics/E7-pykit-release-pin-flip/F7.10-shell-completion.md) | E7 | Closed |
| [F18.10 — The defects the reviews confirmed](../../specs/epics/E18-kiln-simplification/F18.10-review-defects.md) | E18 | Active |
| [F18.11 — Checks police the repository, not kiln's output](../../specs/epics/E18-kiln-simplification/F18.11-checks-police-repository-content.md) | E18 | Active |

<!-- END derived scope -->

## Decisions

None yet.

## Progress

As of 2026-11-19, F7.9 waits on release 1, and F18.10 and F18.11 are new. On
2026-11-21 the owner parked F7.9 (deferred, no Iteration).

## Commits

Commits whose subject names a scope ID, newest first:

```bash
git log --format='%h %ad %s' --date=short -E --grep='[FS](7\.9)'
```

## Exit criteria

- F7.9's acceptance holds: every repository on kiln tracks `main`.

intellibuild is not in this release; it is built on its own schedule from the
intellibuild plan once this release has shipped.

## Shipped

Filled at the cut: the kiln commit each exit criterion was proved at, and the
kiln and Nx refs the release records.
