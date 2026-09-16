# Development

Everything goes through `task`. Nobody — human, agent or CI — invokes `uv`,
`pytest`, `ruff`, `pyright`, `mkdocs` or `kiln` directly;
`kiln doctor --only ci-entrypoint` fails the build if a workflow step does.

```bash
task setup                    # sync the whole workspace with dev and docs
task validate                 # the whole gate: lint, typecheck, test, docs build
task format                   # ruff format + fix, in place, per package
task version -- golden-alpha  # one package's version
task build -- golden-alpha    # one package's wheel and sdist
task docs:serve               # live docs on http://127.0.0.1:8080
```

The per-package tools run from each package's own directory, so a package's
`pyproject.toml` settings are the ones that apply to it. The repo-wide checkers
— generated-file drift, imports, task layout, CI entrypoints, docs — run once,
at the root.

## The ten root verbs

`setup`, `validate`, `lint`, `format`, `typecheck`, `test`, `test:coverage`,
`build`, `clean`, `version` — plus the public `docs:build`, `docs:serve`,
`docs:nav`, `docs:structure`. Every other task is `internal: true` and exists to
be composed by a wrapper. That list is fixed by kiln ADR-0007, and
`kiln doctor --only task-layout` fails if a gate stops being reachable from
`validate`.

## After changing a generated file

Don't. Change `.rn-forge/kiln/config.toml` and run `kiln apply`. If you edited
one anyway, `task lint` will tell you which file drifted and from what.

## After adding a docs page

Run `task docs:nav` — `task lint` fails on a stale nav block.
