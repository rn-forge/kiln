# adr/ — what belongs here

## Belongs here

- One decision per file, `<nnnn>-<slug>.md`, with Context / Decision /
  Consequences and a `**Status:**` line.
- Decisions this repo makes for itself. The decisions about the *standard* live
  in the kiln repo's ADR log and are rendered here as
  `.rn-forge/kiln/standard.md`, not copied.

## Does not belong here

| Instead of | Put it in |
| -- | -- |
| How something works now | `architecture/` |
| A plan | `specs/` |

## Naming and shape

- Numbers are contiguous from `0001`, never reused; a reversed decision gets a
  new ADR and the old one's status becomes `superseded by ADR-nnnn`.
- `**Status:**` is one of `proposed`, `accepted`, `deprecated`, or
  `superseded by ADR-nnnn`.
