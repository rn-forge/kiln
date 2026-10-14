# kiln

kiln is the rn-forge repository generator, and it carries the standard it
generates against. Both halves live here: the decisions and the spec are this
site, the archetypes are the fixtures, and the CLI renders one into the other.

## Read in this order

1. **[Specs](specs/index.md)** — the board: what is shipped, what is next, and
   which release it belongs to. Start here in a new session.
1. **[The standard repository](reference/standard-repo.md)** — the normative
   text: the verb list, the ownership table, the dependency sets, the doctor
   codes, the CI shape, the config schema. kiln renders this into every repo
   it generates as `.rn-forge/kiln/standard.md`.
1. **[Decisions](adr/index.md)** — the ADR log, each decision with the
   alternatives that were rejected.
1. **[The rn-forge workspace](architecture/workspace.md)** — the components,
   what each owns, and the dependency graphs.
1. **[Creating a repository](runbooks/creating-a-repo.md)** — `kiln new`, and
   the three points where it cannot decide for you.
1. **[Context](plans/context.md)** — the evidence, the harvest and the reviews
   behind all of the above.

## What each area is for

| Area | Holds |
| -- | -- |
| [Architecture](architecture/index.md) | how the system works today |
| [Guides](guides/index.md) | how to use and develop kiln |
| [Runbooks](runbooks/index.md) | procedures with decision points |
| Reference | the normative standard, and the generated API reference |
| [Releases](releases/index.md) | what ships when, by feature |
| [Specs](specs/index.md) | work: epics, features, stories, their design and open questions |
| [Decisions](adr/index.md) | choices between real alternatives |
| [Plans](plans/index.md) | the record the work grew out of |

## Where kiln is

The canon, the generator and the render matrix exist. The hand-authored golden
repos that bootstrapped the templates have left git; the oracle now is the
owner's review of the rendered cells (see [ADR-0005](adr/ADR-0005.md)). Render
and validate every cell, and read one as the finished product:

```bash
task self:golden:render && task self:golden:validate
```
