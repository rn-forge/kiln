# Creating a repository

`kiln new` does the mechanical part. This runbook covers the three points where
it cannot decide for you: which archetype, what stays repository-owned, and what
to do when the repo does not fit.

> [E1](../specs/epics/E1-canon-and-golden-repos/index.md) shipped the canon and
> the golden repos; `kiln new` itself lands in
> [E4](../specs/epics/E4-generator/index.md). Until then the procedure below is
> what a human follows by hand, using `tests/fixtures/golden/<archetype>/` as
> the reference repo.

## 1. Choose the archetype

Ask what the repo *ships*, not what it contains.

| If it ships… | Archetype |
| -- | -- |
| a batch, a scheduled job or an ML pipeline behind a command line | `python-app` |
| a tool people install, that owns files and keeps local state | `python-tool` |
| several independently versioned packages | `python-lib` |
| an API service with no separate frontend package | `python-web-api` |
| an API service plus an Nx frontend app | `python-web-app` |
| several independently versioned UI libraries | `node-lib` *(deferred)* |
| a standalone Nx frontend against remote APIs | `node-web-app` *(deferred)* |

Then choose the flags: `--framework django|fastapi` for the web archetypes,
`--frontend angular|react|svelte` for `python-web-app`. A flag value with no
golden repo is `untested` and `kiln new` refuses it.

Rules of thumb for the awkward cases:

- **`python-app` versus `python-tool`: does it own files outside its own
  directory?** A batch that reads a database and writes a report is
  `python-app`. Anything with self-install, `$RNF_HOME`, local state or
  plugins is `python-tool`, and only `python-tool` takes `rn-forge-tooling`.
- **A service with a thin built-in admin surface — Django admin, an actuator
  page — is still `python-web-api`.** `python-web-app` is for a separate,
  independently built frontend package.
- **A workspace whose packages are never released separately is `python-app`,
  not `python-lib`.** The whole difference between them is per-package
  versions and per-package release tags. If there is one version number, there
  is one package as far as the standard is concerned. "Is it a monorepo" does
  not decide anything: every archetype here can be one.

If none fits, stop and write an ADR in the new repo before generating anything.
A new archetype — or a new flag value — is a template set plus a golden repo:
real work, but bounded and reviewable. Bending an existing archetype is neither.

## 2. Generate

```bash
kiln new ../my-repo --archetype python-app --docs mkdocs --yes
```

Without `--yes` this previews and writes nothing. Every prompt has a flag, so
the same command is what an agent runs unattended. `kiln new` refuses a
non-empty directory.

What it does, in order, is the apply sequence in
[the workspace architecture](../architecture/workspace.md#apply-sequence). Step
2 shells out to `uv init` (and `pnpm create` / `nx g` for the `-ng` archetypes)
and then reconciles the result; kiln never templates another tool's scaffold
output.

## 3. Wire in what is genuinely this repo's

Everything repo-specific attaches through `.rn-forge/kiln/config.toml`. Nothing
attaches by editing a generated file.

A repo-owned namespace file, for tasks that are nobody else's business:

```toml
[tasks]
includes = [{ namespace = "self", taskfile = "tasks/self.yml" }]

[tasks.extra_refs]
lint = ["self:check:brand"]
```

`tasks/self.yml` is seeded once and never rewritten. `extra_refs` appends to a
managed wrapper, so `task lint` runs the repo's own lint without the root
Taskfile ceasing to be kiln's.

For a primitive whose shell line is wrong for this repo — and only then:

```toml
[tasks.command_overrides]
"quality:test:python" = "uv run pytest -q -p no:randomly"
```

If you find yourself wanting a third override, the archetype is probably wrong.
That is a judgement call, and it is yours.

If the new repo replaces a pre-v1 one, carry its specs and decisions over now,
following [carrying specs and decisions](carrying-specs-and-decisions.md).

## 4. Check it

```bash
task validate     # what CI will run
kiln doctor       # plus: would a newer kiln render something different?
```

`task validate` must pass on a cold clone with no kiln installed. If it does
not, the repo is not finished, whatever `kiln doctor` says.

## 5. Before the first push

- GitHub Pages must be enabled with **Source: GitHub Actions**. No workflow can
  do this for you, and the docs deploy fails until it is done.
- `SONAR_TOKEN` must exist as a repository secret if `ci.sonar = true`.
- The first release tag is created by CI on the first push to `main` whose
  version is not yet tagged. If you do not want that, set
  `[ci] release = "none"` before pushing.
