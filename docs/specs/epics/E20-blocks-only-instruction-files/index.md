# E20 — Instruction files carry blocks only

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-11-23 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F20.1 — kiln writes and checks only its block](F20.1-blocks-only.md) | Active | release-1 | 1 New · 2 Closed |

<!-- END derived features -->

kiln stops owning any part of `AGENTS.md` or `CLAUDE.md` outside its own fenced
block ([ADR-0020](../../../adr/ADR-0020.md), revised 2026-11-21). `kiln new` no
longer seeds either file's body, the `AGENTS.md` block creates the file when it
is absent, and every kiln check that reads an instruction file reads only kiln's
block. agentkit makes the matching change in its own epic, E5 "Blocks-only
instruction files". That change moves the `@AGENTS.md` import into an agentkit
block in `CLAUDE.md`, and adds an advisory `agentkit review` for the owner's
text.

## Open questions

- Is the order of kiln's and agentkit's blocks in `AGENTS.md` fixed? The
  proposal is kiln's block first, because it states the standard agentkit's
  block builds on. Today the order is whichever tool applied first.
- Without the seeded body, a fresh `AGENTS.md` has no Rules, Guardrails or Story
  workflow headings to prompt the owner. Should kiln's block link to a short
  page of suggested sections, or is the empty body enough?
