# Creating a repository

`kiln new` does the mechanical part. This runbook covers the three points where
it cannot decide for you: which archetype, what stays repository-owned, and what
to do when the repo does not fit.

> Phase B of the [standardization plan](../plans/standardization-plan.md) ships
> the canon and the golden repos; `kiln new` itself lands in Phase D. Until then
> the procedure below is what a human follows by hand, using
> `tests/fixtures/golden/<archetype>/` as the reference repo.

## 1. Choose the archetype

Ask what the repo *publishes*, not what it contains.

| If it publishes… | Archetype |
| --- | --- |
| one console script or one library from one package | `python-cli` |
| several independently versioned packages | `python-lib` |
| a running service, with or without a frontend | `python-web` |

Two rules of thumb for the awkward cases:

- **One package that also has a web UI is still `python-web`** if the service is
  the deliverable. The archetype follows the pipeline, and a service's pipeline
  has a frontend build in it.
- **A workspace whose packages are never released separately is `python-cli`,
  not `python-lib`.** The whole difference between them is per-package versions
  and per-package release tags. If there is one version number, there is one
  package as far as the standard is concerned.

If neither fits, stop and write an ADR in the new repo before generating
anything. A fourth archetype is a template set plus a golden repo — real work,
but bounded. Bending an archetype is neither.

## 2. Generate

```bash
kiln new ../my-repo --archetype python-cli --docs mkdocs --yes
```

Without `--yes` this previews and writes nothing. Every prompt has a flag, so
the same command is what an agent runs unattended. `kiln new` refuses a
non-empty directory.

What it does, in order, is the apply sequence in
[the workspace architecture](../architecture/workspace.md#apply-sequence). Step 2
shells out to `uv init` (and `pnpm create` / `nx g` for `python-web`) and then
reconciles the result; kiln never templates another tool's scaffold output.

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
