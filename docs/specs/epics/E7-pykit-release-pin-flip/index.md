# E7 — pykit releases, and the pin flip

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-10-14 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F7.1 — kiln renders and takes pykit by release tag](F7.1-tag-pins.md) | Closed | release-1 | 2 Closed |
| [F7.2 — A tagged kiln release, taken by each repository](F7.2-kiln-release-and-config-upgrade.md) | New | release-1 | — |
| [F7.3 — kiln takes pykit's document, template and Markdown helpers](F7.3-adopt-pykit-extraction.md) | New | release-1 | 7 New |
| [F7.4 — kiln runs beside a repository, not inside its lock](F7.4-kiln-runs-beside-the-repository.md) | Active | release-1 | 3 New · 1 Closed |

<!-- END derived features -->

Phase: G (triggered, not scheduled) · Absorbs the deferred C.2 step 9
([F2.9](../E2-layer-split-and-golden-rename/index.md#f29-as-it-stood-when-deferred))

**Triggered 2026-10-14:** pykit's tags exist. [F7.1](F7.1-tag-pins.md) is scope
item 2; items 1 and 3 are the release-1 cut.

**2026-10-25:** pykit's Release 6 tagged the extraction release
(`rn-forge-commons-v0.7.0`, `rn-forge-tooling-v0.3.0`, and every dependent
re-tagged on them), so [F7.3](F7.3-adopt-pykit-extraction.md) waits only on
[F7.4](F7.4-kiln-runs-beside-the-repository.md).

Until then, dependencies use `feature/upgrade`, with resolved commits recorded
in lockfiles. This lets integration fixes land without cutting a new library
release for each golden-repo change.
[F3.2](../E3-realign-goldens-and-canon/F3.2-branch-pins.md) records the initial
pin alignment.

## Scope

1. Tag an `rn-forge-kiln` release; each repo moves its kiln pin with
   `kiln upgrade` ([ADR-0006](../../../adr/ADR-0006.md)).
1. Flip the rn-forge source value in kiln's defaults from branch to tag.
1. Run `kiln config upgrade --apply` in each repo.
1. Run kiln beside each repository, pinned in `config.toml`, so kiln's pykit
   pins and a repository's are independent
   ([F7.4](F7.4-kiln-runs-beside-the-repository.md)).
1. Take pykit's later releases when kiln needs what they add, and delete what
   kiln wrote in their place ([F7.3](F7.3-adopt-pykit-extraction.md)).
1. Render pykit by version range from its package index, and accept ranges in
   `rn-forge-deps` ([ADR-0018](../../../adr/ADR-0018.md), F7.3's S7.3.6 and
   S7.3.7).

Once released, consumers pin release tags (D46).
