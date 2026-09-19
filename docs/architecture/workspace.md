# The rn-forge workspace

Workspace-level material that is not a kiln decision: what each component is,
what it owns, and the dependency graphs. pykit references this page rather than
repeating it.

## Components

| Component | Kind | Owns |
| -- | -- | -- |
| **commons** (`rn-forge-commons`, in pykit) | library | runtime-neutral Python, data and filesystem mechanisms, integration protocols, `AppConsole` |
| **cli** (`rn-forge-cli`, in pykit) | app library | the Typer layer: `CliApp` (`from_config`, exit codes), `CliOptions`, the declared `[cli]` surface |
| **tooling** (`rn-forge-tooling`, in pykit) | dev-tool library | the generation engine, templates, local state, the lifecycle surface |
| **web** (`rn-forge-web`, in pykit) | library | framework-free inbound HTTP wire semantics; depends on commons only |
| **django** / **fastapi** (`rn-forge-django`, `rn-forge-fastapi`, in pykit) | framework libraries | adapters over web; `[codegen]` extras later |
| **kiln** (`rn-forge/kiln`, binary `kiln`) | CLI + canon; a pinned dev dependency of every generated repo | the canon (ADRs, the standard-repo spec, runbooks); archetypes; the `core` module and the concern modules `python`, `docs`, `tasks`, `cicd`, `instructions`; generation and `doctor` verification |

Not built, or retired: a separate canon repo, taskkit, `go-task-setup`,
`docs-setup`, `mkdocs-site-setup`, `spec-structure-setup`, `forge-core`,
`forge-ci`, `docskit`.

## The graphs

```text
commons ──► cli ──► tooling ──► kiln
   │         │         │    └──► rn-forge-django[codegen]  (extra; never the runtime surface)
   │         │         └───────► every repo with lifecycle = true
   │         └─────────────────► every python-app / python-web-* repo
   └───────────────────────────► rn-forge-web ──► rn-forge-django, rn-forge-fastapi

kiln ──entry points─► *[codegen]    (kiln discovers generators; never imports a framework)
CI ──► pinned kiln + tooling        (kiln doctor always, kiln doctor --full where asked; never apply — ADR-0006)
```

The **library graph is acyclic**: commons, cli and tooling are the only rn-forge
packages that may be a build dependency of a kit, and each depends only
downward. The **tooling graph is free**: kiln imports no other kit and invokes
none, and pykit adopting kiln as dev tooling is not a cycle because nothing is
imported. The placement test is what an API's *signature* contains, not who
calls it today. These are pykit library-design constraints. kiln consumes these
libraries and owns repository policy; it does not own their internal graph
([ADR-0002](../adr/ADR-0002.md)).

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
`artifacts()` and `checks()` ([ADR-0001](../adr/ADR-0001.md)):

```text
1. core         .rn-forge/kiln/ only (not its siblings), the gitignore block, .editorconfig
2. python       managed Python artifacts, including .importlinter
3. docs         the managed mkdocs nav block; docs content is seeded
4. tasks        Taskfile.yml, tasks/*.yml
5. cicd         workflows, .github/actions/setup, sonar-project.properties
6. instructions the kiln block, .rn-forge/kiln/standard.md; prose bodies are seeded
7. doctor       every check; apply exits non-zero if any error remains
```

Seeded files belong to the repository after scaffolding; doctor does not enforce
their presence or contents.

No apply step shells out; only `kiln new` runs a scaffolder, before the first
apply. Each module owns its configuration, options, artifacts and checks; kiln
composes them through the
[module contract](../specs/epics/E4-generator/design.md#the-module-contract).
