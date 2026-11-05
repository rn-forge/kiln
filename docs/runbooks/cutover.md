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
   and `task docs:generate`. There is no `--force`.

1. **Read the diff file by file.** `git diff` and `git status`; every file
   `init` deleted or replaced is a row. The originals are in the backups.

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
    kiln does not read the old keys.

1. **Land the absorb stories** in kiln.

1. **Bump `[kiln] ref` and run kiln apply.** `init` wrote `state.json` in step
   2, so the repository is under kiln and `init` refuses it with "use
   `kiln apply`". `kiln apply`, run from the new ref, takes the absorbed
   behaviour, and its diff is only that behaviour, plus the new ref where the
   task files render it. To rehearse `init` itself again, start over from step
   1 in a fresh worktree of the default branch.

1. **Merge** when no absorb row is open. The cutover pull request deletes the
   old CI workflow in the same change that adds `ci.yml`: both share the
   concurrency group and a ruleset requires the context `ci-ok`, so a
   follow-up would leave two.
