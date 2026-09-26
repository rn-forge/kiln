# pykit docs alignment — standalone plan

**Date:** 2026-09-26 · **Status:** proposed; the owner answered R1, R2's package
navs and R7 on 2026-09-26 and decides the rest; the accepted ones become an epic

The goal is one `docs/` structure and one content approach across every rn-forge
repository. pykit adopted kiln's docs model on 2026-09-26 (pykit ADR-0007).
Where pykit's structure turned out better, the standard should change here
rather than pykit diverging. This plan says what that means for kiln: which
parts of the standard to extend, which checks to fix, and which kiln pages now
say something untrue about pykit.

It is a plan, not work: kiln's rule is that work lives in an epic. Each
recommendation below ends with the change it would make, so the accepted ones
can be turned into features directly.

## What was measured

kiln's docs-structure checker (`check_structure` with kiln's `POLICY`) was run
directly against pykit's tree on 2026-09-26. `kiln doctor` itself refuses to run
there, because pykit has no `.rn-forge/kiln/config.toml` yet; that is expected
until [F6.1](../specs/epics/E6-rebuild-the-repos/F6.1-pykit-skeleton.md).

| Check | Result |
| -- | -- |
| Areas: each declared area has `index.md` and `_structure.md` | clean |
| Naming: kebab pages, `ADR-<nnnn>.md`, `release-<n>/`, `E<n>-…/F<n>.<m>-….md` | clean |
| ADR `**Status:**` lines | clean |
| Instruction pointer: `CLAUDE.md` links `docs/_structure.md` and `docs/index.md` | clean |
| Links and anchors | 40 findings |

The 40 link findings fall into three groups:

- **25 are links from pykit's root site into its package sites**, such as
  `docs/index.md` → `rn-forge-web/index.md`. MkDocs resolves them, and pykit's
  strict build passes; kiln's checker reads them as plain file paths and
  cannot.
- **14 are in `docs/plans/archive/` and `docs/plans/reviews/`**, which pykit's
  `mkdocs.yml` excludes from the site. kiln checks them anyway.
- **1 is in a pykit page that is being deleted.**

So pykit already conforms to the standard everywhere the standard has an
opinion. Every gap is in something the standard does not model yet: a library
workspace whose packages each have their own docs site.

## Recommendations

| ID | Recommendation | Recommended option |
| -- | -- | -- |
| R1 | How a Python monorepo lays out its docs | Per-package sites, included into a root site (pykit's layout); **answered** |
| R2 | How package sites get into the root nav | A new `include` area kind in `_areas.yml` |
| R3 | How links into package sites are checked | Resolve them the way MkDocs does |
| R4 | Which pages the checks cover | Only pages MkDocs ships: honor `exclude_docs` |
| R5 | What is checked inside a package's docs | A small fixed shape: `index.md`, `guides/`, `reference/` |
| R6 | How specs treat another repository | Acceptance is checkable inside the repo; another repo is a pin, not a tracked story |
| R7 | Published or internal packages | The archetype decides: `python-lib` packages are published one by one, every other archetype's are internal; **answered** |

### R1 — The `python-lib` docs layout

**Today.** The standard gives `python-lib` one root site. `kiln new` writes one
`mkdocs.yml` whose mkdocstrings `paths` list every `packages/<pkg>/src`, so all
packages' API reference lands in the root `reference/` area. Nothing is said
about docs inside a package.

**pykit.** Each package has its own `packages/<pkg>/docs/` (`index.md`,
`guides/`, a generated `reference/`) and its own `mkdocs.yml`, and builds as a
standalone site. The root `mkdocs.yml` uses `mkdocs-monorepo-plugin` to include
all seven under a "Packages" nav section. The root `docs/` holds only
cross-package material: architecture, guides for choosing and combining
packages, runbooks, releases, specs, ADRs and plans.

| Option | For | Against |
| -- | -- | -- |
| (a) One root site, as today | One nav, one build, no plugin | Packages are published and versioned independently, but their docs are not; a package's guide can silently link into another package; the root `guides/` mixes "use this package" with "combine packages" |
| (b) Per-package docs, one site, no standalone builds | Package docs live beside the code | Loses the isolation check, which is the main reason to split |
| **(c) Per-package sites, included into a root site** | Each package's docs travel with it; a standalone strict build fails on any cross-package link, so every package's docs stand on their own; the root stays for cross-package material | Adds `mkdocs-monorepo-plugin`; `docs:build` builds N+1 sites; the nav and link checks must learn the layout (R2, R3) |

**Recommended: (c).** A `python-lib` exists to publish packages independently,
and pykit's experience is that per-package docs catch the drift (c) is designed
to catch: pykit's own instructions rely on the standalone builds to reject
cross-package links. The costs all land in kiln's tooling, once, rather than in
every library repository.

**Change.** In `reference/standard-repo.md`, the `python-lib` archetype gains a
docs section describing the package layer. `kiln new --archetype python-lib`
seeds, per package, `packages/<pkg>/mkdocs.yml` and a docs skeleton; the root
`mkdocs.yml` template adds the `monorepo` plugin; the docs dependency group adds
`mkdocs-monorepo-plugin`; and `tasks/docs.yml`'s `docs:build` builds the root
site and each package site with `--strict`. The root keeps listing every
package's `src` in mkdocstrings `paths`, because included pages render in the
root build.

**Owner answer, 2026-09-26: (c), for every Python monorepo.** The package docs
layer applies wherever kiln scaffolds workspace packages, not only to
`python-lib`. The root site always includes every package and is built from the
branch it is deployed from, so anyone browsing the repository can reach every
package; it makes no claim about a released version. Whether a package also gets
its own published, versioned site depends on whether it is published at all,
which the archetype decides (R7). pykit recorded its side as pykit ADR-0009.

### R2 — Package sites in the generated nav

**Today.** `build_nav` renders `Home` plus one entry per area in `_areas.yml`,
and `Area.nav` is `children` or `index-only`. A repository cannot add the
package includes without editing inside the generated block, which `docs-nav`
then reports as stale.

**Recommended.** Add a third nav kind, `include`, for an area that is not a
directory under `docs/`:

```yaml
- key: packages
  title: Packages
  nav: include
```

`build_nav` renders it as one entry per package, in `config.packages` order,
each `'!include packages/<pkg>/mkdocs.yml'`. `_check_areas` skips the directory,
`index.md` and `_structure.md` requirements for an `include` area. The package
list comes from `config.packages`, so adding a package to the config is the only
step.

**Owner answer, 2026-09-26: kiln seeds every `mkdocs.yml`, then the repository
owns it.** The root file keeps the standard's existing model: a repo-owned body
and one kiln-managed `# BEGIN generated nav` block, because the root nav comes
from `_areas.yml` and now the package list. A package's `mkdocs.yml` is seeded
once by `kiln new` (or, later, `kiln generate package`) and has no managed
block: package navs are curated per package, such as pykit's nested reference
sections, and a generator would fight them. `kiln doctor` never compares a
`mkdocs.yml` body with a template. It reads each package's nav only to run the
missing-page and orphan checks `Site` already runs for the root, so every page
stays reachable, and `docs:build --strict` over every site catches a broken
plugin or extension setting.

### R3 — Links into package sites

**Today.** Both link checkers (`structure._check_links` and `Site.check_links`)
resolve a link against the linking file's directory. A root page's link to
`rn-forge-web/index.md` is a MkDocs virtual path: the monorepo plugin mounts an
included site under its `site_name`. The checkers report it as broken.

**Recommended.** When the root `mkdocs.yml` includes package sites, build a map
from each included config's `site_name` to its `docs_dir`, and resolve a root
link whose first path segment is a mapped `site_name` into that package's docs.
Anchors are checked the same way.

Inside a package's docs, the rule is the reverse: a link that leaves the
package's `docs/` is an error, even when it resolves on disk. That is the check
pykit's standalone builds perform today, moved into kiln so it runs in
`kiln doctor` without a full build.

### R4 — Check only what ships

**Today.** The checks skip `_*.md` files and gitignored subtrees, and nothing
else. pykit excludes `plans/archive/` and `plans/reviews/` from its site with
`exclude_docs`, keeping them as unedited evidence, and kiln reports 14 broken
links inside them.

**Recommended.** Read `exclude_docs` from `mkdocs.yml` and skip matching pages
in the link, anchor and orphan checks. This matches kiln's own rule that a
frozen plan is never edited, even its links: a repository that keeps frozen
evidence should be able to take it out of the site instead of carrying findings
it is not allowed to fix.

### R5 — The package docs shape

**Recommended.** One rule, checked by `docs-structure` for every entry in
`config.packages`:

- `packages/<pkg>/docs/index.md` exists;
- `guides/` exists and holds kebab-case pages;
- `reference/` holds the mkdocstrings pages and is treated as generated;
- no governance area (`adr/`, `specs/`, `releases/`, `plans/`, `runbooks/`) sits
  inside a package: cross-package work and decisions belong at the root.

The rule is written once, in the seeded root `docs/_structure.md`, under a
"Package docs" heading. Packages get no `_structure.md` or `_areas.yml` of their
own; the shape is fixed, so there is nothing for a package to declare.

pykit already matches this shape: on 2026-09-26 its `api/` directories became
`reference/`, and web's `adoption/` pages moved into its `guides/`.

A published package (R7) adds three things to the shape, all checked:

- `packages/<pkg>/CHANGELOG.md` in Keep a Changelog form, and
  `docs/changelog.md`, which includes it with `pymdownx.snippets` and is in
  the package nav;
- `[project.urls]` naming `Documentation` (the package's `latest` site),
  `Source`, `Changelog` and `Issues`;
- a README with only absolute links, because it is the package's page on an
  index, where relative links break.

### R7 — Published or internal packages

A monorepo's packages are either published one by one (pykit's case) or
internal: built and versioned with the repository, never installed on their own.
The docs structure is the same for both. What differs is what CI publishes and
what a package's user needs.

**Owner answer, 2026-09-26: the archetype decides; there is no separate
switch.** `python-lib` exists to publish its packages independently, so every
package it lists in `[archetype.python-lib] packages` is published, each with
its own tag, changelog and versioned site. The application archetypes
(`python-app`, `python-tool`, `python-web-api`, `python-web-app`) hold internal
packages only, and their docs are brought together in the root site.

|  | Internal packages (application archetypes) | Published packages (`python-lib`) |
| -- | -- | -- |
| Package docs shape and standalone strict build (R5) | yes | yes |
| Root site includes every package, built from its branch (R2) | yes | yes |
| Changelog, `[project.urls]`, absolute-link README (R5) | no | yes |
| Per-package `<package>-v<version>` tag and GitHub Release | no | yes |
| Versioned package site at `<site>/packages/<pkg>/<major>.<minor>/` with `latest` | no | yes |

**How new packages get the structure.** `kiln new` seeds
`docs/runbooks/adding-a-package.md`, rendered for the archetype, beside the
"Package docs" section of `docs/_structure.md` (R5). `kiln doctor` checks every
entry in `config.packages` against the archetype's shape, and reports a
workspace member that `config.packages` does not list, so a package added by
hand cannot skip the structure. Rendering a new package is
`kiln generate package`, already scoped in
[E10](../specs/epics/E10-kiln-generators/index.md); it emits this same shape.

**CI.** The `python-lib` CI template gains pykit's docs deploy once pykit proves
it (pykit F9.9, S9.9.4): after the package jobs, one `docs` job builds the root
site, deploys each package tagged at the pushed commit with
`mike --deploy-prefix packages/<pkg>` to a `gh-pages` storage branch, and
uploads the root site plus that branch's `packages/` tree as the Pages artifact.
The application archetypes deploy the root site only. Uploading to a package
index is out of scope until pykit chooses one; it would be a `[ci]` setting
then.

**Change.** The standard page describes both package kinds per archetype;
`kiln new` seeds the runbook and, for `python-lib`, the changelog,
`[project.urls]` and the README links line; the R5 check covers the published
additions; the `python-lib` CI template gains the deploy job.

### R6 — Specs do not track another repository's work

pykit decided on 2026-09-26 (pykit ADR-0008) that it is accepted by its own
specs and tests. Downstream products are sources of requirements. When
acceptance needs a host application, a test scaffolds one in a temporary
directory. As part of the content standard, the same rule applies to every
repository, kiln included:

- Every acceptance line is checkable inside the repository that owns it.
- A dependency on another repository is a version pin, plus at most an entry
  criterion ("pykit has a release that includes X"). Another repository's
  stories, IDs and internal status are not restated.
- Nobody writes a handoff page in one repository for another to cite by path.
  Each repository's docs describe only itself.

**Change.** Add the rule to the seeded `specs/_structure.md` under "Writing
acceptance", and apply it to kiln's own pages, as listed next.

## Kiln pages that are now wrong about pykit

These pages describe pykit as it was before 2026-09-26. Under R6, most of them
should say less, not just be corrected.

| kiln page | What it says | What is true now | Proposed change |
| -- | -- | -- | -- |
| `specs/index.md`, "Upstream work owned by pykit" | pykit's handoff is `docs/plans/kiln-dependencies.md`, and the table lists pykit phases and features | The handoff page is deleted (its 2026-09-12 original stays in pykit's Git history at `12da7f3`). Pykit's internal pins now name `feature/upgrade` in its working tree, pending a push. The lifecycle row's "pykit ADR-0005" is now rule 3 of pykit ADR-0002. | Replace the table with the pins kiln needs, in kiln's terms: "pykit `feature/upgrade` resolves outside the workspace" (for E5) and "pykit release-1 tags exist" (for E7). |
| `specs/epics/E5-web-archetypes/index.md`, "Upstream" | Web, Django and FastAPI pin uncut tags; cli and tooling already pin `feature/upgrade` | Before 2026-09-26, cli and tooling also pinned an uncut tag. Now all seven packages pin `feature/upgrade`, once pushed. | Keep one sentence naming the pin; drop the pykit history. |
| `specs/epics/E7-pykit-release-pin-flip/index.md` | Entry: "the owner declares pykit stable"; scope item 1 cuts pykit's tags in the order commons → cli → tooling → web → django/fastapi, per pykit's commons plan D.8 | pykit cuts its own tags in its release-1, with all seven packages including `rn-forge-sqlalchemy`, and its CI will order package jobs by dependency. | Entry criterion: "pykit release-1's tags exist". Drop scope item 1; kiln's scope starts at tagging `rn-forge-kiln` and flipping pins. |
| `plans/context.md`, rows for §2.8, §2.9, §2.11, §3 and D55 | Point to "the pykit handoff" | The handoff is deleted. | Point to the text itself: `git show 12da7f3:docs/plans/kiln-dependencies.md` in pykit, plus pykit's tooling lifecycle guide for the current `ToolProduct` contract. `context.md` is where kiln records corrections, so this is an allowed edit. |
| `plans/intellibuild.md` | "kiln's pykit handoff" needs aligning | The same | Drop the handoff reference. |
| `specs/epics/E6-rebuild-the-repos/F6.1-pykit-skeleton.md` | The pykit candidate's `kiln doctor --full` passes, with pykit's docs ported | That cannot pass until R1–R5 land: the candidate would carry 25 root-to-package links kiln reports as broken, and seven package sites kiln does not know about. | Add a dependency on the R1–R5 work. Also see the open question on F6.1's shape. |

## What stays out of this plan

- **Instruction files.** kiln's README is the single prose home and `CLAUDE.md`
  a pointer (kiln ADR-0003); pykit keeps agent instructions in `CLAUDE.md`.
  Both pass the instruction-pointer check. Whether the standard should pick
  one model is a separate decision, best made when F6.1 regenerates pykit's
  skeleton.
- **pykit's CI, apart from the docs deploy.** pykit's `_package-ci.yml` and its
  planned change-scoped, dependency-ordered jobs (pykit S9.3.3) are for F6.1
  to map onto the generated matrix. R7 takes only the docs deploy.

## A small bug seen on the way

kiln's own generated nav lists `plans/reviews/index.md` as a second "Overview"
under Plans, because `plans/index.md` links to it and `_children_entries` titles
every `index.md` "Overview". A linked sub-index should take the title of the
link or its directory ("Reviews").

## If accepted: a proposed epic

| Feature | Covers |
| -- | -- |
| Package docs in the standard | R1 and R5: the standard's text, the seeded `_structure.md` section, `kiln new` seeding, `docs:build` over every site |
| Published and internal packages | R7: the per-archetype rule in the standard, the seeded runbook, the published-package checks, the versioned docs deploy in the `python-lib` CI template |
| Nav for package sites | R2: the `include` area kind and generated package navs |
| Checks that match what ships | R3 and R4: link resolution into package sites, the package isolation rule, `exclude_docs` |
| Cross-repository content rule | R6: the seeded `specs/_structure.md` rule and the kiln page corrections above |

The first three and R7 are in F6.1's path; the cross-repository rule can land
any time. R7's CI part waits for pykit to prove the deploy.

## Open questions for the owner

1. **R6:** make the "no cross-repository acceptance" rule part of the standard
   for every repository, or keep it pykit-only?
1. **F6.1's shape.** F6.1's acceptance runs inside pykit (`cd rn-forge/pykit`).
   Under R6, is the pykit cutover kiln's work, or pykit's? The alternative:
   kiln's part is "the `python-lib` archetype renders a repository that can
   host pykit", proved on a pykit-shaped fixture, and the cutover is a pykit
   feature.
