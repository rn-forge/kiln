# E7 — pykit releases, and the pin flip

**Status:** deferred · **Phase:** G (triggered, not scheduled) · Absorbs the
deferred C.2 step 9
([F2.9](../E2-layer-split-and-golden-rename/index.md#f29-as-it-stood-when-deferred))

**Entry criteria:** the owner declares pykit stable
([ADR-0005](../../../adr/ADR-0005.md)).

## Scope

1. Cut the tags in the order commons → cli → tooling → web → django/fastapi
   (pykit's commons plan D.8).
1. Tag an `rn-forge-kiln` release; each repo moves its kiln pin with
   `kiln upgrade` ([ADR-0010](../../../adr/ADR-0010.md)).
1. Flip the rn-forge source value in kiln's defaults from branch to tag.
1. Run `kiln config upgrade --apply` in each repo.

Once released, a tag is the release contract again
([ADR-0005](../../../adr/ADR-0005.md), D46).
