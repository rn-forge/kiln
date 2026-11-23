# Specs

What kiln is made of and what is left to build. Read this before adding an epic,
starting a feature, or cutting a release. **Start here in a new session:** the
board says what is next; the epic says how; its ADRs say why. The Releases and
Backlog sections below are derived from the epic, feature and release pages by
`task docs:generate`; never edit inside their fence.

<!-- BEGIN derived board -->

## Releases

| Release | Status | Features |
| -- | -- | -- |
| [Release 2 — repositories on kiln's `main`](../releases/release-2/index.md) | planned | 2 New · 1 Closed · 1 Removed |
| [Release 1 — kiln generates and self-hosts the Python and web archetypes](../releases/release-1/index.md) | in progress | 1 Active · 95 Closed |
| [Release 0 — the canon and the hand-authored goldens](../releases/release-0/index.md) | shipped (2026-09-12) | — |

## Backlog

Features with no Iteration, by State and epic.

### Deferred

| Epic | Features | Entry criteria |
| -- | -- | -- |
| [E5 — The web archetypes](epics/E5-web-archetypes/index.md) | [F5.4](epics/E5-web-archetypes/F5.4-django-scaffold.md) | Per feature; see the epic. |
| [E7 — pykit releases, and the pin flip](epics/E7-pykit-release-pin-flip/index.md) | [F7.9](epics/E7-pykit-release-pin-flip/F7.9-repos-follow-main.md) | Per feature; see the epic. |
| [E8 — The Azure DevOps CI provider](epics/E8-ado-provider/index.md) | — | a repo needs `ci.provider = "ado"`. The intellibuild plan holds the question of whether intellibuild is that repo |
| [E10 — kiln generators](epics/E10-kiln-generators/index.md) | — | release-1 has shipped and the owner picks this up for elaboration |
| [E18 — kiln simplification](epics/E18-kiln-simplification/index.md) | [F18.3](epics/E18-kiln-simplification/F18.3-area-epics.md), [F18.4](epics/E18-kiln-simplification/F18.4-one-commit-on-main.md) | Per feature; see the epic. |

<!-- END derived board -->

Ideas not yet agreed as work are parked in the [ideas list](ideas/index.md).

Every epic, by number, is on [the epic list](epics/index.md).

## Upstream pins

What kiln needs from other repositories, stated as what kiln can observe from
outside them ([ADR-0009](../adr/ADR-0009.md)). Their own plans and status are
theirs.

| Pin | Needed by | Observed |
| -- | -- | -- |
| Every pykit package kiln renders resolves from its git source outside the pykit workspace | [E5](epics/E5-web-archetypes/index.md): `uv sync` of any web cell | yes (2026-10-04): both web cells sync and validate against pykit `main` `cba6d84` and kiln `feature/v1`. At tags (2026-10-16) they do not, until [S7.1.2](epics/E7-pykit-release-pin-flip/F7.1-tag-pins.md#s712-application-roots-resolve-pykit-without-its-workspace-sources): pykit's workspace sources resolve per tag |
| pykit's release-1 tags exist | [E7](epics/E7-pykit-release-pin-flip/index.md) | yes (2026-10-14): `rn-forge-commons-v0.5.0`, `rn-forge-cli-v0.1.0`, `rn-forge-tooling-v0.2.0` and the web packages, released from pykit `main` `79bb296`. pykit Release 4 (2026-10-16) added `rn-forge-commons-v0.6.0`, `rn-forge-data-v0.1.0`, `rn-forge-django-v0.5.0` and `rn-forge-fastapi-v0.3.0`; kiln's pins stay ([F7.1](epics/E7-pykit-release-pin-flip/F7.1-tag-pins.md)) |
| pykit publishes the workspace planner as the `rn-forge-devops` console script ([ADR-0014](../adr/ADR-0014.md)) | [F6.4](epics/E6-rebuild-the-repos/F6.4-workspace-pipeline.md): `task ci:plan` in a library workspace | yes (2026-10-16): `rn-forge-devops-v0.1.0`, released from pykit `4dadf2b`; `uvx` runs it from the tag outside the workspace; no longer needed (ADR-0017, F6.7) |
| `rn-forge-devops plan` emits a no-extras smoke entry for every selected package ([ADR-0016](../adr/ADR-0016.md)); pykit writes the story and releases a new `rn-forge-devops` tag | [S6.4.7](epics/E6-rebuild-the-repos/F6.4-workspace-pipeline.md#s647-release-publishes-from-the-default-branch-after-the-quality-gate): `smoke` covers a pull request once release stops running there | yes (2026-10-19): `rn-forge-devops-v0.2.0`, released from pykit `4770dc6`; no longer needed (ADR-0017, F6.7) |
| pykit tags `rn-forge-commons` 0.7.0 and `rn-forge-tooling` 0.3.0, with every package that depends on them re-tagged on those pins, so they resolve together | [F7.3](epics/E7-pykit-release-pin-flip/F7.3-adopt-pykit-extraction.md): every story | yes (2026-10-25): pykit's Release 6, from pykit `main` `9557668`: `rn-forge-commons-v0.7.0` and `rn-forge-tooling-v0.3.0`, with `cli-v0.1.1`, `data-v0.1.1`, `web-v0.2.1`, `django-v0.5.1`, `fastapi-v0.3.2`, `sqlalchemy-v0.2.1` re-tagged on commons 0.7. `rn-forge-devops-v0.3.0` came in the same release; it does not depend on commons |
| pykit's `main.yml` uploads to PyPI by trusted publishing, with a TestPyPI dry run and changelog release notes (pykit F21.3) | [F7.6](epics/E7-pykit-release-pin-flip/F7.6-release-to-pypi.md): the behaviour kiln renders | yes (2026-10-30): pykit's Release 7, `main.yml` at pykit `a038a0d`. It also signs PEP 740 attestations (pykit S21.3.5), which [F6.8](epics/E6-rebuild-the-repos/F6.8-pykit-release-7-ci.md) takes |
| Every `rn-forge-*` package kiln renders is on pypi.org (pykit S21.3.3) | [F7.5](epics/E7-pykit-release-pin-flip/F7.5-pykit-from-pypi.md): every story | yes (2026-10-30): ten packages, pykit's Release 7. Each package's Release 7 version is its first on pypi.org, so kiln's floors move with it (S7.5.6) |
| pykit tags `rn-forge-commons` 0.9.0, with `ManagedBlock.end_indent` (pykit S18.6.1) and the release prepared by pykit S18.6.2, and it is on pypi.org | [F19.2](epics/E19-formatting-standard/F19.2-nav-block-end-indent.md): S19.2.1 | yes (2026-11-16): `rn-forge-commons` 0.9.0 is pypi.org's current release |
| pykit's `install` takes `--ref` (a branch, tag or commit, no GitHub release), records `ref` and `commit` in `state.json`, and ships a Python-tool product whose build puts a runnable `bin/<tool>` in the version directory (pykit F23.2), released to pypi.org in `rn-forge-tooling` | [F7.7](epics/E7-pykit-release-pin-flip/F7.7-kiln-installs-as-a-tool.md): S7.7.1 | yes (2026-11-18): `rn-forge-tooling` 0.3.3 is pypi.org's current release, from pykit's Release 9 (PR #36, pykit `dc5336e`) |
| pykit's `--help` shows `[...]` literally and no docstring `Args:`/`Raises:` sections, and a CLI starts with no logger notice and one millisecond field (pykit F23.1), released to pypi.org | [F7.7](epics/E7-pykit-release-pin-flip/F7.7-kiln-installs-as-a-tool.md): S7.7.4 | yes (2026-11-18): `rn-forge-cli` 0.2.0 (help text) and `rn-forge-commons` 0.10.0 (logger notice, millisecond field) are pypi.org's current releases, from pykit's Release 9 (PR #36, pykit `dc5336e`) |
| pykit's `install` writes the rn-forge home's `env.sh`, and `PythonTool` links `completions/_<tool>` by default (pykit F28.1, [pykit ADR-0017](https://github.com/rn-forge/pykit/blob/main/docs/adr/ADR-0017.md)), released to pypi.org as `rn-forge-tooling` 0.4.0 | [F7.10](epics/E7-pykit-release-pin-flip/F7.10-shell-completion.md): S7.10.1 | yes (2026-11-20): `rn-forge-tooling` 0.4.0 is pypi.org's current release, from pykit's Release 11 (PR #41, pykit `7b63ef85`) |

## Order

```text
done:  E1 ─→ E2 ─→ E3 ─→ F4.1 ─→ F4.2 ─→ S4.3.1–S4.3.5 ─→ S4.5.1–S4.5.6
done:  F5.1 ─→ F5.2 fastapi ─→ S5.2.4 frontend module ─→ S4.5.9 staged `new` ─→ S5.3.1 fresh-repo gate fixes ─→ S5.3.5 quality commands ─→ S5.3.6 setup experience
done:  S4.4.1 matrix ─→ S5.3.7 README ─→ S5.3.2 ─→ S5.3.3 ─→ F5.3 shipped cells (S5.3.4 moved to S16.5.3)
       (Django deferred: F5.4)
now:   ADRs accepted ─→ S13.1.1 derived nav ─→ F13.2 board/scope ─→ F13.3 adopt the model
       F11.1 checks ─→ F11.2 python-lib package sites ─→ F11.3 generate package   (S11.4.2 after S13.3.1)
       S12.1.1 accept ─→ F12.1 baseline ─→ F12.2 web records (F5.5 client before S12.2.5)
       F4.4 rest (S4.4.3 approval; S4.4.7–S4.4.9 goldens leave git) ──┐
       S5.3.1 + F11.1–F11.3 ─→ S6.1.1 python-lib hosts pykit          │
       S4.5.3–S4.5.7 ─→ F4.6 doctor ──────────────────────────────────┼─→ F4.8 self-host
       F4.7 contracts ────────────────────────────────────────────────┘
       F7.1 tag pins
       F4.12 task files by owner (after F4.11; before F9.1's stories and the release-1 tag)
       F9.1 node-lib CI ─→ F9.2 one node scaffold ─→ F9.3 node CI holds ─→ S9.1.12 re-label and approval ─→ S9.1.6
       F6.3 CI hardening (after F4.4) ─→ F6.4 workspace pipeline (after F6.1; planner pin met) ─→ S6.4.6 · S6.4.7 · F11.5 package-site deploy
       F7.5 pykit from PyPI ─→ S6.4.5 and F6.7 reruns ─→ F6.8 pykit Release 7 CI ─→ F7.2 the cut
       F6.9 adopted repositories left alone (pykit's 2026-11-01 trial) ─→ F7.2 the cut
       E15 CI standard (F15.1 ─→ F15.2–F15.7 · F15.8 owner decision) ─┐
       E16 init adopts by overwrite (F16.2 · F16.1 ─→ F16.3 · F16.4 ─→ F16.8 retire init ─→ F16.9 ─→ F16.10 agent instructions) ─┤
       E17 task standard (F17.1 · F17.2 · F17.3 a faster gate) ─────────┤
       E19 formatting standard (F19.1: S19.1.1 spike ─→ S19.1.2 clean templates ─→ S19.1.3 tasks ─→ S19.1.4 self-host) ─┴─→ release 1 ships (owner) ─→ F7.9 repositories follow main
triggered: E7 pykit tags · E8 ADO · backlog: E10 generators
```

E3 shipped on 2026-09-15: every feature's acceptance block passes, S3.3.2's
normalized golden diff was reviewed, and the epic block re-proves the whole. E4
is under way. **Build order is not release order:** E5's first two features and
S5.3.1 were built before F4.4, because the owner's next repositories are web
repositories and those stories need neither the render matrix, the full doctor
nor self-hosting; E5 ships in release-1. The **Depends on** column on each epic
and line on each feature are normative; this diagram summarizes them. Nothing in
E4 waits on a pykit release ([E7](epics/E7-pykit-release-pin-flip/index.md)):
the rn-forge dependency source is one constant
([S4.3.7](epics/E4-generator/F4.3-concern-modules.md#s437-the-scaffold-completes-pyprojecttoml)),
so flipping to tags later is a one-line change, not a template change.

## Building a story

One story per session, from a fresh context. The story is the whole brief;
nothing outside it and the files it names is assumed. This is written for
whoever builds the story — a person, or an agent of any size.

1. Read `README.md`, then this page's conventions, then the feature page top to
   bottom. Read every file the story's **Build** list names, and every golden
   file it says to diff — with `diff`, never by eye. Read the tests of the
   nearest `done` story in the same feature: they are the shape to copy.
1. Write the tests first, in the file the story names, each named for the
   behaviour it proves, `test_<subject>_<behaviour>`, with no spec ID in its
   name, docstring or comments. Every acceptance item a script can check is a
   test, so `task validate` is the whole scripted check. An item no script can
   check is listed as not scriptable, with who judges it.
1. Build exactly what the **Build** list says. Where it names a file, a
   function, a constant, a code, a template or a context key, use that name
   verbatim. Where it is silent, do the simplest thing that makes the tests
   pass, and write the choice down.
1. Do not: edit a golden repo unless the story says so; add a dependency; change
   another module; change the module contract; shell out from anything but a
   `scaffold` function; add a check, a flag, an option or a config key the
   story does not list; skip a test the story does not allow to skip.
1. Run `task validate`. It passes, with no failure and no skip the story did not
   allow. If a golden had to change, re-seed its `state.json` as `README.md`
   says. Paste the tail of `task validate` into the story's *What the build
   settled* block.
1. Record under the story, as *What the build settled that the story did not
   say*, every choice from step 3 and every place the build had to depart from
   the list — and flip its **State** to `Closed (<date>)`. Leave the feature's
   `## Acceptance` block for the owner, who judges only what a script cannot.
1. Commit nothing. The owner reviews the diff and the tests, runs the acceptance
   block, and commits.

## Conventions

- **Taxonomy.** Epic `E<n>` → feature `F<n>.<m>` → story `S<n>.<m>.<k>`. The
  prefix chain locates a bare ID without a lookup. IDs are permanent once a
  commit names them or work starts; a `New` item no commit names takes its new
  parent's next ID when it moves. Gaps are fine.
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
  row, and, when it has several stories, a `## Acceptance` block. The block
  holds only what needs the owner's judgement, such as reading rendered prose;
  it never holds a shell script, because every scripted check is a story's
  test and `task validate` runs them. Fenced command blocks anywhere in the
  specs carry no column-aligned comments: a comment goes on its own line above
  the command, where `task format` cannot leave it misaligned. The acceptance
  blocks of closed features keep their text. The owner has accepted F16.8 to
  F16.10 as they stand.
- **Ideas are a parking lot.** An idea not yet agreed as work is a row in
  `ideas/index.md`, with no ID and no state, and a page beside it when the row
  is not enough. Agreed work that is not ready is tagged `deferred`, with
  entry criteria.
- **Design lives with the work** — a `## Design` section on the feature, or the
  epic's `design.md`. Current behaviour belongs in
  [architecture](../architecture/index.md).
- **Decisions are ADRs**, one file per topic, revised in place with a dated line
  under `## Background` when they change — see [the log](../adr/index.md).
- **Open questions live on the feature or epic they block.** Answered, a
  question becomes an ADR or a rejected option recorded on the feature, and
  leaves the page.
- **Why things are the way they are** is the decision log
  ([ADR index](../adr/index.md)) and git history. The planning record that was
  `docs/plans/` was retired on 2026-11-17 and survives in git history.
