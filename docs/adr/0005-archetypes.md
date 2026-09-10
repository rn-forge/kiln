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

### Alternatives considered

- **One `python-web` archetype with `backend` and `web_runner` config keys.**
  The revision-7 design. Two config keys that between them select four
  template sets is four archetypes wearing a trench coat, and the archetype
  name — the thing a human reads in `config.toml` — stops saying what the repo
  is.
- **Six archetypes, frontend runner in the name.** Rejected: `-ng` already means
  a pnpm-managed Nx workspace, which is Nx's own documented shape. A non-Nx
  pnpm variant is not a different archetype until a repo needs one.
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

Four archetypes, asserted in config:

| Archetype | Shape | Prior art | Release tag |
| -- | -- | -- | -- |
| `python-cli` | one uv package, `src/` layout, pytest/ruff/pyright at root | agentkit | `v<version>` |
| `python-lib` | uv workspace of published packages; per-package verify and release | pykit | `<package>-v<version>` |
| `python-django-ng` | uv workspace + Django API + a pnpm-managed Nx workspace for the frontend, one MkDocs site over both | apollo | `v<version>` |
| `python-fastapi-ng` | as above with FastAPI | intellibench | `v<version>` |

`-ng` means a **pnpm-managed Nx workspace** — Nx's own documented shape — so
there is no `web_runner` key. Whether that workspace uses Nx Cloud is a config
option, because it is an account decision rather than a repo shape.

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

- **Every repo depends on `rn-forge-commons`**; a `python-cli` repo also on
  `rn-forge-tooling`; an `-ng` repo also on its framework package, with that
  package's `[codegen]` extra as a *dev* dependency, since kiln discovers
  generators through an entry-point group in the environment kiln runs in and
  never in the one the application ships.
- **`tooling` is a runtime dependency of a CLI**, not a dev one. It is the
  development-*layer* package because of what it holds — console and Typer
  conventions, local state, templates — not because of when it is installed.
  For a CLI, that layer is the runtime.
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
- Adding an archetype is a template set plus a golden repo: real work, bounded,
  and reviewable the same way. Bending an existing one is none of those.
- Snapshot tests are byte-exact, so a whitespace change in a template is a
  failing test until the golden repo agrees.
