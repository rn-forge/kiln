# E8 — The Azure DevOps CI provider

**Status:** deferred · **Phase:** G (triggered, not scheduled)

**Entry criteria:** a repo needs `ci.provider = "ado"`. The
[intellibuild plan](../../../plans/intellibuild.md) holds the question of
whether intellibuild is that repo.

## Scope

Add `ci.provider = "ado"` to the `cicd` module. ADO was parked from the start
(D4), with the generator design leaving room for a second provider: the provider
is an orthogonal capability ([ADR-0005](../../../adr/ADR-0005.md)), and ADO's
`extends`/`template:` are git resources, so the same committed-workflow model
applies ([ADR-0006](../../../adr/ADR-0006.md)).
