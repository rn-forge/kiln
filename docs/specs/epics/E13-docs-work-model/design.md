# E13 design — the docs work model and derived regions

Shared by [F13.1](F13.1-derived-regions.md), [F13.2](F13.2-board-and-scope.md)
and [F13.3](F13.3-adopt-the-model.md). The decisions are
[ADR-0003](../../../adr/ADR-0003.md)'s derived regions,
[ADR-0011](../../../adr/ADR-0011.md) and [ADR-0012](../../../adr/ADR-0012.md).
Everything a builder copies is on this page verbatim: keys, rules, finding codes
and region shapes. Once a story is done, the code and templates are the only
home of that text, and the copy here is not maintained.

## Derived regions

| Region | File | Fence (`ManagedBlock`) | Inputs |
| -- | -- | -- | -- |
| Nav | `mkdocs.yml` | `ManagedBlock("derived nav", indent="  ")`, renamed from `generated nav` | `docs/_areas.yml`, the docs tree, each page's H1, `config.packages` (from S11.1.1) |
| Board | `docs/specs/index.md` | `ManagedBlock("derived board", comment="<!--")` | epic, feature and release pages |
| Scope | `docs/releases/release-<n>/index.md` | `ManagedBlock("derived scope", comment="<!--")` | feature pages whose `Iteration` names that release |

- None of them is an `Artifact`, and none has a `state.json` entry. `kiln apply`
  never writes them. `kiln docs-generate` writes all three, and `kiln new`
  calls the same function after its apply.
- The check is `docs-generate`. It regenerates each region in memory and reports
  `docs.nav-stale`, `docs.board-stale` or `docs.scope-stale` when the result
  differs from disk. It also reports every metadata finding below.
- The board and Scope regions, and metadata validation, apply only when
  `docs/specs/index.md` contains the board fence. Until kiln's own docs adopt
  the model (S13.3.2), kiln's tree has no fence, and the check passes.
- Every region body is mdformat-stable under the seeded `.mdformat.toml`
  (`wrap = 80`, `compact_tables = true`). The body opens and closes with a
  blank line, and table delimiters are `| -- |`. A test runs `mdformat.text`
  over each rendered region with `extensions={"gfm", "tables", "mkdocs"}` and
  the same options, and asserts that nothing changes.

## Nav titles

- An area's own `index.md` is titled `Overview`, as today.
- Every other page is titled with its first `# ` heading, stripped. A page with
  no H1 falls back to `title_from_filename`.
- So a sub-index such as `plans/reviews/index.md` takes its H1 (`Reviews`),
  which replaces S11.1.1's directory-name rule.

## The ownership model

This replaces §2's opening and kinds table in
[the reference](../../../reference/standard-repo.md#2-one-owner-per-file-or-per-block),
and the matching table in `standard.md.j2`. The ownership table below §2 already
uses most of these words ("input", "scaffolded once", "gitignored derived
data"), but the kinds table claims three kinds are "the whole model". Every path
kiln writes or reads has exactly one of these kinds:

| Kind | Owner | Written by | Recorded in `state.json` | Checked by |
| -- | -- | -- | -- | -- |
| **managed** | kiln | `kiln apply` | the file's SHA-256 | `generated`: drift if the file differs |
| **block** | kiln (the fence); repo (the rest of the file) | `kiln apply` | the body's SHA-256 and the markers | `generated`: drift if the body differs |
| **derived region** | kiln (the fence); repo (the rest of the file) | `kiln docs-generate`, and `kiln new` | nothing | `docs-generate`: stale if regenerating it from the repo's inputs differs |
| **seeded** | repo, after the first write | `kiln apply`, once, when absent | creation only | nothing, including presence (see below) |
| **scaffolded** | repo | `kiln new`'s scaffold step, once | nothing | nothing |
| **repo** | repo | never kiln | nothing | the repo's own tasks |
| **input** | repo | the owner, or `kiln config-update` | its hash, as `config_hash` | nothing compares it; `kiln apply` re-renders from it |
| **baseline** | kiln | `kiln apply` | — (it is the record; it never hashes itself) | `generated` reads it |
| **derived data** | kiln | kiln, at run time | nothing | nothing; gitignored |

- A file has one kind, except that a file holding a **block** or **derived
  region** is otherwise scaffolded or repo-owned: `.gitignore`, `CLAUDE.md`
  and `mkdocs.yml`.
- **Seeded** and **scaffolded** differ only in who writes them. A seeded file is
  an apply artifact, so a later `kiln apply` recreates it if it is absent and
  never touches it if present. A scaffolded file (`pyproject.toml`,
  `README.md`, the bodies of `CLAUDE.md`, `AGENTS.md` and `mkdocs.yml`, the
  first `src/` and `tests/`) is written by `kiln new` before its first apply,
  and never again.
- "Nothing, including presence" for **seeded** is the target set by
  [ADR-0003](../../../adr/ADR-0003.md). Today the `generated` check still
  reports a missing seeded file (`generated.seed-missing`), and
  [S4.6.5](../E4-generator/F4.6-doctor.md#s465-doctor-respects-ownership)
  removes that. S13.1.1 documents the target and leaves the check alone.
- Paths kiln neither writes nor reads (`.claude/**`, `.codex/**`, installed
  skills) are not kiln's and have no kind.

The rendered `.rn-forge/kiln/standard.md` lists, under the table, which paths in
that repository have each kiln-owned kind ("Managed here", "Blocks here",
"Derived regions here"), as it does today for managed files and blocks.

## The work model

### Page metadata

An epic, feature or release page opens with its `# ` title, then optional blank
lines, then a two-column table. The table's header row has two blank cells, and
its delimiter row is two cells of dashes; both `| --- | --- |` and mdformat's
`| -- | -- |` are accepted, as is `|  |  |` for the header. Each row after that
is `| **Key** | Value |`, and the table ends at the first line that is not such
a row.

| Page | Path | Keys, in this order |
| -- | -- | -- |
| Epic | `specs/epics/E<n>-<slug>/index.md` | `State`, `Tags`, `Start Date`, `Closed Date`, `Entry criteria` |
| Feature | `specs/epics/E<n>-<slug>/F<n>.<m>-<slug>.md` | `State`, `Parent`, `Iteration`, `Tags`, `Start Date`, `Closed Date`, `Predecessors`, `Source`, `Entry criteria` |
| Release | `releases/release-<n>/index.md` | `Status`, `Start Date`, `Finish Date` |

Epic and feature `State` is one of `New`, `Active`, `Closed`, `Removed`. Release
`Status` is one of `planned`, `in progress`, `shipped`. A story keeps a single
`**State:** New | Active | Closed (<date>) | Removed` line. Stories are not
validated.

A table is a header row, a delimiter row and body rows. An epic's feature table
is any table in the epic page, after the metadata table, with a body row whose
first cell contains `F<n>.<m>` (regex `F\d+\.\d+`). Its columns are found by
header name: it must have a `State` column, and it may have a `Tags` column. A
row whose first cell is a Markdown link to a file matching `F<n>.<m>-*.md` names
that feature file. Any other row is a fileless feature, such as a pre-taxonomy
row or an unelaborated deferred item, and its own `State` and `Tags` cells are
its only source.

A feature's `Iteration` names the release matched by `release-(\d+)` in its
value. Epic, feature and release titles on the board are their full H1 text.

### Rules and finding codes

Every finding is `Severity.ERROR`, with `path` set to the page, relative to the
repository root. Every rule is reported for every page, not just the first, with
two exceptions that keep each broken thing to one finding:

- A page with `docs.work-no-metadata` gets no other finding.
- When `State` (or a release's `Status`) is missing, only
  `docs.work-missing-key` is reported for it. The rules that read the state
  (`invalid-state`, `dates`, `iteration` for an `Active` feature) are skipped
  for that page.

| Code | Reported when |
| -- | -- |
| `docs.work-no-metadata` | an epic, feature or release page has no metadata table directly after its title |
| `docs.work-unknown-key` | a key is not in that page type's list |
| `docs.work-repeated-key` | a key appears twice |
| `docs.work-key-order` | a key comes before one that its list puts earlier |
| `docs.work-missing-key` | an epic has no `State`; a feature has no `State`, `Parent` or `Predecessors`; a release has no `Status` |
| `docs.work-invalid-state` | a `State` or release `Status` is not in its vocabulary |
| `docs.work-dates` | `Closed Date` is present but the State is not `Closed`, or the State is `Closed` with no `Closed Date`. For an epic, `Start Date` is required when `Active` or `Closed`, and forbidden otherwise. For a release, `Finish Date` is present but the Status is not `shipped`, or the Status is `shipped` with no `Finish Date` |
| `docs.work-entry-criteria` | `Entry criteria` without a `deferred` tag, or a `deferred` tag without `Entry criteria` (`Tags` is comma-separated) |
| `docs.work-iteration` | an `Active` feature has no `Iteration`; an `Iteration` names no `release-<n>`; or `releases/release-<n>/index.md` does not exist |
| `docs.work-no-state-column` | an epic's feature table has no `State` column |
| `docs.work-duplicate-id` | a feature ID is in two epic tables, or two feature files share an ID |
| `docs.work-state-mismatch` | an epic table row links a feature file, and the row's `State` cell differs from that file's `State` |
| `docs.board-markers` | `docs/specs/index.md` has one board fence marker without the other |
| `docs.scope-markers` | the board fence exists, but a release page lacks a scope fence |

A feature's `Start Date` is deliberately not validated. Its source model
required it in the template but never enforced it, and enforcing it now would
fail pages that already pass.

### The board region

`render_board(work)` returns exactly this shape, rows filled as described:

```markdown

## Releases

| Release | Status | Features |
| -- | -- | -- |
| [<release H1>](../releases/release-<n>/index.md) | <Status>[ (<Finish Date>)] | <counts> |

## Backlog

Features with no Iteration, by State and epic.

### New

| Epic | Features |
| -- | -- |
| [<epic H1>](epics/<dir>/index.md) | <features> |

### Deferred

| Epic | Features | Entry criteria |
| -- | -- | -- |
| [<epic H1>](epics/<dir>/index.md) | <features> | <epic's Entry criteria, or "Per feature; see the epic."> |

```

- Releases are listed newest first, by `<n>`. `<counts>` is the release's
  features by State, in the order `Active`, `New`, `Closed`, `Removed`,
  omitting zeros, joined with `·`. For example, `2 Active · 1 New`. A release
  with no features shows `—`.
- The backlog holds every non-`Removed` feature with no `Iteration`. A feature
  tagged `deferred` goes under Deferred. Otherwise it goes under New only if
  its State is `New`. A fileless row takes its own `Tags` cell, or failing
  that its epic's tag. An epic with no features at all, whose State is `New`,
  is listed with `—` as its features.
- Rows are ordered by epic number. Inside a row, features are ordered by feature
  number, joined with `, `, and each is linked (to `epics/<dir>/<file>`) when
  it has a file, or bare when it does not.
- `### New` or `### Deferred` is omitted when it is empty. When both are empty,
  the line under `## Backlog` reads
  `Every feature is on a release or Removed.` and no subsection follows.
- With no release pages and no epics, which is the seeded tree, the Releases
  table has no rows and the backlog line is the "Every feature…" line. The
  seeded `docs/specs/index.md` carries exactly that.

### The Scope region

```markdown

| Feature | Epic | State |
| -- | -- | -- |
| [F<n>.<m>](../../specs/epics/<dir>/<file>) | E<n> | <State> |

```

Rows are ordered by epic number, then feature number, numerically. A release
with no features keeps the header and delimiter rows only.

## The seeded rules

S13.3.1 writes each file below into each golden **byte for byte**, then copies
it to `modules/docs/templates/<path>.j2`. Each text is already mdformat-clean
under the seeded `.mdformat.toml`. `docs/releases/index.md` keeps its current
seed.

### `docs/specs/_structure.md`

Replaces the seed of the same path.

````markdown
# specs/ — what belongs here

## Belongs here

- Every piece of work as an epic, `epics/E<n>-<slug>/index.md` — done work
  included, so the tree is the inventory of what this repo is made of.
- An epic's features as `F<n>.<m>-<slug>.md` beside it, stories inline. A
  feature file, once written, stays when its work is closed.
- A closed epic whose work predates this taxonomy, its specs written after the
  code, keeps its features as rows in its `index.md`, with no feature files.
- Design for work not yet built: a `## Design` section in the feature it belongs
  to, or `design.md` in the epic when it spans features.
- Open questions, as a `## Open questions` section on the epic or feature they
  block.
- Ideas not yet agreed as work, in `ideas.md`.

## Does not belong here

| Instead of | Put it in |
| -- | -- |
| Behaviour that already exists | `architecture/` |
| A decision | an ADR under `adr/` |
| What a release carries beyond its scope | `releases/` |
| History and evidence | the commit message |
| A `progress.md`, `decisions.md` or `overview.md` | the epic, an ADR, or the README |

## Work items

Epics, features and stories follow Azure DevOps's Agile process, so that a move
to a tracker is a field-by-field mapping (see
[Tracker mapping](#tracker-mapping)).

### Metadata tables

An epic, feature or release page opens with its `# ` title and then a metadata
table. Its keys come in the fixed order below; a key that does not apply is left
out, never left blank. A value is short: a state, a date, an ID, a link or a
phrase, with no trailing period and no commit hash. `—` means none.

| Page | Keys, in order |
| -- | -- |
| Epic | `State`, `Tags`, `Start Date`, `Closed Date`, `Entry criteria` |
| Feature | `State`, `Parent`, `Iteration`, `Tags`, `Start Date`, `Closed Date`, `Predecessors`, `Source`, `Entry criteria` |
| Release | `Status`, `Start Date`, `Finish Date` ([releases/\_structure.md](../releases/_structure.md)) |

Anything else a page used to carry in its status line — the releases it spans,
its decisions, its design — goes in a plain line under the table.

### States

| State | Means |
| -- | -- |
| `New` | Agreed, not started. With no `Iteration` and no tag, its stories or design are not settled yet. Tagged `deferred`, it is not scheduled and carries `Entry criteria`. With an `Iteration`, its stories are written and it is on a release. |
| `Active` | At least one story started. Carries `Start Date`; a feature also carries `Iteration`. |
| `Closed` | Every story's acceptance holds. Carries `Closed Date`; an epic also carries `Start Date`. Means implemented, not released. |
| `Removed` | Retired: no longer needed. Stays in place, with one line saying why. |

- A story carries one line, `**State:** New`, `Active`, `Closed (<date>)` or
  `Removed`, and may add `· **Depends on:** <IDs>` after it. A story in a
  deferred feature or epic is `New`.
- A feature's `Iteration` is the only place its release is recorded. The release
  page's Scope table is derived from it.
- An epic's feature table has a `State` column, and each row's `State` equals
  its feature's own.
- `Entry criteria` is present exactly when `Tags` includes `deferred`.

### The board

`index.md`'s Releases and Backlog sections and each release page's Scope table
are derived regions. `task docs:generate` writes them from the epic, feature and
release pages, and `task lint` fails when one is stale or a metadata table
breaks the rules above. Never edit inside their fences.

### File templates

An epic, `epics/E<n>-<slug>/index.md`:

```markdown
# E<n> — <Title>

| | |
| -- | -- |
| **State** | New |

<one paragraph: the epic's scope>

| Feature | Scope | State |
| -- | -- | -- |
| [F<n>.<m> — <Title>](F<n>.<m>-<slug>.md) | <what it delivers> | New |
```

A feature, `epics/E<n>-<slug>/F<n>.<m>-<slug>.md`:

```markdown
# F<n>.<m> — <Title>

| | |
| -- | -- |
| **State** | New |
| **Parent** | [E<n>](index.md) |
| **Iteration** | [Release <r>](../../../releases/release-<r>/index.md) |
| **Predecessors** | — |

<one paragraph: what the feature delivers>

## S<n>.<m>.1 — <Title>

**State:** New

**Acceptance:**

- <an observable result>

## Acceptance

<the feature's acceptance block, when it has two or more stories>
```

An epic design, `epics/E<n>-<slug>/design.md`, opens with what it covers and the
feature that settles it into ADRs and implementation. Nothing in it is decided
until it is.

## Naming

- `epics/E<n>-<slug>/` directories; feature files `F<n>.<m>-<slug>.md`.
- IDs are permanent: never renumber; a moved story keeps its ID. Gaps are fine.
  Retired work keeps its ID as `Removed`, and the ID is never reused.

## Changing this area

**Parking an idea:** add a row to `ideas.md`, and a section linked from the row
if it needs more than a line. Do not elaborate an idea unless the owner asks. A
dropped idea is deleted.

**Adding an epic or a feature:**

1. Take the next free ID. Never renumber a sibling. An idea promoted from
   `ideas.md` carries its section into the new file, and its row is deleted.
1. Create `epics/E<n>-<slug>/index.md`, `State` `New`; tag it `deferred`, with
   `Entry criteria`, when it is not scheduled.
1. Write one feature file per feature, stories inline. Give a story its own file
   only when its acceptance runs past about a screen.
1. Put design at the lowest level that fits: the feature's `## Design`; the
   epic's `design.md` when it spans features; a link to `architecture/` when
   it describes current behaviour.
1. Run `task docs:generate`.

**Writing acceptance:**

- Each line is an observable result, and the tests that prove a story belong in
  its acceptance, not in a story of their own.
- A decision still to be made, by comparing options or measuring, is its own
  story, so other work can depend on the decision without depending on its
  implementation. Accepting an ADR already written is not a story: its
  `**Status:**` line records it, and the features that need it name it under
  `Predecessors`.
- A feature with several stories has a `## Acceptance` block that exercises
  every story, each line tagged with the story it proves; a one-story feature
  keeps its acceptance on the story. What cannot be scripted, such as an
  approval, is listed under the block.
- The block fails loudly: `set -euo pipefail`, never `|| echo`, and negative
  checks through these helpers rather than a bare `! cmd`, which `set -e`
  ignores:

```bash
absent() { local rc=0; rg -q --hidden --glob '!.git' "$@" </dev/null || rc=$?; [ "$rc" -eq 1 ]; }
fails_with() { local out rc=0; out=$("${@:2}" 2>&1) || rc=$?; [ "$rc" -ne 0 ] && grep -qF -- "$1" <<<"$out"; }
```

**Checking removed behaviour:** a check that a removed symbol is gone asks "does
any current page describe it as present?", not "does the name appear?". A page
may name removed behaviour to say it is gone.

**Working on and closing out work:**

1. Starting: set the feature, and its epic, to `Active` with a `Start Date`, and
   give the feature its `Iteration`.
1. A story is `Closed (<date>)` when its acceptance holds; run the feature's
   acceptance block, then flip the story's state.
1. When every story is closed, the feature is `Closed` with its `Closed Date`;
   its `Iteration` stays. When every feature is closed, the epic is `Closed`
   with its `Closed Date` and the acceptance as run. Closed work is never
   deleted.
1. An answered open question becomes an ADR, or a rejected option recorded on
   the feature under *Considered and rejected*; the question is then removed.
1. Run `task docs:generate` after every state or `Iteration` change.

**Deferred work:** do not start or elaborate work tagged `deferred` unless the
owner asks. When its entry criteria hold, drop the tag and the `Entry criteria`
row, and give it an `Iteration` once it has a release. Nothing renumbers.

**Retiring work:** a story, feature or epic no longer needed becomes `Removed`
in place, with one line saying why.

## Tracker mapping

| Here | Azure DevOps |
| -- | -- |
| Epic, feature, story | Epic, Feature, User Story, linked by `Parent` |
| `E<n>`, `F<n>.<m>`, `S<n>.<m>.<k>` | the work item title's prefix |
| `State` | `State`; ADO's `Resolved` is unused |
| `Iteration` | Iteration Path |
| `Tags` | Tags |
| `Predecessors` | Predecessor links |
| `Entry criteria`, `Source` | custom fields |
| `**Acceptance:**` | Acceptance Criteria |
| A commit subject naming an ID | an `AB#<id>` link |
| `design.md`, ADRs, release pages, `ideas.md` | stay in the repository |

## Other repositories

- Every acceptance line is checkable inside this repository. When acceptance
  needs a host, such as an application or a library workspace, a test builds
  one in a temporary directory.
- A dependency on another repository's software is a version or git pin in the
  manifest of the code that uses it, plus at most an entry criterion that can
  be observed from outside that repository ("its release-1 tags exist").
- Another repository's pages, paths, spec IDs and internal status are not cited
  or restated. A requirement or finding that came from elsewhere is written
  here in full, as this repository's own.
- No page here is written for another repository to cite.
````

### `docs/releases/_structure.md`

Replaces the seed of the same path.

````markdown
# releases/ — what belongs here

## Belongs here

- One page per release, `release-<n>/index.md`: its metadata table, then these
  sections in this order:
    - **Entry criteria**: what must hold before work on the release starts.
    - **Scope**: the derived Scope table, then, when there is any, a
      `### Done before this release` table: done epics that predate the story
      taxonomy, and other done work the release carries — epic, what it
      delivered, and its closed dates. That table is kept by hand.
    - **Decisions**: each ADR the release added or updated, linked, with one line
      on what changed.
    - **Breaking changes**: what a consumer must change on upgrading, or `None`.
    - **Progress**: a few lines on what is next and what blocks it.
    - **Commits**: the `git log --grep` command that lists commits naming a scope
      ID, and its output, refreshed at least at the cut.
    - **Exit criteria**: what must hold for the release to ship.
    - **Shipped**: once shipped, the release evidence — each version and tag, its
      commit, and what was checked.
- `index.md`, listing every release newest first, each linked, with its status.

## Does not belong here

| Instead of | Put it in |
| -- | -- |
| A story's text, acceptance, design or state | its feature under `specs/` |
| Which features a release carries | each feature's `Iteration`; the Scope table is derived from it |
| Why a choice was made | an ADR under `adr/` |
| How to run a release | `runbooks/` |

## Metadata and scope

A release page opens like this:

```markdown
# Release <n> — <Title>

| | |
| -- | -- |
| **Status** | planned |

<one paragraph: what the release carries>

## Entry criteria

- <what must hold before work starts>

## Scope

<!-- BEGIN derived scope -->

| Feature | Epic | State |
| -- | -- | -- |

<!-- END derived scope -->
```

- `Status` is `planned`, `in progress` or `shipped`. A release closes on scope,
  not on a date, so it keeps its own word rather than a work-item `State`.
- `Start Date` is optional. `Finish Date` is present exactly when `Status` is
  `shipped`.
- The Scope region lists every feature whose `Iteration` names this release.
  `task docs:generate` writes it; never edit inside its fence.
- Commit subjects name the story or feature IDs they deliver, so the Commits
  section can be regenerated.

## Tracker mapping

| Here | Azure DevOps |
| -- | -- |
| `release-<n>` and its title | an Iteration under the Iteration Path |
| `Start Date`, `Finish Date` | the Iteration's dates |
| `Status` | no field: ADO derives past, current and future from dates |
| The Scope table | an iteration query |
| The other sections | stay in the repository |

## Changing this area

1. Cut a release page when there is scope to put on it, not ahead of time.
1. Fill the sections above, and list it in `index.md`, newest first.
1. Put a feature on it by setting the feature's `Iteration`; take it off by
   clearing it. Then run `task docs:generate`.

A release is `shipped`, with its `Finish Date`, once its exit criteria hold.
````

### `docs/specs/index.md`

Replaces the seed of the same path. Its board body is exactly `render_board` of
an empty tree.

```markdown
# Specs

What this repo is made of and what is left to build. **Start here:** the board
says what is next; the epic says how; its ADRs say why. The Releases and Backlog
sections below are derived from the epic, feature and release pages by
`task docs:generate`; never edit inside their fence.

<!-- BEGIN derived board -->

## Releases

| Release | Status | Features |
| -- | -- | -- |

## Backlog

Every feature is on a release or Removed.

<!-- END derived board -->

Ideas not yet agreed as work are parked in the [ideas list](ideas.md).

## Conventions

- **Taxonomy.** Epic `E<n>` → feature `F<n>.<m>` → story `S<n>.<m>.<k>`. The
  prefix chain locates a bare ID without a lookup. IDs are permanent: a moved
  story keeps its ID, and gaps are fine.
- **Every piece of work is an epic**, closed work included. There is no build
  log.
- **State lives on the work.** Epics and features carry `State` in a metadata
  table, stories on a `**State:**` line: `New`, `Active`, `Closed` or
  `Removed`. The board above is derived from them, never a second copy.
- **A feature's `Iteration` is its release.** A release page's Scope table is
  derived from it, so moving a feature edits only the feature.
- **A story is closed when its acceptance holds.** Each story carries an
  `**Acceptance:**` list of observable results, and the tests that prove it
  belong in that list.
- **A feature states its predecessors and its acceptance**: a `Predecessors`
  row, and, when it has several stories, a `## Acceptance` block that
  exercises every story and fails loudly.
- **Ideas are a parking lot.** An idea not yet agreed as work is a row in
  `ideas.md`, with no ID and no state. Agreed work that is not ready is tagged
  `deferred`, with entry criteria.
- **Design lives with the work** — a `## Design` section on the feature, or the
  epic's `design.md`. Current behaviour belongs in
  [architecture](../architecture/index.md).
- **Decisions are ADRs**, one file per topic, revised in place with a dated line
  under `## Background` when they change — see [the log](../adr/index.md).
- **Open questions live on the feature or epic they block.** Answered, a
  question becomes an ADR or a rejected option recorded on the feature, and
  leaves the page.
```

### `docs/specs/ideas.md`

New seed.

```markdown
# Ideas

Ideas not yet agreed as this repository's work. An entry takes no ID and no
state, and does not authorize starting anything. Promoting one moves its section
into a new epic or feature and deletes its row; a dropped idea's row is deleted
too.

[Back to the specs](index.md)

| Idea | Summary | Source |
| -- | -- | -- |
```

### `docs/reference/_structure.md`

New seed.

```markdown
# reference/ — what belongs here

## Belongs here

`index.md`, which links to the generated API reference, to any component catalog
the repository builds, and to each entry point's `README.md`. Pages the
repository's reference tools generate into this area.

## Does not belong here

| Instead of | Put it in |
| -- | -- |
| Hand-written API descriptions | the entry point's `README.md`, or its doc comments, which the API reference renders |
| How the site is built | `architecture/` |
| How to use what the repo builds | `guides/` |
```

### `docs/reference/index.md`

New seed.

```markdown
# Reference

Generated reference. Exact signatures come from doc comments, which the API
reference renders; how to use one entry point lives in that entry point's
`README.md`.
```

### `docs/_structure.md`

Three replacements in the seed as S13.1.1 leaves it; nothing else changes:

1. In *Where new material goes*, `` → a row in `specs/backlog.md`. `` becomes
   `` → a row in `specs/ideas.md`. ``

1. At the end of *Checks*, add this paragraph:

    ```markdown
    `kiln doctor --only docs-generate` checks that the derived regions — the nav,
    the spec board and each release's Scope table — are current, and that every
    epic, feature and release page's metadata table follows
    `specs/_structure.md`.
    ```

1. In *Keeping it honest*, delete the first three bullets (a release naming a
   missing feature; a feature's status differing from its release row; an
   epic's status contradicting its features) and put this bullet first:

    ```markdown
    - A derived region edited by hand: `task lint` fails, and `task docs:generate`
      overwrites it.
    ```

## One site per repository

[ADR-0012](../../../adr/ADR-0012.md) applies the MkDocs site to every language.
For a repository whose language has native reference tools, the docs build works
like this:

1. `mkdocs build --strict` builds the site into a staging directory.
1. Each native tool writes its static site under it: Compodoc to `api/<lib>/`,
   Storybook to `storybook/`, Javadoc to `api/`.
1. A check confirms that each entry point (`index.html`) exists.
1. The staging directory is published.

`reference/index.md` links to each assembled site. Nothing in E13 builds this.
The Node half belongs to [E9](../E9-node-archetypes/index.md), and a Java
archetype is an idea (S13.3.2 parks it in `ideas.md`).

## Considered and rejected

- **A repository-owned nav, checked for reachability.** See
  [ADR-0003](../../../adr/ADR-0003.md#alternatives-considered).
- **Seed the board script as a file.** See
  [ADR-0011](../../../adr/ADR-0011.md#alternatives-considered).
- **New ownership kind in `rn-forge-tooling`'s `ArtifactKind`.** It would need a
  pykit release before kiln could build anything. A derived region is not an
  artifact at all, so apply needs no new kind.
- **Keep the source model's `<!-- board:start -->` markers.** kiln already has a
  fence helper, and one marker style keeps every fenced region recognisable. A
  repository that adopts kiln changes its markers once.
