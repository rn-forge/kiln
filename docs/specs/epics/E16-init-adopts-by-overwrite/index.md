# E16 — `init` adopts by overwrite

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-11-04 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F16.1 — Opinionated `init`](F16.1-opinionated-init.md) | Closed | release-1 | 4 Closed |
| [F16.2 — kiln owns `mkdocs.yml`](F16.2-kiln-owns-mkdocs.md) | Closed | release-1 | 3 Closed |
| [F16.3 — The cutover SOP](F16.3-cutover-sop.md) | Closed | release-1 | 2 Closed |
| [F16.4 — Generated-file hygiene](F16.4-generated-file-hygiene.md) | Active | release-1 | 1 New · 6 Closed |
| [F16.5 — Rebuild an existing repository on kiln, and port it](F16.5-rebuild-and-port.md) | New | — | 3 New |

<!-- END derived features -->

`kiln init` brings an existing repository onto the standard the way `kiln new`
makes one: it writes `new`'s file set over the tree, with no merging of
kiln-shaped files, and never touches content. pykit and ngkit are the only
repositories with a pre-kiln lineage, and each cuts over once, by hand,
following one runbook ([F16.3](F16.3-cutover-sop.md)) that records what the
repository loses and what kiln absorbs. Decided by the owner on 2026-11-04
(findings R1–R4); release 1 carries all of it. The decision record is
[the cutover findings](../../ideas/pykit-cutover-findings.md).

The line `init` draws:

- **Overwritten (kiln-shaped):** tooling and config, the workflows kiln renders,
  `mkdocs.yml`, `docs/_areas.yml`, every `_structure.md`, and seeded indexes
  that hold no content.
- **Merged, because a tool already owns the file:** `pyproject.toml` (uv's
  tables) and `.gitignore` (kiln's fenced block).
- **Never touched:** source, tests, docs content pages, `README.md`, ADRs and
  specs.

[F16.5](F16.5-rebuild-and-port.md), moved here from E6 on 2026-11-04 (it was
F6.5), is the runbook's rebuild route for repositories `init` cannot adopt, and
is not in release 1.

This epic supersedes
[F6.6](../E6-rebuild-the-repos/F6.6-init-leaves-gate-runnable.md)'s decision
that `init` formats nothing,
[F6.9](../E6-rebuild-the-repos/F6.9-init-leaves-adopted-repo-alone.md)'s
framing, and the adopt prompt's mechanical steps.
