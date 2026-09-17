# kiln

The rn-forge repository generator, and the canon it generates against.

kiln owns anything deterministic about a repository: the `.rn-forge/` umbrella,
`Taskfile.yml` and `tasks/**`, the docs tree and its MkDocs site, the workflows,
and the bodies of `README.md`, `CLAUDE.md` and `AGENTS.md`. Every managed file —
or every fenced block inside a shared file — has exactly one owner, and kiln is
it.

**kiln is a developer tool, and a pinned dev dependency of every repo it
generates.** CI runs that pinned kiln through `task validate` to check the
committed `.rn-forge/kiln/state.json` baseline. It never writes a generated file
([ADR-0010](docs/adr/ADR-0010.md)).

```bash
kiln new ../my-repo --archetype python-tool --yes
kiln apply
kiln doctor
```

## Where kiln is

Working towards [release 1](docs/releases/release-1/index.md). The canon and the
hand-authored golden repos exist and match pykit's `feature/upgrade` branch,
tool lifecycle surface included (E1–E3, done 2026-09-15).
[ADR-0009](docs/adr/ADR-0009.md) is accepted. E4, the generator, is under way —
`kiln doctor`'s render-free checks exist (F4.1), and so do the module contract,
the config manager and `core`'s apply cycle (F4.2). Of the concern modules
(F4.3), every module renders its templates; the scaffold's dependency lines
(S4.3.7) are next. The order is deliberate — templates reviewed as templates are
how the fleet ended up with four divergent pipelines, so the standard is
reviewed first, as complete runnable repositories under
`tests/fixtures/golden/`.

```bash
cd tests/fixtures/golden/python-app     # or python-tool, or python-lib
uv sync && task validate
```

**Picking this up in a new session?** Read [the spec board](docs/specs/index.md)
for status — what is done and what is next — then the epic you are starting. The
[decision log](docs/adr/index.md) and [context](docs/plans/context.md) record
why, so you do not re-derive it.
[The standard repository](docs/reference/standard-repo.md) is the normative
text.

## Working here

- Run everything through `task`. `task validate` is the gate.
- **The golden repos under `tests/fixtures/golden/` are the source of truth for
  the templates.** A standard change starts there, in real files, and is
  proven by running that repo's own `uv sync && task validate` from inside it.
  A template change not first made in a golden repo is a bug. This holds until
  the rendered templates reproduce the goldens and they leave git
  ([ADR-0005](docs/adr/ADR-0005.md)).
- The policy and docs checks are `kiln doctor`, and `kiln docs-nav` writes the
  nav; no repo carries `scripts/**` for them
  ([ADR-0010](docs/adr/ADR-0010.md)). The goldens take `rn-forge-kiln` from a
  path source to this checkout, so a change under `src/` reaches their gates
  directly.
- This repo's own skeleton is a hand-copy of the `python-tool` golden repo. It
  regenerates itself once the generator exists; until then, keep them in step
  by hand — a change to a golden repo's skeleton is usually a change here too.
- **After changing any managed file, re-seed the state baseline.** There is no
  `kiln apply` yet, so `.rn-forge/kiln/state.json` is written by hand;
  `task lint` fails with `has drifted from the committed state` until it
  agrees.
- An ADR carries a decision and the alternatives rejected. The moment it starts
  enumerating — verbs, paths, dependency sets — it has become a spec and
  belongs in `docs/reference/standard-repo.md`.
- Work is an epic under `docs/specs/`, a decision is an ADR, and an open
  question lives on the feature it blocks until it becomes one or the other.
  Nothing new goes into `docs/plans/`.
- Prose has one home: this file. `CLAUDE.md` points here and carries the fenced
  blocks; `AGENTS.md` points at `CLAUDE.md`. Do not restate a paragraph in two
  of them ([ADR-0001](docs/adr/ADR-0001.md)).

## Conventions

- Python 3.14, `src/` layout under the `rn_forge` namespace, pyright strict,
  ruff for lint and format.
- `tests/fixtures/**` is excluded from this repo's ruff, pyright and pytest:
  each golden repo is held to its own archetype's configuration, by its own
  gate.
- This repo has a `plans/` docs area that kiln's seeded model does not — which
  is the point of the model being seeded (D44).
- Docstrings describe the contract only (what, args, return, raises); no design
  justification, history, or ADR references — those belong in `docs/guides/`
  or `docs/plans/`. Code comments explain a non-obvious *why* (an ordering
  that matters, a library quirk, a rejected alternative), stay shorter than
  the code they sit beside, and are fixed or deleted in the same edit that
  changes the code they describe. Straightforward code gets no comment at all.

## Documentation

- [Where the work stands](docs/specs/index.md) — the spec board and releases

- [The standard repository](docs/reference/standard-repo.md) — the normative
  text

- [Decisions](docs/adr/index.md) — the ADR log

- [Context](docs/plans/context.md) — how kiln got here

- [The rn-forge workspace](docs/architecture/workspace.md) — components and
  graphs

- [Creating a repository](docs/runbooks/creating-a-repo.md)

- [Agent configuration after kiln](docs/plans/agent-config-future.md) — parked

- [docs/\_structure.md](docs/_structure.md) — what belongs where in this tree
