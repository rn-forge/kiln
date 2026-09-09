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

kiln's skeleton is a hand-copy of `tests/fixtures/golden/python-cli`, with the
names changed. It regenerates itself once the generator exists
([ADR-0006](../adr/0006-archetypes-and-golden-repos.md)); until then, a change to
the golden repo's skeleton is a change kiln should make here too, by hand.

## Changing a golden repo

The golden repos are the source of truth for the templates, so this is the only
place a standard change starts.

1. Make the change in `tests/fixtures/golden/python-cli`, in real files.
2. Run that repo's own gate, from inside it — this is the proof that the change
   produces a working repo, and nothing else is:

   ```bash
   cd tests/fixtures/golden/python-cli
   uv sync && task validate
   ```

3. If the change touches a generated script's *body*, copy it byte-identically
   into every other golden repo. If it touches only the list in the
   `# BEGIN kiln config` header, change only that repo's header.
4. Run kiln's own tests: `task test` asserts every generated script has one body
   across every golden repo.
5. Once the generator exists, the snapshot test fails until the template agrees.
   Update the template, never the snapshot.

## The tests

`tests/test_generated_bodies.py` is the executable form of F2: the four forks of
`check_ci_entrypoint.py` that started this work differed only in a list literal.
`tests/support/assert_generated_bodies.py` strips the provenance line and the
config header and compares what is left, so a drifted comment fails just as
loudly as drifted code.
