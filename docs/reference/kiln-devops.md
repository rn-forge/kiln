# kiln-devops subcommands

`kiln-devops` is the CI planner: it reads a uv workspace's own manifests and
tells a pipeline which packages a change affects, which checks to run and which
packages may be released. Generated tasks reach it as `kiln-devops` from the
pinned kiln (`uvx` beside the repository, `uv run` in kiln's own), per
[ADR-0017](../adr/ADR-0017.md).

Run `kiln-devops` from inside a uv workspace. Its root is the nearest directory
at or above the current one whose `pyproject.toml` declares
`[tool.uv.workspace]`. `sonar-target`, `notes` and the three `release-*`
subcommands load no workspace and run in any repository.

| Subcommand | Does |
| -- | -- |
| `plan [BASE]` | Selects the packages a change affects, and writes every job's matrix and package list as `$GITHUB_OUTPUT` lines. |
| `releasable OK_DIR NAME...` | Prints, in dependency order, the selected packages whose checks all passed and whose selected prerequisites are releasable. |
| `released` | Prints `name dir module version` for each `<name>-v<version>` tag at `HEAD`, for `verify-release` and `docs`. |
| `smoke PACKAGE [EXTRA]` | Builds the package and its internal requirements as wheels, installs one extra into a clean venv from the wheels' metadata, and imports the configured modules, or the package's own module when it has no smoke table. |
| `integration PACKAGE` | Starts the package's declared service containers with `docker run`, waits until each is healthy, runs the package's pytest with every `expose` variable set, and removes the containers, also when pytest fails. Exits with pytest's status, or 1 when a service never becomes healthy. |
| `verify-release --source {pypi,git} [TAG]` | Installs a published release into a clean venv and imports its module. `pypi` installs `name==version` with `uv pip install --no-cache`, retrying up to ten times 30 s apart while the index catches up; `git` fetches the tag and installs `name @ git+$REPOSITORY_URL@tag`. Without `TAG` it verifies each `<name>-v<version>` tag at `HEAD`; with `TAG` (a single-package repository's `v<version>`) it verifies the one member. |
| `adapters` | Checks each package that declares `adapters`: every name has a module or subpackage under the package's source directory and an extra of the same name, and none is repeated. Prints one line per problem to stderr and exits 1 if there are any. |
| `sonar-target` | Prints the `branch-arg=` line for the Sonar scan, from the `EVENT_NAME`, `REF_TYPE` and `REF_NAME` environment variables. |
| `sonar-local [--dry-run] [--branch NAME]` | Runs `task test:coverage`, then `sonar-scanner` with the checked-out branch and `-Dsonar.qualitygate.wait=true`, and exits with the scanner's status. Needs `SONAR_TOKEN` and `sonar-scanner` on `PATH`; refuses `main`. `--dry-run` prints the target and both commands and runs nothing. |
| `release-state TAG` | Prints the release's state for `TAG` as `$GITHUB_OUTPUT` lines. |
| `release-source TAG` | Checks out `TAG` when `origin` has it, and prints the checked-out commit. |
| `release-publish TAG --title TITLE --target SHA [--notes-file FILE] [--upload {pypi,testpypi}] FILE...` | Publishes the GitHub release for `TAG` unless it is already published. |
| `notes CHANGELOG VERSION` | Prints the body of the `## [VERSION]` section of a Keep a Changelog file, up to the next `## [` heading. The heading is `## [VERSION]` alone or followed by ` - <date>`; the version matches exactly. A missing heading or an empty body prints the reason to stderr and exits 1. |

## The release subcommands

They run `git` and `gh` in the current repository. Every command they run writes
its own stdout to stderr, so a subcommand's stdout carries only the lines below.
A command that fails ends the subcommand with that command's exit status.

`release-state TAG` reads the release with
`gh release view TAG --json isDraft --jq .isDraft` (a failure means there is no
release) and whether `git ls-remote --tags origin refs/tags/TAG` prints
anything. It prints `tag=TAG`, `should-release=`, `draft=` and `tagged=`, in
that order, each `true` or `false`. A published release gives
`should-release=false`, and `Release TAG already published; nothing to do.` goes
to stderr.

`release-source TAG`, if the tag exists on `origin`, runs
`git fetch --no-tags origin refs/tags/TAG:refs/tags/TAG` and
`git checkout --detach TAG`. It prints `sha=<git rev-parse HEAD>`. A tag without
a published release is a release that failed after tagging, and it rebuilds from
that tag, because `HEAD` would ship a different commit under the same version.

`release-publish TAG --title TITLE --target SHA FILE...` reads the state as
`release-state` does. A published release writes the same message to stderr and
exits 0. A draft is deleted first (`gh release delete TAG --yes`). Then it runs
`gh release create TAG FILE... --verify-tag --title TITLE --generate-notes` when
the tag exists, and
`gh release create TAG FILE... --target SHA --title TITLE --generate-notes`
otherwise. With `--notes-file FILE`, `--generate-notes` becomes
`--notes-file FILE --latest=false`. The release leaves out the FILEs ending in
`.publish.attestation`. It prints nothing. The release, not the tag, is the
record of what shipped, and `gh release create` makes the tag at `--target`.

With `--upload pypi`, a release that is not yet published first uploads the
`*.whl`, `*.tar.gz` and `*.publish.attestation` among the FILEs with
`uv publish --trusted-publishing always`, unless
`https://pypi.org/pypi/<name>/<version>/json` answers 200; `<name>` and
`<version>` come from `TAG` (`<name>-v<version>`). A failed upload ends the
subcommand before any `gh` command. With `--upload testpypi`, it does only the
upload, to `https://test.pypi.org/legacy/` and checked against test.pypi.org: no
release state is read and no `gh` command runs.

## What it discovers

- **Packages:** the members of the root `[tool.uv.workspace]`, including
  `exclude`. No name prefix is assumed.
- **Internal requirements:** workspace members named in a package's
  dependencies, optional dependencies and dependency groups. Release order and
  `releasable` leave dependency groups out; a cycle among the rest is an
  error.
- **Import name:** `[tool.uv.build-backend].module-name`, used for `--cov`, the
  verify-release import and the smoke imports.
- **Optional jobs:** `sonar` runs only if `sonar-project.properties` exists;
  `docs` only if `mkdocs.yml` exists.

An empty, invalid or non-ancestor `BASE` selects every package. A change under
`docs/` selects no package; any other change outside the members selects every
package.

## What a repository declares

| Table | Where | Holds |
| -- | -- | -- |
| `[tool.workspace-ci]` | root | `pytest-args` for package test runs. |
| `[tool.workspace-ci.suites]` | root | A named workspace-wide pytest run per key, each its own job. |
| `[tool.workspace-ci.integration.<service>]` | package | One service container the package's tests need: `image` (required), `command` (arguments after the image), `ports` (`host:container`), `volumes` (`src:dst[:ro]`, `src` relative to the package directory), `health-cmd`, `health-wait` (seconds to wait for health, default 120, at least 1), `env` (set in the container), `expose` (set in the environment of the tests) and `pytest-args` (added after the root ones for the package's integration run). The `integration` check starts each declared service, waits for its health, runs the package's tests and removes the containers. The older `[tool.workspace-ci.postgres]` and `[tool.workspace-ci.redis]` tables are refused. |
| `[tool.workspace-ci.smoke]` | package | Optional: a package without it is still smoke-tested with no extra, importing its own module. `modules` imported for every smoke run, an optional `setup` script run first, and `extras`: one smoke job per extra with its own modules. |
| `[tool.workspace-ci]` | package | `adapters`: the names of the package's adapter modules. Each must be a module or subpackage of the package and have an extra of the same name; `adapters` checks it. |

## The `plan` outputs

Generated CI workflows read the `plan` outputs. A removed or renamed key, or a
changed row shape, is a breaking change and takes a major version bump. A new
key or a new row field is a minor change.

Each output is one `key=value` line. A string is written as is; a list or a
boolean is written as JSON. "Selected" packages are the packages the change
affects plus every package that depends on one, in release order. "Every" means
every workspace member, whatever the change.

<!-- plan-outputs:start -->

| Key | Value | Scope |
| -- | -- | -- |
| `release-order` | List of package names. | Selected |
| `packages` | List of rows `{name, dir}`. | Selected |
| `integration` | List of rows `{name, dir, services, marker}`, one per package that declares a service. `services` is the list of service names; `marker` is the file name a passing check leaves for `releasable`. | Selected |
| `smoke` | List of rows `{name, extra, marker}`, one per smoke check. `extra` is empty for the run with no extra. `marker` is the file name a passing check leaves for `releasable`. | Selected |
| `suites` | List of rows `{name, args}`, one per `[tool.workspace-ci.suites]` key. `args` is a shell-quoted string. | Every suite |
| `pytest-args` | Shell-quoted string of the root `pytest-args`; empty if none. | Workspace |
| `docs` | `true` if `mkdocs.yml` exists at the root, else `false`. | Workspace |

<!-- plan-outputs:end -->

`docs` reports only that the file exists; it is not scoped to the change.
