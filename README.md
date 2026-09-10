# kiln

The rn-forge repository generator, and the canon it generates against.

kiln owns anything deterministic about a repository: the `.rn-forge/` umbrella,
`Taskfile.yml` and `tasks/**`, the committed CI checkers, the docs tree and its
MkDocs site, the workflows. Every managed file — or every fenced block inside a
shared file — has exactly one owner, and kiln is it.

**kiln is a developer tool. It never runs in CI.** What CI checks is the
committed `.rn-forge/kiln/state.json` baseline, through `task validate`, with
stdlib-only checkers that kiln generated and the repo committed. A cold clone
builds without kiln installed.

```bash
kiln new ../my-repo --archetype python-cli --yes
kiln apply
kiln doctor
```

## Where kiln is

Phase B of the [standardization plan](docs/plans/standardization-plan.md),
reviewed and revised: the canon and the golden repos exist; there is no
generator code yet. The order is deliberate — templates reviewed as templates
are how the fleet ended up with four divergent pipelines, so the standard is
reviewed first, as complete runnable repositories under
`tests/fixtures/golden/`.

```bash
cd tests/fixtures/golden/python-cli
uv sync && task validate
```

**Picking this up in a new session?** Read
[§0.1 of the plan](docs/plans/standardization-plan.md) for status, then §0.6 for
what the last review changed, then §3 for the next phase.

## Documentation

- [Where the work stands](docs/plans/standardization-plan.md) — the plan of
  record
- [The standard repository](docs/reference/standard-repo.md) — the normative
  text
- [Decisions](docs/adr/index.md) — ADRs 0001–0009
- [The rn-forge workspace](docs/architecture/workspace.md) — components and
  graphs
- [Creating a repository](docs/runbooks/creating-a-repo.md)
- [docs/\_structure.md](docs/_structure.md) — what belongs where in this tree
