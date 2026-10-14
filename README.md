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
([ADR-0006](docs/adr/ADR-0006.md)).

```bash
kiln new ../my-repo --archetype python-tool --yes
kiln apply
kiln doctor
```

## Where kiln is

Working towards [release 1](docs/releases/release-1/index.md). The canon and the
rendered archetype cells match pykit's `feature/upgrade` branch, tool lifecycle
surface included (E1–E3, done 2026-09-15). The
[shared CLI integration](docs/specs/epics/E3-realign-goldens-and-canon/index.md#shared-cli-design)
was proven by the hand-authored golden repos, which have since left git
([S4.4.9](docs/specs/epics/E4-generator/F4.4-render-matrix.md#s449--the-goldens-leave-the-repository)).
E4's render-free checks, module contract, config manager, apply cycle and
concern modules exist, and so does the render matrix. E5's FastAPI and Angular
cells pass their own gates in it. What is left is proving them from a clean
clone, the owner's approval, and a first real project
([F5.3](docs/specs/epics/E5-web-archetypes/F5.3-shipped-web-cells.md)). Django
is deferred until a real repository needs it. The order is deliberate —
templates reviewed as templates are how the fleet ended up with four divergent
pipelines, so the standard is reviewed as complete runnable repositories.

```bash
task self:golden:render && task self:golden:validate
```

**Picking this up in a new session?** Read [the spec board](docs/specs/index.md)
for status — what is done and what is next — then the epic you are starting. The
[decision log](docs/adr/index.md) and [context](docs/plans/context.md) record
why, so you do not re-derive it.
[The standard repository](docs/reference/standard-repo.md) is the normative
text.

## Working here

- Run everything through `task`. `task validate` is the gate.
- **A standard change is a template change**, reviewed as the rendered cells
  (`task self:golden:compare BASE=<ref>`), per the
  [render-matrix policy](docs/specs/epics/E4-generator/F4.4-render-matrix.md#template-review-policy).
- The policy and docs checks are `kiln doctor`, and `kiln docs-generate` writes
  the derived regions; no repo carries `scripts/**` for them
  ([ADR-0006](docs/adr/ADR-0006.md)).
- This repo's own skeleton is a hand-copy of the rendered `python-tool` cell. It
  regenerates itself once the generator exists; until then, keep them in step
  by hand — a change to that cell's skeleton is usually a change here too.
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
  of them.

## Conventions

- Python 3.14, `src/` layout under the `rn_forge` namespace, pyright strict,
  ruff for lint and format.
- `tests/fixtures/**` holds the scaffold fixtures (`scaffold/`), and is excluded
  from this repo's ruff, pyright and pytest.
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
