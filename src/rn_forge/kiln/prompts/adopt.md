# Cutting over to kiln by overlay

This prompt is the judgement for an overlay cutover: the steps are in
`docs/runbooks/cutover.md`, and this is what an agent decides once the reference
is built and its files are brought over. It prints guidance and installs
nothing. Facts from pykit (a `python-lib` workspace) and ngkit (a `node-lib`
workspace) are examples, not rules.

## 1. Choose the route

The overlay is the only route: build a reference repository with `kiln new`,
bring its files onto a branch of the existing repository, and review one diff. A
repository with no pre-kiln lineage is rebuilt with `kiln new` and its
generators and does not use this prompt.

## 2. Build the reference

Outside the repository, run one `kiln new` command per archetype, `python-lib`
or `node-lib`, with a `--config` file carrying the repository's archetype keys
(`docs/reference/standard-repo.md`, section 9):

```bash
kiln new <dir> --archetype <archetype> --docs mkdocs --owner <owner> --config <file> --yes
```

Use kiln from a checkout when it is not released:
`uv run --project <kiln> kiln …`.

- A library workspace lists its members:

    ```toml
    [archetype.python-lib]
    packages = ["packages/one", "packages/two"]   # nav order is this order
    modules = { "packages/one" = "rn_forge.one" } # only where the import module is not the path name
    import_contracts = "own"                       # keep the repository's own import contracts
    ```

    Each package must be an existing directory with a `pyproject.toml`. Use
    `import_contracts = "own"` when the repository already has `.importlinter`
    contracts worth keeping; kiln then renders only the root packages (run 1:
    pykit's layering contracts).

- A `node-lib` has no `[archetype.node-lib]` table; its file carries the
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

## 3. Classify the files

In the reference, `.rn-forge/kiln/state.json` lists every file's kind:

- **`managed`**: the whole file is kiln's, taken byte-for-byte.
- **`block`** (`.gitignore`, `.importlinter`, `CLAUDE.md`): only the fenced
  region is taken, markers included; the repository's text stays outside it.
- **`seeded`**: the repository's version wins; a seed the repository lacks is
  added.

Anything else in the repository is its own. A difference the repository keeps in
a managed file or block is not edited in: it goes back to kiln as config or
code.

## 4. Reconcile the files kiln has a block in

`CLAUDE.md` (and any other file that holds a kiln block) has two authors. Read
kiln's block and the repository's text together:

- Delete from the repository's part what the block now states.
- Where they contradict, kiln's block wins on structure: the `task` entrypoint,
  generated files, the docs rules. Correct the repository's text (run 1:
  pykit's `CLAUDE.md` pointed at `uv run` commands that the block forbids).
- Check the guides and runbooks the instructions link to for the same
  contradictions, and fix them on the page.
- Specs and decisions that do not follow kiln's work model are converted by
  `kiln prompt --name port-docs`'s rules, not here.

## 5. Rewrite commands to verbs

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

## 6. Make the gate runnable

`task validate` runs kiln's checks through the kiln that `[kiln] ref` in
`.rn-forge/kiln/config.toml` pins. `kiln new` wrote that ref in the reference;
confirm it is there. Before kiln's first release the ref is a branch, and
`kiln.pin-mismatch` only starts checking once it is a `v<version>` tag. kiln is
not a dependency: the tasks run it with `uvx`, in its own environment, so the
repository's lock and `pyproject.toml` do not change for it. If the repository
already lists `rn-forge-kiln` in a dependency group, or carries an
`override-dependencies` entry only so kiln resolves, remove them
(`deps.kiln-in-lock`).

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

Done when both commands exit `0`.

## 8. Review

Read one `git diff`, file by file, before the first commit. Check it against the
reference and the `kiln diff --old` inventory: nothing the repository relied on
was lost, and nothing is said twice. Report to the owner what was carried over,
what was deleted because kiln's block now states it, which findings were kiln's,
and the final output of both commands in section 7.

The verdict table for what the repository loses is in
`docs/runbooks/cutover.md`.
