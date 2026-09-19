# golden-tool

The golden repo for kiln's `python-tool` archetype: a complete, runnable
repository whose every generated file is exactly what kiln must render for a
single-package Python tool — an installable command line built on all three
rn-forge python libraries.

It is a fixture, and it is also a real repo — `uv sync && task validate` passes
in it standalone. That is the point: a template proven only in the abstract has
never been proven to produce a working repo.

```bash
uv sync
task validate
```

The product is one function, one command and a three-line `main` in
`src/golden_tool/`, and the command line around them is declared rather than
written (kiln ADR-0002); `lifecycle = true` mounts the install verbs over it.
Everything else is the standard, stated in
[.rn-forge/kiln/standard.md](.rn-forge/kiln/standard.md) and documented in
[docs/](docs/index.md).

## Working here

- Run everything through `task`. `task validate` is the gate.
- The product lives in `src/golden_tool/`; its tests live in `tests/`. The CLI
  is *declared* in the `[cli]` table of `.rn-forge/kiln/config.toml` and built
  by `CliApp.from_config` — `main.py` constructs nothing (kiln ADR-0002).
- What the lifecycle verbs install and check is `src/golden_tool/product.py`,
  named by `[cli.lifecycle]`. That module is the whole of the difference
  between this repo and `golden/python-app`.
- Do not edit a file whose first line says it was generated. The kiln block in
  [CLAUDE.md](CLAUDE.md) says what that means and what to do instead.

## Conventions

- Python 3.14, `src/` layout, pyright strict, ruff for lint and format.
- `rn-forge-commons`, `rn-forge-cli` and `rn-forge-tooling` are the only
  rn-forge packages this repo may import.
- Tests are plain pytest with no fixtures beyond what the case needs.
