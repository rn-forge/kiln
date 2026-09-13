# Phase B — codex review

> Kept verbatim. The only change is that the file citations, which pointed at
> absolute paths on the reviewer's machine, are rendered as plain references
> rather than as links — the wording is untouched. What was done about each item
> is in [context §7](../context.md), which carries the plan's §0.6.

1. **[P1] Released packages lose the Git dependency source.** Both members
   declare `rn-forge-commons>=0.2.2`, but its Git location exists only in the
   workspace’s `tool.uv.sources`. Published metadata does not preserve that
   override. Under the plan’s GitHub-only distribution policy, consumers
   cannot resolve commons without additional configuration. Define a
   consumer-installable dependency source and verify each wheel in a clean
   environment outside the workspace. Package declaration
   (`tests/fixtures/golden/python-lib/packages/golden-alpha/pyproject.toml:9`)
   ·
   [uv guidance](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-sources)

1. **[P1] Failed publication cannot recover on rerun.** CI pushes the tag before
   creating the release and uploading assets. If publication fails, subsequent
   runs see the tag and permanently skip publication. Treat a completed
   release with expected assets as success; resume incomplete releases from
   the original tagged commit. This requires refining the plan’s D22 rule.
   Release workflow
   (`tests/fixtures/golden/python-lib/.github/workflows/ci.yml:127`)

1. **[P1] Sonar’s quality gate does not gate releases.** `release` depends on
   successful scan submission, with no quality-gate wait or check. Publication
   can proceed while Sonar subsequently reports failure. Add an explicit gate
   check before release. Scan step
   (`tests/fixtures/golden/python-lib/.github/workflows/ci.yml:88`) ·
   [Sonar guidance](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/ci-integration/overview)

1. **[P2] CI can silently update the lockfile.** Setup uses unrestricted
   `uv sync`; subsequent commands also permit automatic resolution. A stale
   committed lock can therefore pass CI using an uncommitted replacement.
   Enforce locked resolution in CI, including setup, while retaining the
   `task` entrypoint. Setup task
   (`tests/fixtures/golden/python-lib/tasks/workspace.yml:19`) ·
   [uv CI guidance](https://docs.astral.sh/uv/guides/integration/github/)

1. **[P2] Typed libraries lack `py.typed`.** Neither package contains the marker
   required to advertise bundled typing information. Strict checking inside
   the repository does not establish typing support for installed consumers.
   Add the marker to each import package and verify its inclusion in wheels
   and sdists. Package source
   (`tests/fixtures/golden/python-lib/packages/golden-alpha/src/golden_alpha/__init__.py:1`)
   ·
   [Python typing specification](https://typing.python.org/en/latest/spec/distributing.html#packaging-type-information)

1. **[P2] Coverage uses different test configuration from validation.** Normal
   tests run inside each package; coverage runs once from the workspace root,
   bypassing member pytest settings. With default import mode, common
   filenames such as two `test_utils.py` files also collide. Run coverage per
   package and combine results; use `--import-mode=importlib` consistently.
   Test tasks (`tests/fixtures/golden/python-lib/tasks/quality.yml:94`) ·
   [pytest guidance](https://docs.pytest.org/en/stable/explanation/goodpractices.html)

1. **[P2] The lint gate leaves avoidable blind spots.** It never checks
   formatting, and both packages disable **all** Ruff rules for tests. Add
   `ruff format --check` to validation and replace blanket test exclusions
   with specific exceptions. Lint task
   (`tests/fixtures/golden/python-lib/tasks/quality.yml:18`) · Test exclusion
   (`tests/fixtures/golden/python-lib/packages/golden-alpha/pyproject.toml:29`)
   · [Ruff guidance](https://docs.astral.sh/ruff/formatter/)

1. **[P2] Fork pull requests run a scan without its required secret.** Sonar
   runs unconditionally, but GitHub withholds `SONAR_TOKEN` from fork
   workflows. Skip the authenticated scan for forks while keeping validation
   mandatory. Sonar job
   (`tests/fixtures/golden/python-lib/.github/workflows/ci.yml:59`) ·
   [GitHub secret rules](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)

Validation: `UV_OFFLINE=true UV_NO_SYNC=true task validate` passed using the
existing environment: four tests, lint, strict type checks, and docs build.
Publication and clean consumer installation were reviewed statically, not
executed.
