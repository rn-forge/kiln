# Development

Everything goes through `task`. Nobody — human, agent or CI — invokes `uv`,
`pytest`, `ruff`, `pyright`, `mkdocs` or `kiln` directly;
`scripts/ci/check_ci_entrypoint.py` fails the build if a workflow step does.

```bash
task setup       # sync the venv with the dev and docs groups
task validate    # the whole gate: lint, typecheck, test, docs build
task format      # ruff format + fix, in place
task docs:serve  # live docs on http://127.0.0.1:8080
```

## This repo's own skeleton

kiln's skeleton is a hand-copy of `tests/fixtures/golden/python-tool`, with the
names changed. It regenerates itself once the generator exists
([ADR-0005](../adr/0005-archetypes.md)); until then, a change to the golden
repo's skeleton is a change kiln should make here too, by hand.

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

1. If the change touches a generated script's *body*, copy it byte-identically
   into every other golden repo. If it touches only the list in the
   `# BEGIN kiln config` header, change only that repo's header.

1. Run kiln's own tests: `task test` asserts every generated script has one body
   across every golden repo.

1. Once the generator exists, the snapshot test fails until the template agrees.
   Update the template, never the snapshot.

## The gate, in full

`task validate` runs, in order: ruff lint, ruff format check, the generated-file
baseline, the rn-forge dependency contract, the import contracts, the task
layout and gate-shrink check, the CI entrypoint check, the docs link/structure/
nav checks, mdformat, pyright strict, pytest, and a strict MkDocs build. A cold
clone with go-task and the pinned interpreter passes all of it without kiln
installed.

Two of those are easy to trip by accident:

- **`quality:lint:generated`** compares every managed file against
  `.rn-forge/kiln/state.json`. Until `kiln apply` exists that baseline is
  hand-written, so re-seed it after editing a managed file.
- **`quality:lint:markdown`** runs mdformat over the tree, with
  `.mdformat.toml`'s `exclude` as the single authority for exemptions.
  `.rn-forge/kiln/standard.md` is excluded on ownership grounds, not style: a
  formatter rewriting a kiln-owned file is two owners writing the same bytes.

## The tests

`tests/test_generated_bodies.py` is the executable form of F2: the four forks of
`check_ci_entrypoint.py` that started this work differed only in a list literal.
`tests/support/assert_generated_bodies.py` strips the provenance line and the
config header and compares what is left, so a drifted comment fails just as
loudly as drifted code.
