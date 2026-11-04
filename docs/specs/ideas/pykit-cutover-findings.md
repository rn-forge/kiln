# pykit cutover findings

[Back to the ideas](index.md)

On 2026-11-03 pykit rehearsed its cutover (kiln's S7.2.4) in a worktree: branch
`feature/kiln-cutover` at pykit `c1dc2df`, kiln 0.1.0 from
`[kiln] ref = "feature/v1"` (`9e0e1cf`), archetype `python-lib`, docs profile
`mkdocs`. A review in a parallel session recorded 15 findings in pykit's
`docs/specs/epics/E16-kiln-adoption/cutover-findings.md`, on that branch only.

This page catalogues each finding with kiln's first reading and the owner's
observations, so they can be refined into stories. Nothing here is agreed until
an item says **Agreed**. Once every item is agreed, deferred or dropped, its
work moves to an epic and this page is deleted.

## What the rehearsal was reviewing

The review read the tree "as kiln left it, with nothing edited". That is the
state after step 2 of pykit's S16.3.1 (`kiln init`) and before step 4 (convert
the docs tooling), so the review saw an adoption half done.

**Why pykit's S16.3.3 did not produce kiln's docs shape.** It was not meant to.
On 2026-11-03 the owner cut S16.3.3 down to the format changes that need no
kiln:

- `## S…` story headings;
- `ideas.md` moved to `ideas/index.md`;
- links to excluded `_structure.md` pages made plain text.

Everything that needs kiln's config or tooling moved to S16.3.1's step 4, after
`init`:

- derived regions;
- `_areas.yml`;
- kiln's `_structure.md` files;
- deleting `docs/_update_board.sh`.

So `_areas.yml`, the `board:start`/`scope:start` markers and `_update_board.sh`
were still pykit's when the review ran.

**Why `feature/kiln-docs-model` got it right.** Its S16.3.3 (`4558752`,
2026-10-17) did the whole conversion by hand before `init`:

- it copied kiln's seeded `_areas.yml`, with `packages` as `nav: include` and
  `specs` as `nav: work`;
- it rewrote the board and release markers as `BEGIN derived` fences;
- it seeded `docs/specs/epics/index.md`;
- it deleted `_update_board.sh`.

pykit retired the branch on 2026-11-01. It was 136 commits behind
`feature/release-8`, and it left `docs/specs/ideas.md` where `doctor` refuses
it.

**Should pykit have followed kiln's adopt prompt instead?** S16.3.1 step 4
restates `kiln prompt --name adopt` §6–§7 almost line for line. Any repository
that restates the prompt can drift from it. The better answer is the owner's
observation below: a step with one right answer belongs in `init`, not in a
prompt, and not in an adopter's spec. The prompt keeps only judgement, and an
adopter's spec says "follow the adopt prompt" plus its own choices.

## The theme: `init` should settle what has one right answer

The adopt prompt's own opening says `init` "settles everything every repository
hits and that has one right answer". Several findings are steps the prompt
leaves to the adopter, although they have one answer for a given config:

| Step | Today | One right answer? |
| -- | -- | -- |
| A `python-lib` with `packages` has an `include` area in `_areas.yml` (#2) | adopt §6; `docs.packages-area-missing` in `task lint` only | Yes, except where it goes in the nav |
| `specs` is `nav: work` (#4) | adopt §7 | Yes, for kiln's work model |
| `task format` after `init` (#3) | adopt §4; F6.6 decided `init` formats nothing | Yes. The open question is the commit split |
| Derived regions are generated after seeding (#9) | adopt §7 | Yes |
| Legacy board and scope markers become `BEGIN derived` fences (#4) | adopt §7 | Mostly. Content moves need judgement |

A second theme is that **one failure hid the rest.** `task lint` stopped at
`mdformat` (#3) before it reached `kiln:doctor`. `kiln:doctor` would have
reported `docs.packages-area-missing`, the one-line diagnosis of #2's 33
`mkdocs --strict` warnings.

## Items

| # | Finding | Kiln's first reading | Owner's observation | Status |
| -- | -- | -- | -- | -- |
| 1 | Legacy workflows beside `ci.yml` | pykit retires `main.yml`, and the jobs it keeps go through `[[ci.jobs]]` | Licences, secret scan, internal ranges and the umbrella release look standard; kiln should offer them behind opt-in or opt-out flags | Agreed 2026-11-04: [item 1](#1-the-jobs-mainyml-carries-that-ciyml-does-not). Taken by [E15](../epics/E15-ci-standard/index.md): [F15.2](../epics/E15-ci-standard/F15.2-licences-check.md), [F15.3](../epics/E15-ci-standard/F15.3-secret-scan.md), [F15.4](../epics/E15-ci-standard/F15.4-internal-ranges.md), [F15.5](../epics/E15-ci-standard/F15.5-umbrella-release.md), [F15.6](../epics/E15-ci-standard/F15.6-scorecard.md) |
| 2 | Derived nav has no Packages | Caused by the review point; adopt §6 covers it | kiln should detect the structure at `init`, or make it configurable in `config.toml` | Agreed 2026-11-04: [item 2](#2-the-packages-section-of-the-nav). Taken by [S16.2.3](../epics/E16-init-adopts-by-overwrite/F16.2-kiln-owns-mkdocs.md#s1623-packages-is-derived-from-packages) |
| 3 | `task lint` fails on mdformat | Adopt §4 says run `task format` | `init` should run `task format` itself | Agreed 2026-11-04: [item 3](#3-init-and-task-format). Taken by [S16.1.3](../epics/E16-init-adopts-by-overwrite/F16.1-opinionated-init.md#s1613-init-formats-and-generates-last) |
| 4 | Legacy derived-region markers | Caused by the review point; adopt §7 covers it | Covered by the theme above | Agreed 2026-11-04: [item 4](#4-legacy-markers-and-the-two-dropped-rules). Taken by [F16.1](../epics/E16-init-adopts-by-overwrite/F16.1-opinionated-init.md); legacy markers are an SOP row ([F16.3](../epics/E16-init-adopts-by-overwrite/F16.3-cutover-sop.md)) |
| 5 | Dependabot drops `github-actions` | A real gap. A plain entry would bump pins in generated files, which is drift | — | Agreed 2026-11-04: [item 5](#5-action-pins-in-repository-owned-workflows), option (a). Taken by [F15.7](../epics/E15-ci-standard/F15.7-repo-owned-workflows.md) |
| 6 | `[kiln] ref` is a branch | The rehearsal runs from `feature/v1` by design. A doctor check would fail kiln's own CI before the tag | — | Leaning: idea |
| 7 | `site_dir` disagrees | `task docs:build` always passes `--site-dir`, so `mkdocs.yml`'s value is unused | Who owns `mkdocs.yml`? Whatever removes `.out/site` should be kiln's | Agreed 2026-11-04: [item 7](#7-mkdocsyml-and-site_dir). Taken by [S16.2.2](../epics/E16-init-adopts-by-overwrite/F16.2-kiln-owns-mkdocs.md#s1622-docsmkdocs-and-site_dir-render-into-mkdocsyml) |
| 8 | Audit excludes 8 packages | The list is `RN_FORGE_TAGS`, kiln's pin table, not `packages`. `--no-emit-workspace` already drops pykit's members, so it does nothing there. Probably obsolete since F7.5 | — | Agreed 2026-11-04: [S16.4.4](../epics/E16-init-adopts-by-overwrite/F16.4-generated-file-hygiene.md#s1644-the-audit-exclude-list-8) |
| 9 | Seeded epics index is empty | Caused by the review point, but the seed text claims something about the tree | Covered by the theme above | Agreed 2026-11-04: [theme](#the-theme-init-should-settle-what-has-one-right-answer). Taken by [S16.1.2](../epics/E16-init-adopts-by-overwrite/F16.1-opinionated-init.md#s1612-init-overwrites-kiln-shaped-files-and-archives-them) and S16.1.3 |
| 10 | Drift runbook calls bare `kiln` | A real gap. An adopted repository has no `kiln` on PATH, since the tasks run it with `uvx` at the pinned ref. The generated `CLAUDE.md` block says "run `kiln apply`" too | — | Agreed 2026-11-04: [S16.4.5](../epics/E16-init-adopts-by-overwrite/F16.4-generated-file-hygiene.md#s1645-kilndiff-and-kilnapply-tasks-10) |
| 11 | New dev dependencies have no floor | `_DEV_GROUP` in `modules/python/scaffold.py` has no floors; `_DOCS_GROUP` has them | — | Agreed 2026-11-04 (joins R4): [S16.4.3](../epics/E16-init-adopts-by-overwrite/F16.4-generated-file-hygiene.md#s1643-dev-tools-carry-version-floors-11) |
| 12 | `_areas.yml` header says nav is manual | Caused by the review point | Covered by item 2 | Agreed 2026-11-04. Taken by [S16.2.3](../epics/E16-init-adopts-by-overwrite/F16.2-kiln-owns-mkdocs.md#s1623-packages-is-derived-from-packages) |
| 13 | `.importlinter` comments stale | pykit's | — | pykit |
| 14 | `docs` job persists credentials | mike needs the token to push `gh-pages`; add the justification comment `release.yml.j2` has | — | Agreed 2026-11-04: [S16.4.6](../epics/E16-init-adopts-by-overwrite/F16.4-generated-file-hygiene.md#s1646-the-docs-jobs-persisted-credentials-are-justified-14) |
| 15 | `UV_CACHE_DIR` vs setup-uv | Plausible: the Taskfile's `.uv-cache` overrides the `UV_CACHE_DIR` setup-uv exports. Check a green run's post-step first | — | Open: verify |

### 1. The jobs `main.yml` carries that `ci.yml` does not

What kiln decided before:

- **F4.11** (2026-10-20, "Not adopted"): no gitleaks, because GitHub secret
  scanning and push protection are repository settings.
- **F6.8** (owner decision, 2026-10-31): `dependency-audit`, `licenses` and
  `secret-scan` stay pykit's, through `[[ci.jobs]]`, and the idea
  `ci-security-jobs` is parked.
- **F7.6**: the umbrella release stays pykit's, because kiln's release model
  does not number releases.

The owner now questions all of these. The jobs fall into three groups.

| Job | What it does in pykit | Kiln's reading |
| -- | -- | -- |
| `dependency-audit` | `pip-audit` | **Already rendered:** `python:lint:audit`, in `task lint`. Nothing to add |
| `licenses` | `pip-licenses`, failing on UNKNOWN and GPL, with a package ignore list | Generic. It needs a policy in config (the deny list and ignored packages). A good opt-in candidate |
| `secret-scan` | gitleaks release binary, SHA-checked, over git history | Generic. It overlaps GitHub's push protection, which is free on public repositories but has to be turned on. A good opt-out candidate, which revises F4.11 |
| `internal-ranges` | `rn-forge-devops requirements`: workspace members depend on each other by range (pykit E19) | Generic to any multi-member `python-lib`. It fits as a `kiln-devops` command, since `kiln-devops` is that planner |
| `umbrella-release` | One GitHub release per numbered docs release, from `docs/releases/` | Newly generic: every kiln repository now has the same `docs/releases/` model, so F7.6's reason may no longer hold |
| `scorecard.yml` | OpenSSF Scorecard | The idea `openssf-scorecard` |
| `broker-profile.yml` | pykit's broker profile | pykit's own |

Open questions:

- Opt-in or opt-out for each job, and the key shape. One option is
  `[ci.security] licenses = true`; another is a list such as
  `[ci] checks = [...]`.
- Whether `node-lib` gets equivalents in the same story (the idea
  `node-lib-ci-security`) or later.
- **Release 1 or release 2.** The cutover is not blocked: `[[ci.jobs]]` exists,
  and pykit can move a job to kiln's version later by deleting its entry. The
  tag is held only for S7.2.4.

### 2. The Packages section of the nav

`nav.py` emits `Packages:` with one `!include <package>/mkdocs.yml` for each
entry in `packages`, but only from an area with `nav: include`. `_areas.yml` is
seeded, so `init` keeps the repository's own file, and no area means no Packages
section. Today only `docs.packages-area-missing`, in `task lint`, says so.

Options:

- (a) `init` adds a missing `include` area to an existing `_areas.yml` for a
  `python-lib` with `packages`. By default it goes first, as kiln's seed puts
  it, and `init` reports it as a change. This would be the first time kiln
  edits a seeded file after seeding it. It is the same kind of restructuring
  `init` already does to `.importlinter` and `.gitignore`.
- (b) A `config.toml` key, such as `[docs] packages_area = { title, position }`,
  with the Packages section derived from config and no area needed. This
  splits the nav's configuration across two files: `_areas.yml` holds every
  other area.
- (c) `init`'s closing check runs `docs-structure`, so the finding shows in the
  `init` output.

Kiln's lean is (a) plus (c), with (a) generalized: `init` reconciles a seeded
`_areas.yml` with every area that the config and kiln's checks require. That
covers `specs` as `nav: work` too (#4), and the stale header (#12).

### 3. `init` and `task format`

F6.6 decided that `init` runs neither `task setup` nor `task format`. The
reasons are recorded there:

- `init`'s commit then holds only kiln's change;
- S5.3.6's rule that kiln does not reformat repository-owned files stands.

The owner wants `init` to format. Ways to keep both:

- `init` runs `task setup` and `task format` last, and lists the files that
  formatting alone changed. The adopter can then commit them separately (kiln
  commits nothing).
- An `init --no-format` escape.

Either way S5.3.6's rule and F6.6's decision get a dated revision.

The other half of #3 is that `task lint` stops at its first failure. Running
every step and reporting them together is a go-task design change. It may be
unnecessary once `init` formats, because the first failure was formatting.

### 4. Legacy markers and the two dropped rules

The legacy markers (`<!-- scope:start -->`, `<!-- board:start -->`) are pykit's
and ngkit's lineage, not a kiln convention. Teaching `docs:generate` to replace
them is kiln code for one migration. Under the theme above, this is a candidate
for an `init` or `port-docs` step that reports each page still carrying them.

The two rules missing from the rendered `docs/specs/_structure.md` are:

- a retired epic gets a line of prose on the board;
- ideas are linked from the board.

Kiln's lean is that neither belongs in the standard. The board can say both in
its own prose outside the fence, as kiln's board does for ideas.

### 5. Action pins in repository-owned workflows

F4.11 recorded this gap (S4.11.4). Pins in generated files move only with kiln's
`pins.toml`, and a Dependabot bump of a generated file fails `lint:generated`.
pykit's own workflows (`scorecard.yml` and the called workflows) have no updater
after the cutover. ngkit loses the same thing (idea `kiln-pins-freshness`).

Options:

- render `github-actions` with an `ignore:` entry for every action in
  `pins.toml`, so Dependabot moves only pins kiln does not own;
- state in the standard that repository-owned workflows are the repository's to
  keep current.

### 7. `mkdocs.yml` and `site_dir`

kiln writes `mkdocs.yml`'s body once, only when it is absent
(`modules/docs/scaffold.py`). It owns one fenced region, the derived nav.
`[docs] site_dir` reaches only `tasks/docs.yml`'s `--site-dir`, so pykit's
`site_dir: .out/site` is unused but misleading.

The owner's view is that the fix should be kiln's. Options:

- `init` reconciles `site_dir` in `mkdocs.yml` with config, as it already places
  the nav markers;
- `doctor` reports a mismatch;
- kiln renders `site_dir` into a managed region, and `--site-dir` goes.

## Owner review of `feature/kiln-cutover`, 2026-11-04

The owner is reviewing pykit's cutover branch. Each point below records the
owner's input, what kiln's code says, kiln's counters and a recommendation. R1
changes the frame for the whole page, so the items above are re-read under it at
the end of this section.

| # | Owner's input | Recommendation | Status |
| -- | -- | -- | -- |
| R1 | `init` as opinionated as `new`, with no merging. pykit and ngkit cut over once, by a manual SOP that carries what they do well into kiln's standard | Agree, with one line drawn: kiln-shaped files get overwritten, content is never touched | Agreed 2026-11-04: [R1](#r1-an-opinionated-init-and-a-one-time-cutover-sop). Taken by [F16.1](../epics/E16-init-adopts-by-overwrite/F16.1-opinionated-init.md) and [F16.3](../epics/E16-init-adopts-by-overwrite/F16.3-cutover-sop.md) |
| R2 | kiln owns `mkdocs.yml`. It renders the whole file from the docs tree plus a repo hook | Agree. Nav extras go in `_areas.yml`; other settings go in `[docs.mkdocs]` | Agreed 2026-11-04: [R2](#r2-kiln-owns-mkdocsyml). Taken by [F16.2](../epics/E16-init-adopts-by-overwrite/F16.2-kiln-owns-mkdocs.md) |
| R3 | Organize kiln's `.gitignore` block: blank lines between categories, with reasons | Agree. A comment line goes *above* each group, because gitignore has no trailing comments | Agreed 2026-11-04: [R3](#r3-kilns-gitignore-block). Taken by [S16.4.1](../epics/E16-init-adopts-by-overwrite/F16.4-generated-file-hygiene.md#s1641-the-gitignore-block-is-grouped-and-rendered-per-archetype-r3) |
| R4 | `pyproject.toml` entries are appended, not sorted as uv would sort them | Owner's decision: kiln re-sorts the whole group by normalized name on every write, even when that reorders the repo's own entries | Agreed 2026-11-04 (owner's choice): [R4](#r4-dependency-group-order-in-pyprojecttoml). Taken by [S16.4.2](../epics/E16-init-adopts-by-overwrite/F16.4-generated-file-hygiene.md#s1642-the-dependency-group-is-re-sorted-on-every-write-r4) |
| R5 | If `main.yml` is deleted for `ci.yml`, which one runs on the PR? | Only `ci.yml`. Delete `main.yml` in the same PR, but check what `ci-ok` stops gating first | Answered 2026-11-04; gating closed by absorbing first ([R6](#r6-the-ci-model-everything-pykit-runs-in-kiln)): [R5](#r5-mainyml-and-ciyml-on-the-cutover-pr). Delete `main.yml` in the cutover PR: [S7.2.4](../epics/E7-pykit-release-pin-flip/F7.2-kiln-release-and-config-upgrade.md#s724-run-the-cutover-sop-on-pykit-then-ngkit) |
| R6 | Everything pykit's CI does should be in kiln, some of it opt-in through `config.toml` | Agree: a check registry and `[ci.checks]` | Agreed 2026-11-04: [R6](#r6-the-ci-model-everything-pykit-runs-in-kiln). Taken by [E15](../epics/E15-ci-standard/index.md), [F15.1](../epics/E15-ci-standard/F15.1-check-model.md) and F15.2–F15.6 |
| R7 | A structured CI design for every archetype, a matrix of checks, a known hook for a repository's own steps | Agree: `ci.md` plus ADR-0016, a finite epic, a derived matrix | Agreed 2026-11-04: [R7](#r7-where-the-ci-design-lives-proposal-2026-11-04). Taken by [E15](../epics/E15-ci-standard/index.md), [F15.1](../epics/E15-ci-standard/F15.1-check-model.md) and [F15.7](../epics/E15-ci-standard/F15.7-repo-owned-workflows.md) |

### R1. An opinionated `init` and a one-time cutover SOP

**Input.** `new` will be used far more than `init`. `init` should write every
file a repository needs to be on kiln's standard, as `new` does, and not merge
with what is there. The merge problems seen so far are pykit's and ngkit's, the
only two repositories with a pre-kiln lineage like this. They cut over once,
manually, by an SOP. The goal of that SOP is to review the differences and keep
what each repository does well, folded into kiln's standard. Then the repository
loses nothing and future repositories get it too. The specs on both sides have
grown complex across the runs and findings. They should be cleaned up to a
simple approach for something done once.

**What `init` merges today.** Each of these is code that exists for adopters
only:

- `.gitignore`: `_dedupe_gitignore` (`commands.py`) drops repository lines that
  kiln's block already holds, and skips the file when any `!` rule exists;
- `pyproject.toml`: `add_task_tools` (`modules/python/scaffold.py`) appends the
  missing task tools to existing groups, which is R4;
- `mkdocs.yml`: `mark_nav` places the nav fence in an existing file, and
  `_archive` backs it up first;
- `_areas.yml`, `_structure.md` and the epics index are seeded only when absent,
  which is the cause of #2, #4, #9 and #12;
- the adopt prompt's §4–§7 hand the rest to the adopter, and pykit's S16.3.1
  step 4 restates them.

**Recommendation (agreed 2026-11-04).** `init` writes `new`'s file set over the
tree, with one rule for what it may overwrite:

- **Overwritten (kiln-shaped):** tooling and config, such as `Taskfile.yml`,
  `tasks/`, the workflows kiln renders, `.editorconfig`, `.taplo.toml`,
  `mdformat.toml`, `.importlinter`, `mkdocs.yml` (R2), `docs/_areas.yml` and
  every `_structure.md`, plus seeded indexes that have no content yet;
- **merged only where a tool already owns the file:** `pyproject.toml` (uv's
  tables) and `.gitignore` (kiln's fenced block). These keep today's
  block-and-append behaviour, fixed by R3 and R4;
- **never touched:** source, tests, docs content pages, README prose, ADRs and
  specs.

Everything overwritten is archived to `.rn-forge/kiln/backups/` first, as
`_archive` already does, and git is the review tool. `init` then runs
`task format` (#3) and `docs:generate` (#9), so its output passes `task lint`.

The **cutover SOP** is `docs/runbooks/cutover.md` (agreed 2026-11-04): a runbook
holding the steps and the absorb/extend/drop table format. Each repository's
verdict table lives in its own spec and links to the runbook. This ideas page is
pykit's first table. The SOP is used for pykit and then ngkit:

1. Branch, then run `kiln init`.
1. `git diff` file by file. For each behaviour the repository loses, record it
   in a table: the file, what was lost, and a verdict of **absorb** (a kiln
   story, so every repository gets it), **extend** (keep it through an
   extension point: `[[ci.jobs]]`, `_areas.yml`, `[docs.mkdocs]`) or **drop**.
1. Land the absorb stories in kiln, bump `[kiln] ref`, and re-run `init`.
1. Merge when the table has no absorb rows left open.

**What this simplifies.**

- kiln: the adopt prompt keeps only judgement (no §4–§7 mechanics). S7.2.4's
  rehearsals become "run the SOP on pykit". This page is the first table.
- pykit: E16/F16.3's step lists collapse to "follow kiln's cutover SOP" plus
  pykit's own verdicts. `cutover-findings.md` on the branch is superseded by
  this page.
- ngkit: E17 likewise.
- Superseded decisions get dated revisions: F6.6 (`init` formats nothing),
  S5.3.6 (kiln does not reformat repository-owned files, which now holds only
  for content) and the seed-once rule for `_areas.yml` and `mkdocs.yml`.

**Counters, settled 2026-11-04.**

- `_areas.yml` holds real choices: area titles, order, and which areas are
  `include`. Resolved: `init` overwrites it, and the SOP records the
  repository's area choices as extend rows. A cutover is reviewed by diff
  anyway.
- An opinionated `init` on a repository that has never seen kiln is destructive
  by design. Resolved: `kiln init` refuses to run unless the worktree is clean
  (`git status` clean). It still backs up what it overwrites, and prints the
  backup path. The gate is not warn-only and has no `--force`.

### R2. kiln owns `mkdocs.yml`

**Today.** `modules/docs/scaffold.py` writes `mkdocs.yml.j2` once, when the file
is absent, and kiln owns only the `BEGIN derived nav` fence that `nav.build_nav`
fills from `_areas.yml`, the tree and `packages`. The body already derives from
config: `site_name`, the `monorepo` plugin and `pymdownx.snippets` for
`python-lib`, and the mkdocstrings `paths`. `site_dir` is the exception: it
reaches only `tasks/docs.yml` (#7).

**Recommendation (agreed 2026-11-04, as split).** `mkdocs.yml` becomes a managed
artifact with a provenance header, rendered whole, so `lint:generated` catches
an edit in place. The repository's hook is split by kind:

- **Nav additions** (external links, extra sections, ordering) go in
  `_areas.yml`, which is already the nav's config. One file for the nav was
  the reason item 2's option (b) was rejected.
- **Everything else** (extra plugins, `markdown_extensions`, theme overrides,
  `extra_css`, `extra`) goes in a `[docs.mkdocs]` table in `config.toml`,
  rendered in place. `site_dir` is rendered from `[docs] site_dir`, which
  closes #7, and the `--site-dir` flag can go.

mkdocs's own `INHERIT:` does not fit. It replaces lists rather than merging
them, so nav and plugins could not be extended through it.

**Packages (agreed 2026-11-04).** kiln derives the Packages section from
`packages` for every `python-lib`, with no area needed. Title and position
default to kiln's seed and can be overridden in `_areas.yml`.

**This closes:** #7, #12 (the header is kiln's), and #2, unconditionally.

**Before the story.** List what pykit's and ngkit's `mkdocs.yml` carry beyond
the template, as SOP rows, so `[docs.mkdocs]` is sized to real needs and not
guessed. kiln's own `mkdocs.yml` is the first adopter.

### R3. kiln's `.gitignore` block

`modules/core/templates/gitignore.j2` renders 14 flat lines with one comment.
gitignore comments must start a line: `site/ # reason` is the pattern
`site/ # reason`, not a comment. So each reason goes on a comment line above its
group. Proposed groups:

- kiln's state: `backups/`, `rendered/`, `state.lock`;
- OS: `.DS_Store`;
- Python tool caches: `.pytest_cache/`, `.ruff_cache/`, `.import_linter_cache/`,
  `.uv-cache/`;
- coverage: `.coverage`, `.coverage.*`, `coverage.xml`;
- docs output: `.docs-site/` (`[docs] site_dir`), and `site/` for mkdocs's
  default.

**Agreed 2026-11-04:** these groups, with a blank line between groups and a
reason comment line above each.

A second gap: the template has no conditions, so a `node-lib` gets the Python
caches and a `docs = none` repository gets the docs lines. Each group is
rendered only for the archetype and docs profile that need it.
`_dedupe_gitignore` already skips blank and comment lines, so it is unaffected.
pykit's diff showed it dropping pykit's own `.DS_Store`, `.pytest_cache`,
`.ruff_cache`, `.coverage` and `coverage.xml` lines, as designed.

### R4. Dependency-group order in `pyproject.toml`

`add_task_tools` calls `groups[name].append(entry)`. pykit's `dev` group gained
`actionlint-py`, `pip-audit`, `taplo` and `zizmor` after `types-authlib`. The
four are sorted among themselves but not against the group.

pykit's `dev` group was not fully sorted to begin with: `aiosqlite`, `alembic`
and others sit after `pytest-cov`.

**Decision (owner, 2026-11-04, differing from kiln's first recommendation).**
kiln re-sorts the whole dependency group by normalized name on every write, even
when that reorders the repository's own entries. The alternative considered was
uv's rule (insert in sorted position when the list is already sorted, append
otherwise), which kiln first recommended and the owner did not choose.

`init` reformatted the lists to 4-space indent too, which is `_multiline_lists`.
That is fine once `init` formats as R1 says. R4 stays bundled with #11 (no
version floors on `_DEV_GROUP`) in one story.

### R5. `main.yml` and `ci.yml` on the cutover PR

**Facts from the branch.** Both files trigger on `push` to `main`,
`pull_request` to `main` and `workflow_dispatch`. Both use the concurrency group
`ci-${{ github.ref }}`, and both end in a job named `ci-ok`. pykit's ruleset (id
24435474\) requires one status check, context `ci-ok` from GitHub Actions, with
strict mode on. There is no classic branch protection.

**The answer.** On a `pull_request` event, GitHub reads workflow files from the
PR's merge ref. If the PR deletes `main.yml`, only `ci.yml` runs, on the PR and
on `main` after merge. The required check is matched by its context name, not by
workflow, so `ci.yml`'s `ci-ok` satisfies the ruleset with no settings change.

**If both stayed,** they would share the concurrency group. Concurrency groups
are repository-wide, so on a PR one workflow cancels the other. That leaves two
`ci-ok` contexts, one of them cancelled, which can block the merge. So
`main.yml` must go in the same PR that adds `ci.yml`, never in a follow-up.

**What the swap stops gating.** `ci.yml`'s `ci-ok` needs only its own jobs.
`import-boundaries`, `licenses`, `secret-scan`, `internal-ranges` (a call to
`internal-ranges.yml`) and `umbrella-release` (a call to `umbrella-release.yml`)
leave the gate unless they are declared in `[[ci.jobs]]`. `dependency-audit` is
covered by `task lint`, and so is `import-boundaries` if `lint` runs
import-linter. Verify both on the branch. Deleting `main.yml` also orphans
`internal-ranges.yml` and `umbrella-release.yml`, which have no other caller.
Under R1 each of these is an SOP row: absorb (item 1's opt-in jobs) or extend
(`[[ci.jobs]]` until then).

**Open (deferred 2026-11-04).** What happens to the jobs `ci-ok` stops gating
(`licenses`, `secret-scan`, `internal-ranges`, `umbrella-release`): declare them
in `[[ci.jobs]]` in the same PR, absorb them into kiln first, or accept a gap.
The owner: "the owner will discuss CI more". It is tied to item 1.

### R6. The CI model: everything pykit runs, in kiln

**Input (2026-11-04).** Everything pykit's CI does today should be in kiln, and
some steps can be opt-in through `config.toml`. This revises F4.11 (no
gitleaks), F6.8 (security jobs stay pykit's) and F7.6 (the umbrella release
stays pykit's).

**Principles.** The first three are kiln's today; the last two are new.

1. One workflow (`ci.yml`) and one required check (`ci-ok`). The workflow is
   kiln's, and a repository never edits it.
1. Every check is a `task` verb first and a job second. It runs locally the same
   way, and the job only orchestrates it.
1. A check gets its own job only when it needs one of these: full git history,
   extra permissions, services, a schedule, or a fork guard. Otherwise it
   folds into `task validate`/`task lint`, with no new job.
1. A check has one of three switches:
    - **standard:** always on;
    - **derived:** on when the tree calls for it, with no key;
    - **configured:** a key in `[ci.checks]`, defaulting on or off.
1. Each check names one tool per stack. `python-lib` and `node-lib` share the
   key, so ADR-0016's one-contract rule holds.

**pykit's CI, mapped.**

| pykit job | Where it lands | Switch | Default |
| -- | -- | -- | -- |
| plan, verify, postgres, redis, smoke, suites, sonar, release, external-install, docs | Already in kiln's workspace `ci.yml` | standard (sonar: `[ci] sonar`) | on |
| `import-boundaries` | Already in `task lint` (`lint-imports`) | standard | on |
| `dependency-audit` | Already in `task lint` (`pip-audit`) | standard | on |
| `licenses` | New `task lint:licenses` in `validate`, with policy in config | configured | **on**, deny GPL/AGPL/UNKNOWN |
| `secret-scan` | New `secret-scan` job (gitleaks, SHA-pinned, `fetch-depth: 0`, fork-guarded) in `ci-ok`, plus a `task` verb | configured | **on** |
| `internal-ranges` | `kiln-devops requirements` inside the `plan` job | derived: a workspace with two or more members | on |
| `umbrella-release` | A step of kiln's release job, from `docs/releases/` | configured | off |
| `scorecard.yml` | A separate kiln workflow (schedule, `security-events: write`), not in `ci-ok`: it reports and does not gate | configured | off (public repositories only) |
| `broker-profile.yml` | Stays pykit's: a scheduled, non-gating Keycloak run that only pykit has | repository-owned | — |

**Config shape.** One table holds the configured checks. A boolean switches a
check, and an inline table also carries its policy:

```toml
[ci.checks]
secret-scan = true                    # default true
licenses = { deny = ["GPL-*", "AGPL-*", "UNKNOWN"], ignore = ["some-pkg"] }
umbrella-release = false              # default false
scorecard = false                     # default false
```

`[[ci.jobs]]` stays as the escape hatch for a gating job that is truly the
repository's. Under R1 an SOP row that lands there is an **extend** verdict.

**Repository-owned workflows** (`broker-profile.yml`) stay allowed, for
non-gating scheduled runs only. That reopens item 5. Their action pins need an
updater, so this is item 5's option (a): Dependabot `github-actions` with an
`ignore:` entry for every action in `pins.toml`.

**Cutover consequence (R5's open question).** If these checks land in kiln
before pykit's cutover PR, `ci.yml`'s `ci-ok` gates all of them, and pykit
declares no `[[ci.jobs]]` at all. That is the SOP's "absorb first" path. It
costs one feature (licences, secret scan, internal ranges, the umbrella release)
ahead of S7.2.4. The idea `ci-security-jobs` and item 1 fold into that feature,
and `node-lib-ci-security` becomes its node half.

**Answered by the owner, 2026-11-04. Agreed.**

- The defaults are as recommended: on for licences and the secret scan, off for
  the umbrella release and Scorecard.
- The `node-lib` half lands in the same feature:
  [F15.2](../epics/E15-ci-standard/F15.2-licences-check.md) and
  [F15.3](../epics/E15-ci-standard/F15.3-secret-scan.md) cover both stacks.
- Absorb before the cutover: pykit declares no `[[ci.jobs]]` for these checks,
  and S7.2.4 waits on E15.
- Release 1.

Taken by [E15](../epics/E15-ci-standard/index.md). The ideas `ci-security-jobs`,
`node-lib-ci-security` and `openssf-scorecard` are folded into it.

### R7. Where the CI design lives (proposal, 2026-11-04)

**Input.** A structured CI design, written for every archetype, that can be
referenced at any time. It has a matrix of checks: mandatory, or optional with a
default of on or off, all managed through config. It is attached to an epic that
keeps growing as new archetypes show new needs. Repositories get a known hook
for their own steps.

**Kiln's proposal.** Split by what each document is for, as `docs/_structure.md`
routes them:

| What | Where | Why |
| -- | -- | -- |
| The CI as it is now: per-archetype pipelines and the check matrix | `docs/architecture/ci.md` | The always-current reference. Architecture describes now and is never duplicated into a spec |
| The model (one workflow, `ci-ok`, check switches, hook tiers) | ADR-0016, revised in place | ADR-0016 is already "one CI contract for every archetype". F4.11, F6.8 and F7.6 get dated revisions pointing to it |
| Work to reach the model | A new epic, `E15-ci-standard` | Holds the target design until each feature lands, then its rows move to `ci.md` |
| Each repository's own matrix | The rendered `.rn-forge/kiln/standard.md` | An adopter sees which checks it runs, and why |

**The matrix is derived, not hand-written.** kiln keeps one check registry in
code: check, archetypes, switch, default, task verb and job. That registry
renders `ci.yml`, validates `[ci.checks]`, and fills a `BEGIN derived` region in
`ci.md` and `standard.md`. The doc then cannot drift from the workflow, and
adding a check is one registry row plus its task.

**The epic should be finite.** kiln's work model closes epics. An epic that is
never closed becomes a second backlog that the board cannot show as done. E15
carries the model, pykit's absorbed checks and `node-lib` parity, then closes. A
CI need found later goes to `ideas/` and then to a feature under whichever epic
owns that archetype's work, with `ci.md` as the one living document.

**Hook tiers.** All of them live in `config.toml` and name repository-owned
`task` verbs, so the entrypoint rule holds:

1. `[ci.checks]`: switch a kiln check, or set its policy.
1. `[ci.hooks]`: steps inside kiln's jobs, as `setup` and `docs` do today, with
   stage points added only when a repository needs one.
1. `[[ci.jobs]]`: a repository's own job, gated by `ci-ok` unless it declares
   `required = false`, a boolean flag that controls whether the job is in
   `ci-ok`'s `needs`.
1. A repository-owned workflow file: allowed for non-gating or scheduled runs
   only (`broker-profile.yml`), with Dependabot keeping its pins current (item
   5).

There is no separate hook file. `config.toml` is already the one place a
repository talks to kiln.

**Agreed 2026-11-04:** this split, the finite epic, the derived matrix, and the
archetype list `ci.md` covers (`python-lib`, `python-tool`, `python-app`,
`python-web-api`, `python-web-app` and `node-lib`). The design page is
[the CI architecture page](../../architecture/ci.md) and the model is
[ADR-0016](../../adr/ADR-0016.md), revised. Taken by
[E15](../epics/E15-ci-standard/index.md), starting with
[F15.1](../epics/E15-ci-standard/F15.1-check-model.md).

### R8. Review of `ci.md` and E15 (agreed 2026-11-04)

The owner reviewed the new [ci.md](../../architecture/ci.md) and E15. Kiln's
reading and recommendation for each point. The owner agreed all of them on
2026-11-04; the answers are recorded after the table.

| # | Owner's question | Kiln's reading | Recommendation |
| -- | -- | -- | -- |
| R8.1 | Why does `python-lib` render `postgres` and `redis` jobs? They are one stack's | They came from pykit's planner. A package opts in with `[tool.workspace-ci.postgres]` or `[tool.workspace-ci.redis]`, and the jobs run its tests against a service container. The mechanism is generic; the names are pykit's | One `integration` stage: a package declares the service containers it needs (image and env), and the matrix runs one leg per package. postgres and redis become data, not jobs |
| R8.2 | Shouldn't `smoke` and `suites` apply to every archetype, with a common vocabulary and only the how stack-specific? | Yes. Today they exist only in the `python-lib` workspace pipeline | One stage vocabulary for every archetype: `validate` → `test` → `integration` → `smoke` (the built artifact installs and starts) → `suites` (end-to-end, cross-unit) → `sonar` → `release` → `verify-release` (install from the registry) → `docs`. Each archetype maps each stage to a task, or marks it n/a. A single-package archetype has a plan of one unit |
| R8.3 | Why do the other Python archetypes have `docs.yml` and `python-lib` does not? | `python-lib` deploys versioned package sites from `ci.yml` after release (F6.4 and F11.5). The single-package archetypes kept E5's separate `docs.yml`, outside `ci-ok` and not gated on release. That is history, not design | Fold into `ci.yml` for every archetype (F15.8, gap 1) |
| R8.4 | Shouldn't `node-lib` have an external-install check? | It has one: `published-install`, in `release.yml`, which also runs its own gate | The same `verify-release` stage in `ci.yml` (F15.8, gap 2). The single-package Python archetypes lack it entirely (gap 3) |
| R8.5 | Could `ci.md` be structured better? Where is the to-be state? E15 has no design page | `ci.md` is ordered by mechanism and has a `python-lib` deep dive tacked on. `docs/specs/_structure.md` puts design that spans features in the epic's `design.md`, and E15 lacks one | Add `E15-ci-standard/design.md`: the stage vocabulary (R8.2), the archetype × stage × check matrix with switches and defaults, the `[ci.checks]` and `[[ci.jobs]]` (`required`) shapes, and the hook tiers. Restructure `ci.md` the same way (model → stages → matrix → hooks → per-archetype detail), describing only what is built. As each E15 feature lands, its rows move from `design.md` to `ci.md`. F15.8's gaps become build stories once R8.2 is agreed |

Also from this review:

**Agreed 2026-11-04.**

- **R8.1:** one `integration` stage, with services as data.
- **R8.2:** the nine stages `validate` → `test` → `integration` → `smoke` →
  `suites` → `sonar` → `release` → `verify-release` → `docs`, then `ci-ok`.
- **R8.3, R8.4:** all five F15.8 gaps fold into `ci.yml` with no exceptions, and
  stages may be split into kiln-rendered reusable workflow files for
  maintainability.
- **R8.5:** E15's `design.md` holds the to-be state, and rows move to `ci.md` as
  features land.
- **E6:** F6.5 moves to E16 as
  [F16.5](../epics/E16-init-adopts-by-overwrite/F16.5-rebuild-and-port.md)
  (S6.5.1 to S6.5.3 became S16.5.1 to S16.5.3).
- **Agent choices:** the licence task names and the CI-only secret scan are
  accepted. The umbrella release is available to every archetype, default off.
  Internal ranges are extended to `node-lib` (`workspace:^` and `workspace:~`
  only, never `workspace:*` or a literal version). `pnpm audit` is in release
  1; npm provenance is deferred to the idea `npm-build-provenance`.
- **F16.4 #8, #10 and #14:** confirmed.
- **Number clash:** noted only, no rename.

Notes from the review:

- **E6.** Every E6 feature is closed except F6.2 (retire taskkit, release 2) and
  F6.5 (the rebuild route: `kiln diff --from`, the adopt prompt's rebuild
  route, apollo). The closed features are history and stay. F6.5 overlaps E16:
  S6.5.1's `kiln diff --from` is the diff tool for the SOP's step 2, and
  S6.5.2 edits the adopt prompt that S16.1.4 slims. The recommendation is to
  move F6.5 into E16 as the SOP's rebuild route, keeping apollo as its worked
  example, and to leave E6 holding only F6.2. Done 2026-11-04.
- **Agent-made choices in E15 and E16** (accepted, see above):
    - task names `python:lint:licenses` and `node:lint:licenses`;
    - `ci:lint:secrets`, which runs in CI only;
    - the umbrella release is `python-lib` only, tagged `release-<n>`;
    - the rule `kiln-devops requirements` enforces;
    - `pnpm audit` and build provenance dropped from `node-lib-ci-security`.
- **Number clash.** kiln's E16 and pykit's E16 (kiln adoption) share a number,
  so cross-repository references name the repository.

### The items above under R1

| Items | Under R1 |
| -- | -- |
| 2, 4, 9, 12 | Closed by `init` overwriting `_areas.yml`, `_structure.md` and the seeded indexes, and by R2. #4's legacy markers become an SOP row, not kiln code. Agreed 2026-11-04. #2 is closed by deriving Packages from `packages`; #12 by kiln owning the header |
| 3 | `init` formats. F6.6 gets a dated revision |
| 7 | Closed by R2 (`site_dir` rendered from `[docs] site_dir`) |
| 1 | Agreed 2026-11-04: absorbed into kiln by E15, so the SOP has no `[[ci.jobs]]` rows for it |
| 5, 11 | Agreed 2026-11-04: 5 is F15.7, 11 joins R4 in F16.4 |
| 8, 10, 14 | Agreed 2026-11-04: stories in F16.4 |
| 6, 13, 15 | Open: 6 is a leaning idea, 13 is pykit's, 15 needs a run log |

## Next

- Items 6, 13 and 15 are still open; this page goes once every item is agreed,
  deferred or dropped. Decide 6, and verify 15 against a run log.
- The agreed work is elaborated in [E15](../epics/E15-ci-standard/index.md) (CI)
  and [E16](../epics/E16-init-adopts-by-overwrite/index.md) (adoption). Build
  order: F15.1, then F15.2–F15.7 and F16.1–F16.4, then
  [S7.2.4](../epics/E7-pykit-release-pin-flip/F7.2-kiln-release-and-config-upgrade.md#s724-run-the-cutover-sop-on-pykit-then-ngkit),
  which runs the SOP on pykit and ngkit, then the tag.
- Verify on the cutover branch that `task lint` runs import-linter (R5); it is
  the SOP's first row for `import-boundaries`.
