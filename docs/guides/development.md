# Development

Everything goes through `task`. Nobody — human, agent or CI — invokes `uv`,
`pytest`, `ruff`, `pyright`, `mkdocs` or `kiln` directly; `kiln doctor`'s
`ci-entrypoint` check fails the build if a workflow step does.

```bash
task setup       # sync the venv with the dev and docs groups
task validate    # the whole gate: lint, typecheck, test, docs build
task format      # ruff format + fix, in place
task docs:serve  # live docs on http://127.0.0.1:8080
```

## This repo's own skeleton

kiln generates its own skeleton from `.rn-forge/kiln/config.toml` (the
`python-app` archetype, `lifecycle = true`). Change the config or a template and
run `kiln apply`; never edit a generated file.

## Changing a golden repo

The golden repos are the source of truth for the templates, so this is the only
place a standard change starts.

1. Make the change in `tests/fixtures/golden/python-tool`, in real files.

1. Run that repo's own gate, from inside it — this is the proof that the change
   produces a working repo, and nothing else is:

    ```bash
    cd tests/fixtures/golden/python-tool
    uv sync && task validate
    ```

1. Make the same change in every other golden repo it applies to, and re-seed
   each one's `.rn-forge/kiln/state.json`.

1. Once the generator exists, the snapshot test fails until the template agrees.
   Update the template, never the snapshot.

## The gate, in full

`task validate` runs, in order: ruff lint, ruff format check, the generated-file
baseline, the rn-forge dependency contract, the import contracts, the task
layout and gate-shrink check, the CI entrypoint check, the docs link/structure/
nav checks, mdformat, pyright strict, pytest, and a strict MkDocs build. The
policy and docs checks are `kiln doctor`, which comes from the dev group, so
`task setup` is all a cold clone needs.

Two of those are easy to trip by accident:

- **`kiln:doctor`'s `generated` check** compares every managed file against
  `.rn-forge/kiln/state.json`. Until `kiln apply` exists that baseline is
  hand-written, so re-seed it after editing a managed file.
- **`quality:lint:markdown`** runs mdformat over the files git lists — tracked
  and untracked, less what `.gitignore` ignores — so it must run from a git
  repository's root. `.mdformat.toml`'s `exclude` exempts files git does list.
  `.rn-forge/kiln/standard.md` is excluded on ownership grounds, not style: a
  formatter rewriting a kiln-owned file is two owners writing the same bytes.
- **`quality:lint:toml`** runs taplo over the same git file list, with
  `.taplo.toml`'s `exclude` for files git lists but the repo does not format.
  A repository created before this check adopts it by adding `taplo` to its
  dev group, then running `kiln apply` and `task format`.
