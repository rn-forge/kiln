# kiln

kiln is the rn-forge repository generator, and it carries the standard it
generates against. Both halves live here: the decisions and the spec are this
site, the archetypes and golden repos are the fixtures, and the CLI renders one
into the other.

## Read in this order

1. **[Where the work stands](plans/standardization-plan.md)** — §0.1 of the plan
   is the status; §0.6 is what the last review changed; §3 is the next phase.
   Start here in a new session.
1. **[The standard repository](reference/standard-repo.md)** — the normative
   text: the verb list, the ownership table, the dependency sets, the doctor
   codes, the CI shape, the config schema. kiln renders this into every repo
   it generates as `.rn-forge/kiln/standard.md`.
1. **[Decisions](adr/index.md)** — ADRs 0001–0008 *are* the standard, each with
   the alternatives that were rejected. ADR-0009 is proposed and aimed at
   Phase C.
1. **[The rn-forge workspace](architecture/workspace.md)** — the components,
   what each owns, and the two dependency graphs.
1. **[Creating a repository](runbooks/creating-a-repo.md)** — `kiln new`, and
   the three points where it cannot decide for you.

## Where kiln is

**Phase B, reviewed and revised.** The canon and the golden repos exist and are
green; there is no generator code yet. That order is deliberate — see
[ADR-0005](adr/0005-archetypes.md).

The golden repos under `tests/fixtures/golden/` are complete, runnable
repositories. Read one as if it were the finished product, because that is
exactly what the templates will be derived from:

```bash
cd tests/fixtures/golden/python-cli
uv sync && task validate
```

**Next: Phase C** — extract `rn-forge-tooling` from pykit's commons, against the
target in [ADR-0009](adr/0009-tooling-owns-the-boilerplate.md), then wire it
into the golden repos. The phase's own step list carries the details.
