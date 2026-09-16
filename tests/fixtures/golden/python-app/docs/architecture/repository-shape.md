# Repository shape

Every file in this repo has exactly one owner (kiln ADR-0001). Three kinds:

| Kind | Example | Rule |
| -- | -- | -- |
| **managed** | `Taskfile.yml`, `tasks/**`, `.github/**` | kiln's bytes; edits are drift and CI fails |
| **block** | `.gitignore`, `mkdocs.yml`, `CLAUDE.md` | kiln owns a fenced region; the body is ours |
| **seeded** | `docs/_areas.yml`, every area `index.md` | kiln wrote it once and never returns |

The committed `.rn-forge/kiln/state.json` records a hash for each managed file
and each block body, and presence for each seeded file.
`kiln doctor --only generated` compares that baseline against the tree. kiln is
a pinned dev dependency, and CI runs it read-only: it checks, and never renders
(kiln ADR-0010).

## What `task validate` proves

Lint, imports, task layout, CI entrypoints, docs structure and links, the
generated-file baseline, types, tests, and a strict docs build. A cold clone
with go-task and the pinned interpreter passes all of it.

## The command line

`src/golden_app/main.py` constructs nothing. The `[cli]` table in
`.rn-forge/kiln/config.toml` names the app, its help text and each command's
import target; `rn_forge.cli.CliApp.from_config` reads that table and returns
the built Typer application, with the standard `--log-level`, `--log-file`,
`--quiet` and `--json` flags and the error-to-exit-code mapping already wired
(kiln ADR-0009).

Adding a command is an entry in that table and a function in `commands.py`. The
escape hatch is open: a repo whose application the declaration cannot describe
constructs `rn_forge.cli.CliApp` itself and registers its commands with
`@app.command()`, keeping the same flags and exit-code mapping.

## What `kiln doctor` adds

Only the question CI cannot ask: whether a *newer kiln, or an edited config*,
would render something different from what is committed.
