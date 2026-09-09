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
