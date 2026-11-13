# E16 — `init` adopts by overwrite

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-11-04 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F16.1 — Opinionated `init`](F16.1-opinionated-init.md) | Closed | release-1 | 5 Closed |
| [F16.2 — kiln owns `mkdocs.yml`](F16.2-kiln-owns-mkdocs.md) | Closed | release-1 | 3 Closed |
| [F16.3 — The cutover SOP](F16.3-cutover-sop.md) | Closed | release-1 | 2 Closed |
| [F16.4 — Generated-file hygiene](F16.4-generated-file-hygiene.md) | Closed | release-1 | 7 Closed |
| [F16.5 — Rebuild an existing repository on kiln, and port it](F16.5-rebuild-and-port.md) | New | — | 1 New · 2 Removed |
| [F16.6 — What the cutover rehearsals found](F16.6-cutover-rehearsal-findings.md) | Closed | release-1 | 13 Closed |
| [F16.7 — What the cutover found](F16.7-cutover-findings.md) | Closed | release-1 | 9 Closed · 1 Removed |
| [F16.8 — Retire `kiln init`](F16.8-retire-kiln-init.md) | Active | release-1 | 3 Closed |
| [F16.9 — What the overlay cutovers found](F16.9-overlay-cutover-findings.md) | Active | release-1 | 1 New · 11 Closed · 2 Removed |
| [F16.10 — Agent instructions live in AGENTS.md](F16.10-agent-instructions-in-agents-md.md) | Active | release-1 | 7 Closed |

<!-- END derived features -->

**Superseded 2026-11-09.** The epic's premise, that `kiln init` adopts a
repository in place, was reversed by the owner after the cutover reruns on
`45a1e40`: `init` is retired before the `v0.1.0` tag, and a cutover overlays a
`kiln new` reference onto the existing repository
([ADR-0019](../../../adr/ADR-0019.md)). [F16.8](F16.8-retire-kiln-init.md) does
the work, and [F16.9](F16.9-overlay-cutover-findings.md) holds what the overlay
cutovers of pykit and ngkit found, and
[F16.10](F16.10-agent-instructions-in-agents-md.md) moves the agent instructions
into `AGENTS.md` ([ADR-0020](../../../adr/ADR-0020.md)). The closed features
below keep their text as history; what they say of `init` no longer holds.

`kiln init` brought an existing repository onto the standard the way `kiln new`
makes one: it writes `new`'s file set over the tree, with no merging of
kiln-shaped files, and never touches content. pykit and ngkit are the only
repositories with a pre-kiln lineage, and each cuts over once, by hand,
following one runbook ([F16.3](F16.3-cutover-sop.md)) that records what the
repository loses and what kiln absorbs. Decided by the owner on 2026-11-04
(2026-11-03 rehearsal findings R1–R4); release 1 carries all of it. The decision
record is [ADR-0019's background](../../../adr/ADR-0019.md#background), with the
CI decisions in [ADR-0016](../../../adr/ADR-0016.md).

The line `init` draws:

- **Overwritten (kiln-shaped):** tooling and config, the workflows kiln renders,
  `mkdocs.yml`, `docs/_areas.yml`, every `_structure.md`, and seeded indexes
  that hold no content.
- **Merged, because a tool already owns the file:** `pyproject.toml` (uv's
  tables) and `.gitignore` (kiln's fenced block).
- **Never touched:** source, tests, docs content pages, `README.md`, ADRs and
  specs.

[F16.5](F16.5-rebuild-and-port.md), moved here from E6 on 2026-11-04 (it was
F6.5), is rebuild and port, now the only cutover route, and is not in release 1.

This epic supersedes
[F6.6](../E6-rebuild-the-repos/F6.6-init-leaves-gate-runnable.md)'s decision
that `init` formats nothing,
[F6.9](../E6-rebuild-the-repos/F6.9-init-leaves-adopted-repo-alone.md)'s
framing, and the adopt prompt's mechanical steps.
