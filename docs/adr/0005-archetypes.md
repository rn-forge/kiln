# ADR-0005 — An archetype is a shape, a library set, and a golden repo

**Status:** accepted

## Context

Repo shape varies along axes that would multiply if each became its own
dimension: what the repo is, which backend framework it uses, whether it
publishes a docs site. But shape is only half of what makes a repo *ours*. The
other half is what it is built on — the component libraries that mean it does
not write the boilerplate again. The fleet showed both halves failing:

- agentkit depends on `jinja2`, `pydantic`, `rich`, `ruamel-yaml`, `tomlkit` and
  `typer` directly and grew its own `core/{state,config,paths,io}.py`, while
  pykit's commons already held most of it (F12, F17).
- apollo *did* reuse commons, via `{ git = "…/pykit", branch = "main" }` — a
  declaration it invented alone, and an unpinned one: what apollo builds
  changes when pykit's main moves, without a tracked byte in apollo changing.

Templates have a review problem of their own. A template is reviewed as a diff
of placeholders, which is exactly the form in which a missing gate or a wrong
pin is hardest to see — and the fleet's four divergent pipelines were each
reviewed that way at some point.

A third failure surfaced in the Phase C review. `python-cli` was one name for
two different repos: a business batch or ML job that exposes a command line to a
scheduler, and an installable developer tool that owns `$RNF_HOME`, installs and
updates itself, keeps local state and loads plugins. They have the same file
shape and completely different library sets, and collapsing them is what forced
`rn-forge-tooling` to be a package that most of the fleet was told not to use
([ADR-0002](0002-the-dependency-graphs.md)).

### Alternatives considered

- **One `python-web` archetype with `backend` and `web_runner` config keys.**
  The revision-7 design. Two config keys that between them select four
  *topologies* is four archetypes wearing a trench coat, and the archetype
  name — the thing a human reads in `config.toml` — stops saying what the repo
  is. The rule below keeps that rejection while allowing the narrower kind of
  flag that only swaps an implementation library.
- **Six archetypes, frontend runner in the name.** Rejected: `-ng` already means
  a pnpm-managed Nx workspace, which is Nx's own documented shape. A non-Nx
  pnpm variant is not a different archetype until a repo needs one.
- **One `python-cli` archetype, with the tool capabilities as an opt-in
  dependency.** Rejected: an archetype *is* a library set, and the checker
  that enforces it (`check_rn_forge_deps.py`) needs one answer for `REQUIRED`.
  An archetype whose required set is a matter of taste enforces nothing.
- **"Is it a monorepo" as the axis.** It does not discriminate: `python-lib`,
  `python-app`, `python-web-app` and `node-lib` can all be workspaces. What
  separates them is whether the workspace *publishes* — per-package release
  tags and a per-package CI matrix — or ships one version.
- **Templates as the source of truth, golden repos as tests generated from
  them.** The normal direction, and the reason four pipelines diverged: the
  reviewer never sees a whole repo.
- **Publish rn-forge libraries to PyPI.** Would make dependency declaration
  trivial. Deferred, not rejected — the release pipeline publishes GitHub
  Releases today, and this decision is written so that adding PyPI later
  relaxes a rule rather than breaking one.
- **`[tool.uv.sources]` for the git location.** What a workspace reaches for
  first, and what apollo used. It is a *local* override that does not survive
  into a built wheel, so a consumer of a published package could not resolve
  the dependency at all.

## Decision

### The catalogue

Seven archetypes, asserted in config. The name states the repo's **shape** and
its **release/CI topology**; nothing else selects those.

| Archetype | Shape | Publishes | Prior art | Release tag |
| -- | -- | -- | -- | -- |
| `python-app` | one uv package, `src/` layout, optional internal-only workspace packages | no | intellibuild batches | `v<version>` |
| `python-tool` | as `python-app`, plus self-install, `$RNF_HOME`, local state, plugins, doctor | no | agentkit, kiln | `v<version>` |
| `python-lib` | uv workspace of published packages; per-package verify and release | yes | pykit | `<package>-v<version>` |
| `python-web-api` | uv workspace, one API service, no separate frontend package; may ship a thin self-contained admin UI | no | — | `v<version>` |
| `python-web-app` | uv workspace + API + a pnpm-managed Nx workspace for the frontend, one MkDocs site over both | no | apollo, intellibench | `v<version>` |
| `node-lib` | pnpm/Nx workspace of published UI libraries | yes | ngkit | `<package>-v<version>` |
| `node-web-app` | standalone pnpm-managed Nx frontend consuming remote APIs | no | — | `v<version>` |

`python-app` and `python-tool` are the split of the former `python-cli`. Both
are command-line programs; only `python-tool` owns files outside its own
directory, and only it takes `rn-forge-tooling`.

`python-web-api` and `python-web-app` replace `python-django-ng` and
`python-fastapi-ng`. The framework moved out of the name because it does not
change the topology; the frontend's presence did not, because it does.

The two node archetypes are **named and deferred**: they need a second toolchain
— pnpm release, node CI, no uv — and nothing in scope for v1 uses them. Naming
them now fixes the taxonomy so `ui-lib` does not arrive later as a one-off.

### When a config flag is allowed

> **The archetype name states the repo's shape and its release/CI topology. A
> config flag may select an implementation library only when it changes neither
> the file topology nor the task graph.**

`framework = "django" | "fastapi"` passes: it changes `tasks/api.yml` primitives
and adds `manage.py`, but the uv workspace, the release model and the CI matrix
are identical. `frontend = "angular" | "react" | "svelte"` passes: it changes
which `nx g` runs; the task graph is `pnpm nx run-many` either way. The rejected
`backend` + `web_runner` pair failed because *together* they selected four
topologies.

**Every flag value that ships has a golden repo.** A value without one is
`untested = true` in `archetype.toml` and `kiln new` refuses it without an
explicit override. That is what stops the flag freedom from reintroducing the
combinatorial explosion this ADR was written to avoid: the catalogue can only
grow as fast as someone is willing to hand-author and run a repo.

For v1 the shipped values are `python-web-app` with **`django + angular`** and
**`fastapi + angular`** — django because `rn-forge-django` already exists and is
the batteries-included path, fastapi because intellibuild needs it — and
`python-web-api` with **`fastapi`**. `react`, `svelte`, and
`python-web-api --framework django` are named and `untested`; the django API
tree is nonetheless exercised inside the django `python-web-app` golden, so
promoting it later is a golden repo, not a design.

`-ng` is gone from archetype names. A pnpm-managed Nx workspace — Nx's own
documented shape — is what `python-web-app`, `node-lib` and `node-web-app` mean,
so there is still no `web_runner` key. Whether that workspace uses Nx Cloud
stays a config option, because it is an account decision rather than a repo
shape.

**Docs profile is orthogonal**: `mkdocs` seeds the full area model (from
agentkit's `_areas.yml`, E17); `external` generates nothing and records
`external_url` in the instructions block; `none` generates nothing. Repos extend
their own `_areas.yml`, which is why it is seeded rather than managed
([ADR-0001](0001-ownership.md)).

### The library set

An archetype carries the libraries a repo of that shape is built on, and the
generated `scripts/standards/check_rn_forge_deps.py` enforces them. The set per
archetype, and the exact rules, live in
[the standard-repo reference](../reference/standard-repo.md#3-the-dependency-set);
the decisions behind them are:

- **Every repo depends on `rn-forge-commons`**; every repo with a command line
  also on `rn-forge-cli`; a `python-tool` repo also on `rn-forge-tooling`; a
  web repo also on its framework package, with that package's `[codegen]`
  extra as a *dev* dependency, since kiln discovers generators through an
  entry-point group in the environment kiln runs in and never in the one the
  application ships.
- **`rn-forge-cli` and `rn-forge-tooling` are runtime dependencies**, not dev
  ones. They are named for what they hold — the process shape, and the
  file-owning machinery — not for when they are installed. For a CLI, that
  layer is the runtime.
- **The dependency is a pinned PEP 508 direct URL in `dependencies`**, never a
  `[tool.uv.sources]` override, because only the former survives into a built
  wheel. Two consequences are accepted deliberately: such a distribution
  cannot be uploaded to PyPI, and the version floor disappears because a
  requirement cannot hold both a URL and a specifier. **The tag is the
  version.**
- **The required list is config**, in the checker's own header, so pykit — which
  *contains* commons and cannot depend on it — renders an empty list rather
  than needing an exemption.

### Golden repos

**Golden repos are the source of truth for the templates.** Each is a complete,
hand-authored, *runnable* repo: `uv sync` and `task validate` pass in it
standalone, its workflows lint, its docs site builds `--strict`, and its
committed checkers run. They are reviewed as if they were the finished product
*before* any generator code exists. The templates are then the golden output
parameterized, and the snapshot tests assert
`render(golden config) == golden bytes`, with the provenance version rendered as
the literal `golden`.

**A template change that is not first made in the golden repo is a bug.**

**Scaffolding shells out.** `kiln new` runs `uv init`, `pnpm create`, `nx g` and
then reconciles the result. kiln never templates another tool's scaffold output.

## Consequences

- The archetype name says what the repo is, and there is no config key whose
  value silently selects a different template set.
- Review happens on real files, in a repo a reviewer can run — at the cost of a
  `uv sync` per fixture in kiln's own CI. That cost is the point: it is the
  only proof that the templates produce a working repo.
- A generated repo starts with the component libraries wired in, which is the
  point of naming archetypes at all. Both golden repos depend on commons and
  *use* it, so the fixture proves the wiring rather than asserting it.
- Every golden repo's `uv sync` fetches from GitHub. pykit is public, so no CI
  credential is needed, and the pinned tag keeps resolution reproducible.
- Bumping a pin is a kiln release, not a per-repo decision — a fleet on one
  commons version is worth more than each repo tracking main.
- Adding an archetype, *or a flag value*, is a template set plus a golden repo:
  real work, bounded, and reviewable the same way. Bending an existing one is
  none of those.
- Seven archetypes and two flags is a bigger catalogue than four with none. The
  golden-repo-per-shipped-value rule is what keeps it from being a bigger
  *surface*: six golden repos exist at v1 — `golden-app`, `golden-tool`,
  `golden-lib`, `golden-api`, and the two `golden-web` variants — not the
  fourteen the flag matrix could name.
- Snapshot tests are byte-exact, so a whitespace change in a template is a
  failing test until the golden repo agrees.
