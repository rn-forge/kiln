# golden-lib

The golden repo for the `python-lib` archetype: a complete, runnable uv
workspace whose every generated file is exactly what kiln must render for a
repository of published library packages. Its product is two functions;
everything else is the standard.

- [Architecture](architecture/index.md) — how the repo is put together.
- [Guides](guides/index.md) — how to work in it.
- [Runbooks](runbooks/index.md) — procedures that need judgement.
- [Reference](reference/python-api.md) — the generated Python API.
- [Releases](releases/index.md) — what shipped when.
- [Specs](specs/index.md) — work planned and done.
- [Decisions](adr/index.md) — the ADR log.

The repository standard this tree obeys is rendered into
`.rn-forge/kiln/standard.md` by kiln; the reasoning behind it lives in the kiln
repo's own decision log.
