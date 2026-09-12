# golden-tool

The golden repo for the `python-tool` archetype: a complete, runnable repository
whose every generated file is exactly what kiln must render for a single-package
Python tool. Its product is one function and one command; everything else is the
standard.

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
