# Adopting kiln in an existing repository

Bring an existing repository under kiln without rebuilding it: choose the route,
run `kiln init` in place, and make the judgement calls that kiln's code cannot,
reconciling instructions, specs and the gate.

`kiln init` settles everything with one right answer: it overwrites the files it
owns (after copying each to a backup), fences an unfenced `.importlinter`, adds
the task tools the repository lacks, and ends by running `task setup`, the
formatter and the docs generator, so the tree it leaves is already formatted. It
reports what it cannot settle. This prompt is the rest, the judgement. It prints
guidance and installs nothing, and it is written from in-place adoptions (run 1:
pykit, a `python-lib` workspace; run 4: ngkit, a `node-lib` workspace). Facts
from those runs are examples, not rules.

## 1. Choose the route

- **In place** (`kiln init`, this prompt) when the repository already has the
  archetype's shape: for a `python-lib`, a `src/` layout or a `packages/`
  workspace, a `pyproject.toml`, tests, and a docs tree that is close to
  kiln's areas; for a `node-lib`, a pnpm workspace with `nx.json`, projects
  under `libs/` or `apps/`, and a docs tree that is close to kiln's areas.
- **Rebuild and port** (`kiln new`, then carry the specs and decisions over with
  `kiln prompt --name port-docs`) when it does not: a different layout, a
  different toolchain, or docs that share nothing with the standard. The
  rebuild route in this prompt is not yet written.

If you cannot tell, run section 3's dry run: a plan with a handful of conflicts
is an in-place adoption; a plan that replaces most of the repository is a
rebuild.

## 2. Prepare

- Work on a branch, and start from a clean tree: `init --yes` refuses a dirty
  one (`init.dirty-tree`) so that the review is kiln's change alone. Commit or
  `git stash -u`.

- Use kiln from a checkout when it is not released:
  `uv run --project <kiln> kiln …`. Run it from the repository being adopted.

- Write a config file for `--config`, outside the repository or ignored, with
  the archetype's keys (`docs/reference/standard-repo.md`, section 9). A
  library workspace lists its members, which `init` (unlike `new`) accepts:

    ```toml
    [archetype.python-lib]
    packages = ["packages/one", "packages/two"]   # nav order is this order
    modules = { "packages/one" = "rn_forge.one" } # only where the import module is not the path name
    import_contracts = "own"                       # keep the repository's own import contracts
    ```

    Each package must be an existing directory with a `pyproject.toml`
    (`init.package-missing` otherwise). Use `import_contracts = "own"` when the
    repository already has `.importlinter` contracts worth keeping; kiln then
    renders only the root packages (run 1: pykit's layering contracts).

    `init` records the file as `[source]`, and `kiln config-update` re-reads it
    from there. For a one-off file kept outside the repository or git-ignored,
    delete the `[source]` table from `.rn-forge/kiln/config.toml` after `init`
    (run 3: pykit's `dist/pykit-kiln.toml`, which `task clean` also deletes).

    A `node-lib` has no `[archetype.node-lib]` table; its file carries the
    repository's own CI and task declarations (run 4: ngkit):

    ```toml
    [ci]
    sonar_exclusions = ["apps/demo/**"]         # paths the repository's own Sonar file excluded
    sonar_coverage_exclusions = ["libs/*/src/testing/**"]  # counted, but not expected to have coverage

    [tasks.extra_refs]
    lint = ["self:check:tokens"]                # repository-owned checks a root verb also runs
    ```

    The archetype's release default is `nx-dispatch`, so `[ci] release` is left
    unset.

## 3. Preview and sort the plan

Run the preview, which writes nothing. `<archetype>` is `python-lib` or
`node-lib`:

```bash
uv run --project <kiln> kiln init --archetype <archetype> --docs mkdocs --config <file> --dry-run
```

The plan lists creates, conflicts (files `init` overwrites) and block inserts.
Sort each conflict by how kiln owns the file:

- **Kiln's whole file replaces yours** (a conflict). Read yours first for
  anything worth keeping. What is worth keeping goes to a repository-owned
  place (a seeded file, a guide, a runbook, the README), not into the
  generated file.
- **A block.** Kiln owns a fenced block; your content stays outside it.
- **Seeded.** Kiln replaces a seeded page that holds nothing beyond the seed
  text, and keeps one that holds content.

The plan lists each path and its kind, not its content. The list made here is of
*which* files to read: for each conflict, read the repository's file now, and
note what it holds that kiln's will not. The originals are archived, but a list
made now is the one you will check against at review.

## 4. Apply

```bash
uv run --project <kiln> kiln init --archetype <archetype> --docs mkdocs --config <file> --yes
```

The archetype is the one section 3 used, `python-lib` or `node-lib`. `init`
refuses a dirty worktree, and copies every file it overwrites to
`.rn-forge/kiln/backups/<UTC timestamp>/` (gitignored) first. Do not re-run it;
it refuses a repository that is already under kiln.

The tree was clean, so `git diff` and `git status` now show every file kiln
replaced, inserted into or created, against the repository's own version, and
the originals are also under the backups. Finish the carry-over list from that
diff before section 5. Commit `init`'s change on its own.

`init` ends by running the checks, so it may exit non-zero on findings in files
you have not reconciled yet. Read them in section 7.

## 5. Reconcile the files kiln inserted a block into

`CLAUDE.md` (and any other file that now holds a kiln block) has two authors.
Read kiln's block and the repository's text together:

- Delete from the repository's part what the block now states.
- Where they contradict, kiln's block wins on structure: the `task` entrypoint,
  generated files, the docs rules. Correct the repository's text (run 1:
  pykit's `CLAUDE.md` pointed at `uv run` commands that the block forbids).
- Check the guides and runbooks the instructions link to for the same
  contradictions, and fix them on the page.
- A document contradicts kiln's block when it tells a developer to run, in this
  repository, a tool that a root `task` verb wraps (`uv run pytest` is
  `task test`, `uv run ruff check` is `task lint`, `uv sync` is `task setup`,
  `mkdocs build` is `task docs:build`). In a `node-lib`, `pnpm exec nx lint`
  or `nx run-many -t lint` is `task lint`, `nx test` is `task test`,
  `nx build` is `task build`, and `pnpm install` is `task setup`. Rewrite
  those to the verb. Leave commands with no verb (`uv add`, `uv lock`,
  `uv build`, `pnpm add`), and commands for a consumer outside the repository
  (a README's `uvx …` install line). No check finds these: grep the docs,
  `README.md` and `CLAUDE.md` for `uv run`, `pytest`, `ruff`, `pyright`,
  `mkdocs` (run 2: pykit's `development.md`, `README.md`,
  `releasing-packages.md`) and, in a `node-lib`, `pnpm exec`, `pnpm dlx`,
  `npx` and a bare `nx` command.
- In a node archetype kiln writes the `.prettierignore` block, which already
  lists `*.md` because mdformat formats Markdown in every archetype (run 4:
  ngkit); the repository keeps its own lines above it.
- Specs and decisions that do not follow kiln's work model are converted by
  `kiln prompt --name port-docs`'s rules, not here.

## 6. Make the gate runnable

`task validate` runs kiln's checks through the kiln that `[kiln] ref` in
`.rn-forge/kiln/config.toml` pins. `kiln init` writes that ref; confirm it is
there. Before kiln's first release the ref is a branch, and `kiln.pin-mismatch`
only starts checking once it is a `v<version>` tag. kiln is not a dependency:
the tasks run it with `uvx`, in its own environment, so the repository's lock
and `pyproject.toml` do not change for it. If the repository already lists
`rn-forge-kiln` in a dependency group, or carries an `override-dependencies`
entry only so kiln resolves, remove them (`deps.kiln-in-lock`).

## 7. Run the gate and sort what is left

```bash
task validate
KILN_DOCTOR_FULL=1 task validate
```

Sort each finding by who owns the file:

- **A file kiln owns** (it carries a provenance header or sits in a kiln block):
  the finding is kiln's. Report it; do not edit the file, and do not hide it
  by editing `.rn-forge/kiln/state.json`.
- **The repository's own file:** the finding is the repository's. Fix it.
- **A hand-written CI workflow** is retired when the generated one runs its jobs
  (run 1: pykit's `main.yml` failed `ci-entrypoint` with direct `uv` steps,
  and retires with the generated workflows).

`init`'s closing check, like a plain `kiln doctor`, runs only the ownership
checks; `task lint` also runs `rn-forge-deps`, `docs-structure` and `docs-site`,
so read its findings too.

Done when both commands exit `0`.

## 8. Review

Read one `git diff`, file by file, before the first commit. Check it against
section 3's carry-over list and `.rn-forge/kiln/backups/`: nothing the
repository relied on was lost, and nothing is said twice. Report to the owner
what was carried over, what was deleted because kiln's block now states it,
which findings were kiln's, and the final output of both commands in section 7.

After `init`, follow `docs/runbooks/cutover.md`: it reviews the diff and records
what the repository loses.
