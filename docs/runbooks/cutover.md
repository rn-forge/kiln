# Cutting a repository over to kiln

The one-time move of a repository with a pre-kiln lineage onto kiln, by the
overlay of [ADR-0019](../adr/ADR-0019.md): build a reference repository with
`kiln new`, bring its files onto a branch of the existing repository, review one
diff. The old `init` command is gone. This page holds the steps and the format
of the absorb/extend/drop table. Everything specific to a repository lives in
its own cutover story and links here: the `kiln new` config, every command, the
nuances it keeps, its verdict table and the record of each run. The story is
enough to rerun the cutover from scratch. A repository with no pre-kiln lineage
is rebuilt with `kiln new` ([creating a repository](creating-a-repo.md)).

## Steps

1. **Build the reference.** Outside the repository, run
   `kiln new <dir> --archetype <archetype> --docs mkdocs --owner <owner> --config <file> --yes`
   from the `[kiln] ref` the cutover targets. The config file's content, and
   any `kiln generate package` or generator runs, are written out in the
   repository's own cutover story (pykit S16.3.1, ngkit S17.2.1); the file
   passed to `--config` is a copy of that block. Run `task setup` and
   `task validate` in the reference; it must pass before anything is brought
   over.

1. **Format first.** Once, before the first overlay, so that the overlay's diff
   carries no reformatting of the repository's own files. In the existing
   repository, from its default branch (or the release branch the cutover
   merges to) with a clean worktree:

    1. `git switch -c feature/kiln-format`.
    1. Bring the reference's files over as step 4 says. This is temporary: it
       gives the repository kiln's formatter configuration (`.editorconfig`,
       `.mdformat.toml`, `.taplo.toml`, `.yamlfmt.yaml`) and its `task format`.
       Save the overlay's path list: `git status --porcelain`.
    1. `task setup`, then `task format`.
    1. Keep only the reformatting of files the repository owns: the Markdown,
       TOML and YAML files that changed and are not on the overlay's path list.
       Write their diff to a patch outside the repository
       (`git diff -- <those paths>`), throw the overlay away
       (`git reset --hard`, `git clean -fd`), apply the patch, and commit it
       alone.
    1. The commit changes only `*.md`, `*.toml`, `*.yml` and `*.yaml` files, and
       only their layout. Run the repository's existing gate on it. If it
       passes, it can merge ahead of the cutover and shrink the cutover's
       review. If the old gate's own formatter disagrees, it stays the first
       commit of the cutover branch.

    Redo this step only when kiln's formatter configuration or the formatter pins
    in its lock change; a rerun of the overlay (step 8) starts from the same
    commit.

1. **Branch.** `git switch -c feature/kiln-cutover feature/kiln-format`. History
   and tags stay.

1. **Bring the files over.** Take the inventory: from the reference, run
   `kiln diff --old <old repo>`
   ([S16.9.11](../specs/epics/E16-init-adopts-by-overwrite/F16.9-overlay-cutover-findings.md#s16911-kiln-diff-old-old-repo-the-cutovers-inventory)).
   It lists every file with its class (`managed`, `block`, `seeded`,
   `scaffolded`, `old-only`) and whether the bytes match; the `old-only` rows
   are the deletions list. Then, by class: copy each `managed` file
   byte-for-byte (`cp`); replace each `block` file's fenced region with the
   reference's, markers included, leaving the repository's text outside;
   `AGENTS.md` takes the reference's block, and a fenced kiln region left in
   `CLAUDE.md` is deleted; add each `seeded` or `scaffolded` file the
   repository lacks. A `seeded` or `scaffolded` configuration file the
   repository has (`pyproject.toml`, `nx.json`, `package.json`,
   `tsconfig.base.json`, `pnpm-workspace.yaml`, `eslint.config.mjs`,
   `.mdformat.toml` and the like) also starts from the reference's copy: copy
   it over, then re-apply the repository's own changes to it, each a named
   hand edit in its cutover story with the reason it stays. A change with no
   reason is dropped, and one every repository would want is an absorb row.
   The file's diff against the reference is then only the repository's edits,
   as if kiln had seeded it and the repository had edited it since. List them
   with `diff -u <reference>/<path> <old repo>/<path>` for each row
   `kiln diff --old` marks as differing; build the reference with the
   repository's toolchain versions (its Nx and Angular, its Python) and its
   generator choices, or version noise hides the edits. A lockfile is never
   copied: the repository's stays, and `task setup` moves only what the merged
   manifest changed. Copy `.rn-forge/kiln/config.toml` and `state.json` last.
   `mkdocs.yml` is copied whole like any managed file; its `nav` is a derived
   region, so run `task docs:generate` after the copy and the repository's own
   pages fill it (about 150 lines of the first diff are this, and no verdict
   row). Source, tests and docs content are never copied. Every hand edit and
   every other difference the repository keeps is a step in its cutover story,
   not a rule here.

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
   the reference from step 1, reset the cutover branch to the formatted base
   (`git switch -C feature/kiln-cutover feature/kiln-format`) and repeat from
   step 4. The diff of the repeat is only the absorbed behaviour. A difference
   a repository needs inside a managed file or block is an absorb or extend
   row, never an edit of the copy. Each run is recorded in the repository's
   cutover story: the date, the kiln commit, the reference commit, and the
   exit status of the gate.

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
    (`pnpm add -D prettier@~3.9.10`), then run `task format`.

1. **Commit in groups, docs first.** Record the branch's commit before step 4
   (`git rev-parse HEAD`) and diff against it, never against `HEAD~N`. Commit
   by explicit path, never `git add -A`, in this order, so each diff reviews
   alone: docs (Markdown under `docs/`, `mkdocs.yml`, the docs config kiln
   brings, and the wrapping `task format` gave them), the biggest mechanical
   difference; kiln's managed files and config; deletions; manifests,
   lockfiles and source; formatting of other files last. The repository's
   cutover story lists the paths of each group. Only the last commit has to
   pass `task validate`; the others are for review. A rerun stops before this
   step.

1. **Merge** when no absorb row is open. The cutover pull request deletes the
   old CI workflow (step 5 did) in the same change that adds `ci.yml`: both
   share the concurrency group and a ruleset requires the context `ci-ok`, so
   a follow-up would leave two.

## Examples

- kiln's own table, for its `mkdocs.yml`:
  [S16.2.1](../specs/epics/E16-init-adopts-by-overwrite/F16.2-kiln-owns-mkdocs.md#s1621-inventory-what-the-three-mkdocsyml-files-carry).
- pykit's verdict tables and runs:
  [F16.3](https://github.com/rn-forge/pykit/blob/main/docs/specs/epics/E16-kiln-adoption/F16.3-cutover.md).
- ngkit's verdict tables and runs:
  [F17.2](https://github.com/rn-forge/ngkit/blob/main/docs/specs/epics/E17-kiln-adoption/F17.2-cutover.md).
