# Cutting a repository over to kiln

The one-time move of a repository with a pre-kiln lineage onto kiln. It holds
the steps and the format of the absorb/extend/drop table; each repository's
verdict table lives in its own specs and links here. A repository too far from
its archetype's shape for `kiln init` takes the rebuild route instead
([F16.5](../specs/epics/E16-init-adopts-by-overwrite/F16.5-rebuild-and-port.md)).

For a repository with no lineage worth keeping, use
[adopting an existing repo](adopting-a-repo.md); to start a new one,
[creating a repository](creating-a-repo.md).

## Steps

1. **Branch.** From the repository's default branch, with a clean worktree.
   `init` refuses a dirty tree.

1. **Run kiln init.** `kiln init --archetype <archetype> --docs mkdocs --yes`,
   with `kiln` run from the `[kiln] ref` the cutover targets. It overwrites
   kiln-shaped files and backs each up under
   `.rn-forge/kiln/backups/<stamp>/`; it then runs `task setup`, `task format`
   and `task docs:generate`. There is no `--force`. Run it from a checkout
   whose `origin` is the repository: the repository name comes from the
   `origin` remote's name, not from the directory (then the root
   `pyproject.toml`'s `[project].name`, then the directory). The owner comes
   from a GitHub `origin` too; without one, pass `--owner <owner>` (it is
   `[repository] owner`, which every URL kiln writes is built from). A
   `python-lib` passes `--config` with `packages`, `modules`,
   `import_contracts` and `[ci] release`; pykit's is in
   [its cutover story](https://github.com/rn-forge/pykit/blob/main/docs/specs/epics/E16-kiln-adoption/F16.3-cutover.md).
   `init` exits 1 while the old workflows are present, because its closing
   `kiln doctor` checks them; see step 3.

1. **Read the diff file by file.** `git diff` and `git status`; every file
   `init` deleted or replaced is a row. The originals are in the backups.
   Delete the old workflows now (`git rm .github/workflows/<old>.yml`), not
   only at merge: `init`'s closing `kiln doctor` fails on them and exits 1,
   and the rewritten files are still on disk. Do it right after this read and
   before step 6.

1. **Record a verdict** for each behaviour the repository loses, in a table in
   the repository's own spec with this header:

    | File | What is lost | Verdict | Where it went |
    | -- | -- | -- | -- |

    The verdict is one of:

    - **absorb**: a kiln story, so every repository gets it.
    - **extend**: keep it through an extension point: `[ci.checks]`,
      `[[ci.jobs]]`, `[ci.hooks]`, `_areas.yml` or `[docs.mkdocs]`.
    - **drop**: cite the decision.

    Known rows for pykit: its `[tool.workspace-ci.postgres]` and
    `[tool.workspace-ci.redis]` tables become
    `[tool.workspace-ci.integration.<name>]` service declarations
    ([S15.8.2](../specs/epics/E15-ci-standard/F15.8-one-workflow-contract.md#s1582-the-integration-stage-services-as-data));
    kiln does not read the old keys. Its `broker-profile.yml` row is absorb:
    an `integration` service of `rn-forge-auth`
    ([S16.6.5](../specs/epics/E16-init-adopts-by-overwrite/F16.6-cutover-rehearsal-findings.md#s1665-integration-services-cover-pykits-broker-profile-and-broker-profileyml-retires)).

1. **Land the absorb stories** in kiln.

1. **Bump `[kiln] ref` and run kiln apply.** `init` wrote `state.json` in step
   2, so the repository is under kiln and `init` refuses it with "use
   `kiln apply`". `kiln apply`, run from the new ref, takes the absorbed
   behaviour, and its diff is only that behaviour, plus the new ref where the
   task files render it. To rehearse `init` itself again, start over from step
   1 in a fresh worktree of the default branch.

    For a `node-lib`, also run `pnpm exec nx migrate <NX_VERSION>` (the version
    in `src/rn_forge/kiln/modules/node/angular.py`) and its migrations, then
    `pnpm audit --prod --audit-level moderate`; add pnpm overrides only for
    what the migrate leaves vulnerable. `kiln doctor`'s `nx-version` check
    fails while `nx` is behind.

    Also make sure `prettier` is a dev dependency
    (`pnpm add -D prettier@~3.9.10`), then run `task format`; commit the
    formatting separately.

1. **Merge** when no absorb row is open. The cutover pull request deletes the
   old CI workflow (step 3 did) in the same change that adds `ci.yml`: both
   share the concurrency group and a ruleset requires the context `ci-ok`, so
   a follow-up would leave two.

## Examples

- kiln's own table, for its `mkdocs.yml`:
  [S16.2.1](../specs/epics/E16-init-adopts-by-overwrite/F16.2-kiln-owns-mkdocs.md#s1621-inventory-what-the-three-mkdocsyml-files-carry).
- pykit's rehearsal, items 1–15:
  [the cutover findings](../specs/ideas/pykit-cutover-findings.md#items).
