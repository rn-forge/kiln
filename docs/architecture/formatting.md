# Formatting

How the generated repositories are formatted, in every archetype kiln has. The
model is [ADR-0021](../adr/ADR-0021.md), built by
[E19](../specs/epics/E19-formatting-standard/index.md).

**Status.** Markdown, TOML, Python and the Node archetypes' Prettier run as
described. Everything marked *E19* below, which is the YAML formatter and the
checks that go with it, is not built yet. Until it is, the Python archetypes
format no YAML, and the Node archetypes format YAML with Prettier except in the
files kiln owns.

## The model

- **One owner per file type.** Each type has one formatter in every archetype it
  occurs in. A file is never formatted by two tools, and a type is not
  formatted differently in two archetypes.
- **A toolchain formatter stays in its toolchain.** ruff is in `python:` and
  Prettier is in `node:`; they own what their language needs.
- **Every other type has a uv-installed formatter in `quality:`.** The tasks
  come in pairs, `quality:lint:<type>` and `quality:format:<type>`, both
  `internal: true`, called by the root `lint` and `format` verbs
  ([Tasks](tasks.md)).
- **Lint and format agree.** The check is the formatter's own `--check`, so
  `task format` never leaves a file that `task lint` still rejects.
- **kiln's own files are formatted too.** A generated workflow, task file or
  config is held to the same formatter as the repository's files, so a
  template that renders unformatted output is a defect found by a test
  (*E19*).

## File types and their owners

| Type | Formatter | Namespace | Archetypes | Built |
| -- | -- | -- | -- | -- |
| Python | ruff (`ruff check --fix`, then `ruff format`) | `python:` | the Python archetypes, and the backend of `python-web-app` | yes |
| Markdown | mdformat, with its plugins from the `docs` group | `quality:` | every archetype | yes |
| TOML | taplo, from the `dev` group | `quality:` | every archetype | yes |
| TypeScript, HTML, SCSS, JSON | Prettier (`pnpm exec prettier`) | `node:` | `node-lib`, the frontend of `python-web-app` | yes |
| YAML | the Node archetypes: Prettier, except the kiln-owned files; the Python archetypes: none | `node:` | the Node archetypes | yes |
| YAML | one uv-installed formatter, from the `dev` group | `quality:` | every archetype | *E19* |
| JSON | none | none | the Python archetypes | parked ([ADR-0021](../adr/ADR-0021.md)) |

The tools' versions are floors in the rendered `pyproject.toml`
(`modules/python/scaffold.py`, `_DEV_GROUP` and `_DOCS_GROUP`), so the lock pins
them. A Node archetype carries a root `pyproject.toml` with no package, which is
how it has mdformat, taplo and MkDocs.

## How the file list is built

The Markdown and TOML tasks share one `FILES` variable in `tasks/quality.yml`:

```text
git grep --untracked -lz -e '' -- '<glob>' | xargs -0 -r <tool>
```

- Tracked and untracked files, less what `.gitignore` ignores, so caches, build
  output and virtualenvs are never seen.
- `git grep -e ''` lists only files present in the working tree, so a deleted
  file is skipped.
- A `.git` guard stops a repository without its own from listing an enclosing
  repository's files.
- Each task passes a glob, such as `'*.md'` or `'*.toml'`. The YAML pair (*E19*)
  passes `'*.yml'` and `'*.yaml'`.
- The Markdown pair batches, `xargs -0 -r -n 20 -P 4`, twenty files to each of
  four processes (S17.3.4). The TOML pair, and the YAML pair (*E19*), run
  serially.
- `command_overrides` replaces one task's command, keyed by the task name
  (`quality:lint:markdown`, and so on); the other task of the pair keeps its
  own.

## Lint and format in the gate

`lint` calls every `quality:lint:*` task, so `validate` runs them, and
`required_validate` in each archetype's `archetype.toml` names them so that
`task-layout` fails when one stops being reachable ([Tasks](tasks.md)). `format`
calls every `quality:format:*` task, after `python:format` and `node:format`.
The order matters only for ruff, which runs `check --fix` and then `format` to
make the two agree.

In the Node archetypes `node:lint:format` runs `prettier --check .`, and
`node:format` runs `prettier --write .`. They belong to `node:` because Prettier
is the toolchain's.

## Ignore files and config

| File | Owner | Holds |
| -- | -- | -- |
| `.mdformat.toml` | the repository, seeded once | `wrap`, the plugin options, and `exclude` for kiln's `.rn-forge/kiln/standard.md` |
| `.taplo.toml` | the repository, seeded once | `include`, `exclude` and the 4-space style |
| the YAML formatter's config (*E19*) | the repository, seeded once | the few style keys, and the exclusion of `pnpm-lock.yaml` |
| `.prettierrc` | kiln, managed | the Prettier options, in the Node archetypes |
| `.prettierignore` | kiln's fenced block, plus the repository's own lines | what Prettier must not touch: the types other tools own (`*.md`, `*.toml`, `*.py`, `*.pyi`, and with *E19* `*.yml` and `*.yaml`), generated and installed paths, and the paths kiln owns |
| `.editorconfig` | kiln, managed | the editor's indent: 2 by default, 4 for TOML and Python |

A tool that does not own a type lists it in its own ignore file. That is how
Prettier and mdformat never format the same file
([ADR-0012](../adr/ADR-0012.md)), and how Prettier and the YAML formatter will
not (*E19*).

## How kiln's own files are proven clean

Until E19, two guards exist: the seeded `.mdformat.toml` and `.taplo.toml` are
taplo-clean, and `kiln new`'s `config.toml` and `pyproject.toml` are taplo-clean
(`tests/modules/core/test_cycle.py`, `tests/test_new.py`). Instruction blocks
are rendered already mdformat-clean.

With E19 one test renders every archetype and runs mdformat, taplo and the YAML
formatter in check mode over everything that is rendered
(`tests/test_formatting_clean.py`). A template that renders output a formatter
would change fails it. The fix is in the template, never in a rendered file. The
check that a rendered file still equals its template is `kiln doctor`'s
`generated` check; it and the formatting check meet in the template.

## Adding a type, or excluding a file

- **Exclude a file** the repository does not want formatted: add it to the
  tool's own config (`exclude` in `.mdformat.toml` or `.taplo.toml`, or the
  YAML formatter's) or, for Prettier, to the lines of `.prettierignore`
  outside kiln's block. A file a package manager writes belongs in the config
  kiln seeds.
- **Add a type** kiln does not format: a repository puts a formatter in its own
  task file, wired through `[tasks] includes` and `[tasks.extra_refs]` for
  `lint` and `format` ([Tasks](tasks.md)). A type that every archetype needs
  is a decision of the shape of [ADR-0021](../adr/ADR-0021.md): one formatter,
  one task pair, and an ignore line wherever another tool would touch it.
