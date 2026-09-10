# Repository shape

Every file in this repo has exactly one owner (kiln ADR-0001). Three kinds:

| Kind | Example | Rule |
| -- | -- | -- |
| **managed** | `Taskfile.yml`, `scripts/**`, `.github/**` | kiln's bytes; edits are drift and CI fails |
| **block** | `.gitignore`, `mkdocs.yml`, `CLAUDE.md` | kiln owns a fenced region; the body is ours |
| **seeded** | `docs/_areas.yml`, every area `index.md` | kiln wrote it once and never returns |

The committed `.rn-forge/kiln/state.json` records a hash for each managed file
and each block body, and presence for each seeded file.
`scripts/standards/check_generated.py` compares that baseline against the tree
using nothing but the standard library, which is why CI never installs kiln
(kiln ADR-0003).

## What `task validate` proves without kiln

Lint, imports, task layout, CI entrypoints, docs structure and links, the
generated-file baseline, types, tests, and a strict docs build. A cold clone
with go-task and the pinned interpreter passes all of it.

## What `kiln doctor` adds

Only the question CI cannot ask: whether a *newer kiln, or an edited config*,
would render something different from what is committed.
