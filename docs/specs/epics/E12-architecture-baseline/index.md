# E12 — The architecture baseline

|  |  |
| -- | -- |
| **State** | New |

Releases: [release-1](../../../releases/release-1/index.md),
[release-2](../../../releases/release-2/index.md) · Decision:
[ADR-0010](../../../adr/ADR-0010.md)

kiln's canon stops at the repository's structure today. `src/` and `tests/` are
the repository's own, and nothing tells the first feature built there how to
arrange it. This epic renders an architecture baseline into every generated
repository: a few decision records, managed by kiln, that fix the design of the
product code whatever the product is, with import contracts that enforce what
they can. [ADR-0010](../../../adr/ADR-0010.md) is the decision.
[design.md](design.md) holds the catalogue, the contracts and every record's
text, verbatim.

**Dependencies.** F12.1 builds on the `python` and `instructions` modules as
[S4.3.1](../E4-generator/F4.3-concern-modules.md#s431-python) and
[S4.3.5](../E4-generator/F4.3-concern-modules.md#s435-instructions) left them.
F12.2 needs F12.1, and the web shapes of
[F5.1](../E5-web-archetypes/F5.1-web-library-sets-and-modules.md), which are
done. Each feature starts with an owner's story that accepts the record texts;
no build story starts before it.

**Goldens first.** While `tests/fixtures/golden/` is in git, a template change
starts in the golden it reproduces
([render-matrix policy](../E4-generator/F4.4-render-matrix.md#template-review-policy)).
F12.1 changes all three Python goldens before any template. F12.2 changes no
golden, because the web cells have none;
[F4.4](../E4-generator/F4.4-render-matrix.md)'s render matrix reviews their
output.

**Build order.** F12.1 is built before F4.4, so that F4.4's matrix renders the
baseline with the rest. F12.2 is built after F12.1 and before the FastAPI cells
of [F5.3](../E5-web-archetypes/F5.3-shipped-web-cells.md) are approved.

## Features

| ID | Feature | Release | Depends on | State |
| -- | -- | -- | -- | -- |
| [F12.1](F12.1-python-baseline.md) | The baseline module, and the Python records | release-1 | S4.3.1, S4.3.5 (done) | New |
| [F12.2](F12.2-web-baseline.md) | The web records | release-2 | F12.1; F5.1 (done) | New |

**Out of scope.** kiln's own repository: its skeleton is a hand-copy of the
`python-tool` golden, and it adopts the baseline when it regenerates itself in
[F4.8](../E4-generator/F4.8-self-hosting.md). A client-generation task for
B-0005 is out of scope too; the record says the repository adds its own until
kiln renders one. Records for Django wait with the Django cells.

## Risks

- **Records that are really one product's taste.** Guard: the test in
  [ADR-0010](../../../adr/ADR-0010.md) (the record holds for a business API
  and for a dashboard alike), applied in each feature's owner story before any
  text is built.
- **Patterns the goldens cannot prove.** The goldens keep their product code
  trivial, so they prove that the contracts render and pass, not that the
  patterns are right. Guard: each contract has a test that makes it bite on a
  package built in a temporary directory.
- **A contract that fails a fresh repository.** Guard: every layer is optional,
  and the FastAPI contract names only `.**` wildcards, which match nothing on
  a fresh repository. Both were checked against import-linter 2.15
  ([design](design.md#the-tiers-and-their-contracts)).
