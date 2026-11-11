# Cutting a repository over to kiln

The one-time move of a repository with a pre-kiln lineage onto kiln, by the
overlay of [ADR-0019](../adr/ADR-0019.md): build a reference repository with
`kiln new`, bring its files onto a branch of the existing repository, review one
diff. The old `init` command is gone. It holds the steps and the format of the
absorb/extend/drop table; each repository's verdict table lives in its own specs
and links here. A repository with no pre-kiln lineage is rebuilt with `kiln new`
([creating a repository](creating-a-repo.md)).

## Steps

1. **Branch.** In the existing repository, from its default branch with a clean
   worktree: `git switch -c feature/kiln-cutover`. History and tags stay.

1. **Build the reference.** Outside the repository, run
   `kiln new <dir> --archetype <archetype> --docs mkdocs --owner <owner> --config <file> --yes`
   from the `[kiln] ref` the cutover targets. The config file, and any
   `kiln generate package` or generator runs, are listed in the repository's
   own cutover story (pykit S16.3.1, ngkit S17.2.1). Run `task setup` and
   `task validate` in the reference; it must pass before anything is brought
   over.

1. **Bring the files over.** Take the inventory: from the reference, run
   `kiln diff --old <old repo>`
   ([S16.9.11](../specs/epics/E16-init-adopts-by-overwrite/F16.9-overlay-cutover-findings.md#s16911-kiln-diff-old-old-repo-the-cutovers-inventory)).
   It lists every file with its class (`managed`, `block`, `seeded`,
   `scaffolded`, `old-only`) and whether the bytes match; the `old-only` rows
   are the deletions list. Then, by class: copy each `managed` file
   byte-for-byte (`cp`); replace each `block` file's fenced region with the
   reference's, markers included, leaving the repository's text outside;
   `AGENTS.md` takes the reference's block, and a fenced kiln region left in
   `CLAUDE.md` is deleted; add each `seeded` file the repository lacks and
   keep the repository's version of one it has; keep every `scaffolded` file
   the repository has; copy `.rn-forge/kiln/config.toml` and `state.json` last.
   `mkdocs.yml` is copied whole like any managed file; its `nav` is a derived
   region, so run `task docs:generate` after the copy and the repository's own
   pages fill it (about 150 lines of the first diff are this, and no verdict
   row). Source, tests and docs content are never copied. Every
   repository-owned or seeded difference the repository keeps is a step in its
   cutover story, not a rule here.

1. **Read the diff file by file.** `git diff` and `git status`; every file
   deleted or replaced is a row. Delete the old workflows now
   (`git rm .github/workflows/<old>.yml`): the reference's `ci.yml` and an old
   workflow share a concurrency group, and a ruleset requires the context
   `ci-ok`.

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

1. **Rebuild the reference and re-run the overlay.** Bump `[kiln] ref`, rebuild
   the reference from step 2 and repeat step 3; the diff of the repeat is only
   the absorbed behaviour. A difference a repository needs inside a managed
   file or block is an absorb or extend row, never an edit of the copy.

1. **Reconcile and gate.** Do what the repository's cutover story lists for the
   files kiln has a block in (reconcile `CLAUDE.md`'s and `AGENTS.md`'s blocks
   with the repository's text, rewrite the commands in its docs to `task`
   verbs); then `task validate` and `KILN_DOCTOR_FULL=1 task validate` exit 0,
   and `task kiln:apply` changes nothing.

    For a `node-lib` only, also run `pnpm exec nx migrate <NX_VERSION>` (the
    version in `src/rn_forge/kiln/modules/node/angular.py`) and its migrations,
    then `pnpm audit --prod --audit-level moderate`; add pnpm overrides only
    for what the migrate leaves vulnerable. `kiln doctor`'s `nx-version` check
    fails while `nx` is behind.

    Also make sure `prettier` is a dev dependency
    (`pnpm add -D prettier@~3.9.10`), then run `task format`; commit the
    formatting separately.

1. **Merge** when no absorb row is open. The cutover pull request deletes the
   old CI workflow (step 4 did) in the same change that adds `ci.yml`: both
   share the concurrency group and a ruleset requires the context `ci-ok`, so
   a follow-up would leave two.

## Examples

- kiln's own table, for its `mkdocs.yml`:
  [S16.2.1](../specs/epics/E16-init-adopts-by-overwrite/F16.2-kiln-owns-mkdocs.md#s1621-inventory-what-the-three-mkdocsyml-files-carry).
- pykit's rehearsal, items 1–15:
  [the cutover findings](../specs/ideas/pykit-cutover-findings.md#items).
