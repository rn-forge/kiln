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

## The ten root verbs

`setup`, `validate`, `lint`, `format`, `typecheck`, `test`, `test:coverage`,
`build`, `clean`, `version` — plus the public `docs:build`, `docs:serve`,
`docs:nav`, `docs:structure`. Every other task is `internal: true` and exists to
be composed by a wrapper. That list is fixed by kiln ADR-0008, and
`scripts/task/check_task_layout.py` fails if a gate stops being reachable from
`validate`.

## After changing a generated file

Don't. Change `.rn-forge/kiln/config.toml` and run `kiln apply`. If you edited
one anyway, `task lint` will tell you which file drifted and from what.

## After adding a docs page

Run `task docs:nav` — `task lint` fails on a stale nav block.
