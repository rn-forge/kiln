# E7 — pykit releases, and the pin flip

**Status:** deferred · **Phase:** G (triggered, not scheduled) · Absorbs the
deferred C.2 step 9
([F2.9](../E2-layer-split-and-golden-rename/index.md#f29-as-it-stood-when-deferred))

**Entry criteria:** the owner declares pykit stable
([ADR-0005](../../../adr/0005-archetypes.md)).

## Scope

1. Cut the tags in the order commons → cli → tooling → web → django/fastapi
   (pykit's commons plan D.8).
1. Release `rn-forge-kiln-checks` (or whatever
   [F4.1](../E4-generator/F4.1-checks-by-module.md) settles on).
1. Flip the rn-forge source value in kiln's defaults from branch to tag.
1. Run `kiln config upgrade --apply` in each repo.

Once released, a tag is the release contract again
([ADR-0005](../../../adr/0005-archetypes.md), D46).
