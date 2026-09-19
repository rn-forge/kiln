# E7 — pykit releases, and the pin flip

**Status:** deferred · **Phase:** G (triggered, not scheduled) · Absorbs the
deferred C.2 step 9
([F2.9](../E2-layer-split-and-golden-rename/index.md#f29-as-it-stood-when-deferred))

**Entry criteria:** the owner declares pykit stable.

Until then, dependencies use `feature/upgrade`, with resolved commits recorded
in lockfiles. This lets integration fixes land without cutting a new library
release for each golden-repo change.
[F3.2](../E3-realign-goldens-and-canon/F3.2-branch-pins.md) records the initial
pin alignment.

## Scope

1. Cut the tags in the order commons → cli → tooling → web → django/fastapi
   (pykit's commons plan D.8).
1. Tag an `rn-forge-kiln` release; each repo moves its kiln pin with
   `kiln upgrade` ([ADR-0006](../../../adr/ADR-0006.md)).
1. Flip the rn-forge source value in kiln's defaults from branch to tag.
1. Run `kiln config upgrade --apply` in each repo.

Once released, consumers pin release tags (D46).
