# golden-cli

The golden repo for kiln's `python-cli` archetype: a complete, runnable
repository whose every generated file is exactly what kiln must render for a
single-package Python CLI.

It is a fixture, and it is also a real repo — `uv sync && task validate` passes
in it standalone. That is the point: a template proven only in the abstract has
never been proven to produce a working repo.

```bash
uv sync
task validate
```

The product is one function in `src/golden_cli/`. Everything else is the
standard, stated in [.rn-forge/kiln/standard.md](.rn-forge/kiln/standard.md) and
documented in [docs/](docs/index.md).
