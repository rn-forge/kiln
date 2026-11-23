# E20 — Instruction files carry blocks only

|  |  |
| -- | -- |
| **State** | Closed |
| **Start Date** | 2026-11-23 |
| **Closed Date** | 2026-11-23 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F20.1 — kiln writes and checks only its block](F20.1-blocks-only.md) | Closed | release-1 | 3 Closed |
| [F20.2 — kiln's block links the README](F20.2-block-links-readme.md) | Closed | release-1 | 1 Closed |

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

None. The block-order question is settled in ADR-0020 (2026-11-23). The question
of a fresh `AGENTS.md`'s empty body became [F20.2](F20.2-block-links-readme.md):
kiln's block links `README.md`, and kiln seeds no body.
