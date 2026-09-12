# kiln

The rn-forge repository generator, and the canon it generates against.

kiln owns anything deterministic about a repository: the `.rn-forge/` umbrella,
`Taskfile.yml` and `tasks/**`, the docs tree and its MkDocs site, the workflows,
and the bodies of `README.md`, `CLAUDE.md` and `AGENTS.md`. Every managed file —
or every fenced block inside a shared file — has exactly one owner, and kiln is
it.

**kiln is a developer tool. It never runs in CI.** What CI checks is the
committed `.rn-forge/kiln/state.json` baseline, through `task validate`, against
pinned dev dependencies. It never runs a generator.

```bash
kiln new ../my-repo --archetype python-tool --yes
kiln apply
kiln doctor
```

## Where kiln is

Phase C.2 of the [standardization plan](docs/plans/standardization-plan.md),
reviewed: the canon and the golden repos exist; there is no generator code yet.
The order is deliberate — templates reviewed as templates are how the fleet
ended up with four divergent pipelines, so the standard is reviewed first, as
complete runnable repositories under `tests/fixtures/golden/`.

```bash
cd tests/fixtures/golden/python-app     # or python-tool, or python-lib
uv sync && task validate
```

**Picking this up in a new session?** Read
[§0.1 of the plan](docs/plans/standardization-plan.md) for status — what is done
and what is next — then §0.9 for what the last review changed and why, so you do
not re-derive it. [The standard repository](docs/reference/standard-repo.md) is
the normative text; the [decision log](docs/adr/index.md) is why.

## Working here

- Run everything through `task`. `task validate` is the gate.
- **The golden repos under `tests/fixtures/golden/` are the source of truth for
  the templates.** A standard change starts there, in real files, and is
  proven by running that repo's own `uv sync && task validate` from inside it.
  A template change not first made in a golden repo is a bug
  ([ADR-0005](docs/adr/0005-archetypes.md)).
- A generated script's body is byte-identical across every golden repo; only the
  `# BEGIN kiln config` header differs. `task test` enforces it. This goes
  away at Phase D, when the checkers become a pinned package
  ([ADR-0010](docs/adr/0010-checkers-are-a-package.md)).
- This repo's own skeleton is a hand-copy of the `python-tool` golden repo. It
  regenerates itself once the generator exists; until then, keep them in step
  by hand — a change to a golden repo's skeleton is usually a change here too.
- **After changing any managed file, re-seed the state baseline.** There is no
  `kiln apply` yet, so `.rn-forge/kiln/state.json` is written by hand;
  `task lint` fails with `has drifted from the committed state` until it
  agrees.
- An ADR carries a decision and the alternatives rejected. The moment it starts
  enumerating — verbs, paths, dependency sets — it has become a spec and
  belongs in `docs/reference/standard-repo.md` (D48).
- Prose has one home: this file. `CLAUDE.md` points here and carries the fenced
  blocks; `AGENTS.md` points at `CLAUDE.md`. Do not restate a paragraph in two
  of them (D57).

## Conventions

- Python 3.14, `src/` layout under the `rn_forge` namespace, pyright strict,
  ruff for lint and format.
- `tests/fixtures/**` is excluded from this repo's ruff, pyright and pytest:
  each golden repo is held to its own archetype's configuration, by its own
  gate.
- This repo has a `plans/` docs area that kiln's seeded model does not — which
  is the point of the model being seeded (D44).

## Documentation

- [Where the work stands](docs/plans/standardization-plan.md) — the plan of
  record
- [The standard repository](docs/reference/standard-repo.md) — the normative
  text
- [Decisions](docs/adr/index.md) — ADRs 0001–0010
- [The rn-forge workspace](docs/architecture/workspace.md) — components and
  graphs
- [Creating a repository](docs/runbooks/creating-a-repo.md)
- [Agent configuration after kiln](docs/plans/agent-config-future.md) — parked
- [docs/\_structure.md](docs/_structure.md) — what belongs where in this tree
