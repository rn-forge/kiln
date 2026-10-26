# Adopting kiln in an existing repository

Bring an existing repository under kiln without rebuilding it: choose the route,
run `kiln init` in place, and make the judgement calls that kiln's code cannot,
reconciling instructions, specs and the gate.

`kiln init` settles everything every repository hits and that has one right
answer: a missing file is created, a duplicate `.gitignore` line is dropped, an
unfenced `.importlinter` is fenced, the derived-nav markers are placed. It
reports what it cannot settle. This prompt is the rest, the judgement. It prints
guidance and installs nothing, and it is written from the first in-place
adoption (run 1: pykit, a `python-lib` workspace). Facts from that run are
examples, not rules.

## 1. Choose the route

- **In place** (`kiln init`, this prompt) when the repository already has the
  archetype's shape: `src/` layout or a `packages/` workspace, a
  `pyproject.toml`, tests, and a docs tree that is close to kiln's areas.
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

## 3. Preview and sort the plan

Run the preview, which writes nothing:

```bash
uv run --project <kiln> kiln init --archetype python-lib --docs mkdocs --config <file> --dry-run
```

The plan lists creates, conflicts and block inserts. Sort each conflict by how
kiln owns the file:

- **Kiln's whole file replaces yours.** Read yours first for anything worth
  keeping. What is worth keeping goes to a repository-owned place (a seeded
  file, a guide, a runbook, the README), not into the generated file.
- **A block.** Kiln owns a fenced block; your content stays outside it.
- **Seeded.** Kiln writes it once; yours is kept as is.

The plan lists each path and its kind, not its content. The list made here is of
*which* files to read: for each conflict, read the repository's file now, and
note what it holds that kiln's will not. The originals are archived, but a list
made now is the one you will check against at review.

## 4. Apply

```bash
uv run --project <kiln> kiln init --archetype python-lib --docs mkdocs --config <file> --yes --force
```

`--force` approves every conflict. Before it overwrites, kiln copies each
conflicting file, and every file it restructures, to
`.rn-forge/kiln/backups/<UTC timestamp>/` (gitignored). It also restructures
three things for you:

- An unfenced `.importlinter` is fenced: kiln's `[importlinter]` root section
  goes inside the markers and your contracts stay below them.
- Lines in your `.gitignore` that kiln's block already holds are dropped (unless
  a `!` negation makes order matter); the block is appended.
- A `mkdocs.yml` without the derived-nav markers is refused without `--force`
  (`init.nav-unmarked`); with it, kiln places the markers around the nav's
  entries and `docs-generate` replaces them.

The tree was clean, so `git diff` and `git status` now show every file kiln
replaced, inserted into or created, against the repository's own version, and
the originals are also under `.rn-forge/kiln/backups/`. Finish the carry-over
list from that diff before section 5.

`init` ends by running the checks, so it may exit non-zero on findings in files
you have not reconciled yet. Read them in section 9; do not re-run `init`.

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
  `mkdocs build` is `task docs:build`). Rewrite those to the verb. Leave
  commands with no verb (`uv add`, `uv lock`, `uv build`), and commands for a
  consumer outside the repository (a README's `uvx …` install line). No check
  finds these: grep the docs, `README.md` and `CLAUDE.md` for `uv run`,
  `pytest`, `ruff`, `pyright`, `mkdocs` (run 2: pykit's `development.md`,
  `README.md`, `releasing-packages.md`).

## 6. Seeded files that kiln's checks need in a given shape

`init` keeps a seeded file as it found it, so a stale one survives and a check
fails or, worse, stays silent.

- `docs/_areas.yml` in a library needs an area with `nav: include` for the
  package sites (conventionally `packages`). Without it the derived nav drops
  every package site; `docs.packages-area-missing` reports it. Put the area
  where you want Packages in the nav (run 1: first, so Packages follows Home).
- The nav lists packages in the order of `packages` in
  `.rn-forge/kiln/config.toml`; reorder that list, not the nav.
- Page titles in the nav come from each page's H1. If a title reads wrong, fix
  the H1.

## 7. Convert the specs to kiln's work model

kiln keeps every repository's specs in one structure, so a reader never learns a
second one. Convert by `kiln prompt --name port-docs`'s rules (content moves
verbatim, nothing is dropped silently), and in particular:

- `### S…` story headings become `## S…`, and a `## Stories` heading over them
  goes: kiln derives a feature's stories table from `## S…` headings.
- The board's and each release's Scope markers become kiln's `BEGIN derived …`
  fences, which `task docs:generate` writes.
- An epic's hand-written table of the features that have files goes. First check
  that each `Scope` cell is said in its feature: a feature with no summary
  takes the cell as one, and any other column goes to the feature's
  `## Context`.
- The `specs` area becomes `nav: work` in `docs/_areas.yml`, and
  `docs/specs/epics/index.md` is seeded.
- The repository's own board script retires, with whatever calls it.

Then run `task docs:generate`, and fix every `docs.state-contradicts-work`
finding on the page (an epic or feature state that its features or stories
contradict). Never edit a derived region by hand.

## 8. Make the gate runnable

`task validate` runs kiln's checks through the kiln that `[kiln] ref` in
`.rn-forge/kiln/config.toml` pins. `kiln init` writes that ref; confirm it is
there. kiln is not a dependency: the tasks run it with `uvx`, in its own
environment, so the repository's lock and `pyproject.toml` do not change for it.
If the repository already lists `rn-forge-kiln` in a dependency group, or
carries an `override-dependencies` entry only so kiln resolves, remove them
(`deps.kiln-in-lock`).

Then `task setup`.

## 9. Run the gate and sort what is left

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

Done when both commands exit `0`.

## 10. Review

Read one `git diff`, file by file, before the first commit. Check it against
section 3's carry-over list and `.rn-forge/kiln/backups/`: nothing the
repository relied on was lost, and nothing is said twice. Report to the owner
what was carried over, what was deleted because kiln's block now states it,
which findings were kiln's, and the final output of both commands in section 9.
