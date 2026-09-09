# kiln

kiln is the rn-forge repository generator, and it carries the standard it
generates against. Both halves live here: the decisions and the spec are this
site, the archetypes and golden repos are the fixtures, and the CLI renders one
into the other.

- **[The standard repository](reference/standard-repo.md)** — the normative
  text. kiln renders it into every repo as `.rn-forge/kiln/standard.md`, so a
  repo always carries the rules it is held to.
- **[Decisions](adr/index.md)** — ADRs 0001–0008 *are* the standard; anything
  after them is a decision about kiln itself.
- **[The rn-forge workspace](architecture/workspace.md)** — the components, what
  each owns, and the two dependency graphs.
- **[Creating a repository](runbooks/creating-a-repo.md)** — `kiln new`, and the
  three points where it cannot decide for you.
- **[Plans](plans/index.md)** — the standardization plan and its harvest
  inventory.

## Where kiln is

Phase B: the canon and the golden repos exist and are reviewable; there is no
generator code yet. That order is deliberate — see
[ADR-0006](adr/0006-archetypes-and-golden-repos.md). The golden repos under
`tests/fixtures/golden/` are complete, runnable repositories; read one as if it
were the finished product, because that is exactly what the templates will be
derived from.
