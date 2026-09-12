# golden-lib

The golden repo for kiln's `python-lib` archetype: a uv workspace of published
library packages, whose every generated file is exactly what kiln must render.

It is a fixture, and it is also a real repo — `uv sync && task validate` passes
in it standalone. That is the point: a template proven only in the abstract has
never been proven to produce a working repo.

```bash
uv sync
task validate
```

The product is two functions, in `packages/golden-alpha` and
`packages/golden-beta`. Two is the smallest number that proves the release
matrix is a matrix. Everything else is the standard, stated in
[.rn-forge/kiln/standard.md](.rn-forge/kiln/standard.md) and documented in
[docs/](docs/index.md).

## Working here

- Run everything through `task`. `task validate` is the gate.
- The packages live in `packages/golden-alpha/` and `packages/golden-beta/`,
  each with its own `pyproject.toml`, `src/` and `tests/`.
- `task build` and `task version` take a package:
  `task version -- golden-alpha`.
- Do not edit a file whose first line says it was generated. The kiln block in
  [CLAUDE.md](CLAUDE.md) says what that means and what to do instead.

## Conventions

- Python 3.14, `src/` layout per package, pyright strict, ruff for lint and
  format.
- Each package is published on its own `<package>-v<version>` tag. Adding a
  package means adding it to `.rn-forge/kiln/config.toml` and re-applying, not
  editing the workflow.
- Packages do not import each other; `.importlinter` enforces it.
