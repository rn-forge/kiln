# The rn-forge workspace

Workspace-level material that is not a kiln decision: what each component is,
what it owns, and the dependency graphs. pykit references this page rather than
repeating it.

## Components

| Component | Kind | Owns |
| -- | -- | -- |
| **commons** (`rn-forge-commons`, in pykit) | library | runtime-neutral Python, data and filesystem mechanisms, integration protocols, `AppConsole` |
| **cli** (`rn-forge-cli`, in pykit) | app library | the Typer layer: `CliApp` (`from_config`, exit codes), `CliOptions`, the declared `[cli]` surface |
| **tooling** (`rn-forge-tooling`, in pykit) | dev-tool library | the generation engine, templates, local state, docs mechanics, the lifecycle surface |
| **web** (`rn-forge-web`, in pykit) | library | framework-free inbound HTTP wire semantics; depends on commons only |
| **django** / **fastapi** (`rn-forge-django`, `rn-forge-fastapi`, in pykit) | framework libraries | adapters over web; `[codegen]` extras later |
| **kiln** (`rn-forge/kiln`, binary `kiln`) | CLI + canon | the canon (ADRs, the standard-repo spec, runbooks); archetypes; the `core` module and the concern modules `python`, `docs`, `tasks`, `cicd`, `instructions`; `doctor` |
| **checks** (`rn-forge-kiln-checks`, in kiln) | dev-dependency library | the checkers CI runs; its shape is open on [F4.1](../specs/epics/E4-generator/F4.1-checks-by-module.md) |

Not built, or retired: a separate canon repo, taskkit, `go-task-setup`,
`docs-setup`, `mkdocs-site-setup`, `spec-structure-setup`, `forge-core`,
`forge-ci`, `docskit`.

## The graphs

```text
commons ──► cli ──► tooling ──► kiln ──► kiln-checks  (checks never imports kiln)
   │         │         │    └──► rn-forge-django[codegen]  (extra; never the runtime surface)
   │         │         └───────► every repo with lifecycle = true
   │         └─────────────────► every python-app / python-web-* repo
   └───────────────────────────► rn-forge-web ──► rn-forge-django, rn-forge-fastapi

kiln ──entry points─► *[codegen]    (kiln discovers generators; never imports a framework)
CI ──► kiln-checks + tooling        (verification only; CI never installs kiln)
```

The **library graph is acyclic**: commons, cli and tooling are the only rn-forge
packages that may be a build dependency of a kit, and each depends only
downward. The **tooling graph is free**: kiln imports no other kit and invokes
none, and pykit adopting kiln as dev tooling is not a cycle because nothing is
imported. The placement test is what an API's *signature* contains, not who
calls it today. See [ADR-0002](../adr/0002-the-dependency-graphs.md).

## Where a thing belongs

| It is… | It lives in |
| -- | -- |
| runtime-neutral, and a Django app could use it | commons |
| the process and command-line shape of any program with a CLI | cli |
| a tool that installs itself, owns files, or renders templates | tooling |
| rn-forge policy: what a repo looks like, what CI does | kiln |
| a framework's code generator | that framework's `[codegen]` extra |

## Apply sequence

`kiln apply` is always this order, and each step is a module exposing its
`artifacts()` and `checks()`
([ADR-0011](../adr/0011-kiln-is-modules-under-one-contract.md)):

```text
1. core         .rn-forge/kiln/, the gitignore block, .editorconfig
2. python       (new repos only) uv init / pnpm create / nx g, then reconcile; .importlinter
3. docs         the tree, _areas.yml, _structure.md, the mkdocs nav block
4. tasks        Taskfile.yml, tasks/*.yml
5. cicd         workflows, .github/actions/setup, sonar-project.properties
6. instructions README.md / CLAUDE.md / AGENTS.md bodies (seeded), the kiln block, .rn-forge/kiln/standard.md
7. doctor       every check; apply exits non-zero if any error remains
```

No apply step shells out; only `kiln new` runs a scaffolder, before the first
apply ([ADR-0001](../adr/0001-ownership.md)). That module contract is what keeps
kiln from becoming a god-kit: a module is a template set plus a doctor check,
and nothing else.
