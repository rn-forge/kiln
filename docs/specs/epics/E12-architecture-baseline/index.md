# E12 — The architecture baseline

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-11-19 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F12.1 — The catalogue, and the Python records](F12.1-python-baseline.md) | Active | release-1 | 2 New · 2 Closed |
| [F12.2 — The web records, and a starter that follows them](F12.2-web-baseline.md) | New | release-1 | 5 New |

<!-- END derived features -->

Release: [release-1](../../../releases/release-1/index.md) · Decision:
[ADR-0010](../../../adr/ADR-0010.md)

kiln's canon stops at the repository's structure today. `src/` and `tests/` are
the repository's own, and nothing tells the first feature built there how to
arrange it. This epic renders kiln's architecture baseline into every generated
repository: a few decision records under `docs/adr/kiln/`, named `ARCH-<nnnn>`
and managed by kiln, that fix the design of the product code whatever the
product is, with import contracts that enforce what they can.
[ADR-0010](../../../adr/ADR-0010.md) is the decision. [design.md](design.md)
holds the catalogue, the contracts and every record's text, verbatim.

*Rewritten 2026-11-19 (owner decisions):* records under `docs/adr/kiln/` with
the `mkdocs` profile, `ARCH-` identifiers, every repository on kiln receiving
records and contracts at its next pin, the FastAPI starter brought into line
with its records, and ARCH-0005 waiting on
[F5.5](../E5-web-archetypes/F5.5-web-app-api-client.md)'s client task. The
earlier text is in git history.

**Dependencies.** F12.1 builds on the `core`, `docs`, `instructions` and
`python` modules as they stand. F12.2 needs F12.1; its S12.2.5 needs F5.5. Each
feature starts with an owner's story that accepts the record texts; no build
story starts before it.

**Review.** The goldens are no longer in git
([F4.4](../E4-generator/F4.4-render-matrix.md)), so every build story's output
is reviewed as a `task self:golden:compare BASE=HEAD` diff. kiln is a
`python-tool` with the `mkdocs` profile, so its own repository takes ARCH-0001,
ARCH-0002 and the layers contract through `task kiln:apply`.

## Features

**Out of scope.** Records for `node-lib`, and for the Angular frontend beyond
ARCH-0005. Records for Django wait with the Django cells
([F5.4](../E5-web-archetypes/F5.4-django-scaffold.md)). A repository already
scaffolded keeps its seeded starter.

## Risks

- **Records that are really one product's taste.** Guard: the test in
  [ADR-0010](../../../adr/ADR-0010.md) (the record holds for a business API
  and for a dashboard alike), applied in each feature's owner story before any
  text is built.
- **A contract that breaks a repository at its next pin.** The repositories on
  kiln have code. Guard: every layer is optional, and the FastAPI contract
  names only `.**` wildcards, so only a real upward import or a framework
  import in `domain` or `services` breaks; the release notes it as breaking,
  and the repository fixes the import or records an ADR that supersedes the
  record.
- **Patterns the render matrix cannot prove.** The starter is small, so the
  matrix proves that the contracts render and pass, not that the patterns are
  right. Guard: each contract has a test that makes it bite on a package built
  in a temporary directory.
- **A record that is not reachable on the site.** `docs-site` fails an orphan
  page. Guard: kiln's block in `docs/adr/index.md` links the index, and
  S12.1.2 tests that a fresh repository's docs checks pass with the records.
