# The rn-forge workspace

Workspace-level material that is not a kiln decision: what each component is,
what it owns, and the two dependency graphs. pykit and agentkit reference this
page rather than repeating it.

## Components

| Component | Kind | Owns |
| --- | --- | --- |
| **commons** (`rn-forge-commons`, in pykit) | library | runtime-neutral Python, data and filesystem mechanisms, and integration protocols |
| **tooling** (`rn-forge-tooling`, in pykit) | dev library | shared console/CLI conventions, local state, templates, the generation engine, installer mechanics |
| **kiln** (`rn-forge/kiln`, binary `kiln`) | CLI + canon | the canon (ADRs, the standard-repo spec, runbooks); archetypes and golden repos; the `.rn-forge/` umbrella; `Taskfile.yml` + `tasks/**`; the docs tree + MkDocs; CI; `doctor` |
| **agentkit** (`rn-forge/agentkit`) | CLI | `.claude/**`, `.codex/**`, the `CLAUDE.md`/`AGENTS.md` body, generic skills |
| `rn-forge-django[codegen]` | extra | framework templates, option schemas, generator entry points |

Not built, or retired: a separate canon repo, taskkit, `go-task-setup`,
`docs-setup`, `mkdocs-site-setup`, `spec-structure-setup`, `forge-core`,
`forge-ci`, `docskit`.

## The two graphs

```text
commons (pykit) ──► tooling (pykit) ──► kiln
                          │       └───► agentkit
                          └───► rn-forge-django[codegen]

kiln ──subprocess──► agentkit          (never the reverse)
kiln ──entry points─► *[codegen]       (kiln never imports a framework)
```

The **library graph is acyclic**: commons and tooling are the only rn-forge
packages that may be a build dependency of a kit, and commons never imports
tooling. The **tooling graph is free**: kiln and agentkit never import each
other, and pykit adopting kiln as dev tooling is not a cycle because nothing is
imported. See [ADR-0003](../adr/0003-the-dependency-graphs.md).

## Where a thing belongs

| It is… | It lives in |
| --- | --- |
| runtime-neutral, and a Django app could use it | commons |
| a local-development mechanism shared by kits | tooling |
| rn-forge policy: what a repo looks like, what CI does | kiln |
| agent configuration: hooks, adapters, instruction bodies | agentkit |
| a framework's code generator | that framework's `[codegen]` extra |

## Apply sequence

`kiln apply` is always this order, and each step is a module exposing exactly
`artifacts(config)` and `checks(config, root)`:

```text
1. umbrella      .rn-forge/kiln/, the gitignore block, .editorconfig
2. scaffold      (new repos only) uv init / pnpm create / nx g, then reconcile
3. docs          the tree, _areas.yml, _structure.md, the mkdocs nav block, scripts/docs/*
4. tasks         Taskfile.yml, tasks/*.yml, scripts/task/*, scripts/ci/*, scripts/standards/*
5. ci            workflows, sonar-project.properties
6. agentkit      subprocess: `agentkit project init`, or `update` if already present
7. instructions  the CLAUDE.md / AGENTS.md kiln block, .rn-forge/kiln/standard.md
8. doctor        every check; apply exits non-zero if any error remains
```

Step 6 is skipped with a warning when `agentkit` is not on `PATH`. Step 7 runs
after step 6 so that the instruction files exist to hold a block.

That two-function module contract is what keeps kiln from becoming a god-kit: a
module is a template set plus a doctor check, and nothing else.
