# E11 — Package docs sites

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-09-26 |

Releases: [release-1](../../../releases/release-1/index.md),
[release-2](../../../releases/release-2/index.md) · Decisions:
[ADR-0008](../../../adr/ADR-0008.md), [ADR-0009](../../../adr/ADR-0009.md)

pykit adopted kiln's docs model on 2026-09-26, and kiln's docs checker was run
against pykit's tree ([plan](../../../plans/pykit-docs-alignment.md)). It passed
on everything the standard models. Every finding was in something the standard
does not model yet: a library workspace whose packages each publish their own
docs site. This epic makes the standard model it, for `python-lib` only
([ADR-0008](../../../adr/ADR-0008.md)). It also seeds the rule that a
repository's specs are accepted inside that repository
([ADR-0009](../../../adr/ADR-0009.md)).

**Dependencies.** F11.1 builds on the `docs` module as
[S4.3.2](../E4-generator/F4.3-concern-modules.md#s432-docs) left it, and after
[S13.1.1](../E13-docs-work-model/F13.1-derived-regions.md#s1311-the-nav-is-a-derived-region)
made the nav a derived region. F11.2 needs F11.1. F11.5 needs F11.2 and its
entry criterion. F11.3 needs F11.2 and the CLI's
[S4.5.1–S4.5.2](../E4-generator/F4.5-cli.md). F11.4 needs nothing. Downstream,
[S6.1.1](../E6-rebuild-the-repos/F6.1-pykit-skeleton.md) needs F11.1–F11.3, and
[F4.4](../E4-generator/F4.4-render-matrix.md)'s `python-lib` cell needs S11.3.1.

**Goldens first.** While `tests/fixtures/golden/` is in git, a template change
starts in the golden it reproduces
([render-matrix policy](../E4-generator/F4.4-render-matrix.md#template-review-policy)).
S11.2.1 and S11.3.1 change the `python-lib` golden before any template does.

**Where the checks run.** Every check this epic adds extends `docs-structure`,
`docs-site` or `docs-generate`.
[S4.6.5](../E4-generator/F4.6-doctor.md#s465-doctor-respects-ownership) moves
those checks out of doctor's ownership report and into explicit docs quality
tasks, and these checks move with them. Nothing here is a doctor-only check.

**Already applied, 2026-09-26.** Under ADR-0009, the kiln pages that restated
pykit's work were corrected when the ADR was accepted: the board's
[pins](../../index.md#upstream-pins), [E5](../E5-web-archetypes/index.md),
[E7](../E7-pykit-release-pin-flip/index.md),
[F6.1](../E6-rebuild-the-repos/F6.1-pykit-skeleton.md), `plans/context.md` and
`plans/intellibuild.md`. kiln's own `docs/specs/_structure.md` gained the rule
at the same time. F11.4 carries it into the templates.

## Features

| ID | Feature | Depends on | State |
| -- | -- | -- | -- |
| [F11.1](F11.1-checks-learn-package-sites.md) | The docs checks learn package sites | S4.3.2 (done), S13.1.1 | Closed |
| [F11.2](F11.2-python-lib-package-sites.md) | `python-lib` repositories carry package docs sites | F11.1 | New |
| [F11.3](F11.3-generate-package.md) | `kiln generate package` | F11.2, S4.5.1, S4.5.2 | New |
| [F11.4](F11.4-cross-repository-rule.md) | The docs rules are one standard, and kiln owns them | S13.3.1, for S11.4.2 | Closed |
| [F11.5](F11.5-deploy-package-sites.md) | CI deploys versioned package sites | F11.2; the entry criterion on S11.5.1 | New |

**Out of scope.** Instruction files: kiln keeps its prose in `README.md` and
pykit keeps it in `CLAUDE.md`. Both pass the instruction-pointer check, so
choosing one model is a separate decision. pykit's CI, apart from the docs
deploy, is out of scope too. Uploading packages to an index waits until a
repository chooses one; it would be a `[ci]` setting then.
`kiln generate package` for the application archetypes' internal packages stays
in [E10](../E10-kiln-generators/index.md).

## Design

The layout a `python-lib` repository has once this epic is done:

```text
mkdocs.yml                    # repo-owned body + derived nav region; monorepo plugin;
                              # mkdocstrings paths: [packages/*/src]
docs/                         # cross-package material only: architecture, guides,
  _areas.yml                  #   runbooks, releases, specs, adr
  _structure.md               # gains a "Package docs" section
  runbooks/adding-a-package.md
packages/<pkg>/
  pyproject.toml              # [project.urls]: Documentation, Source, Changelog, Issues
  README.md                   # absolute links only
  CHANGELOG.md                # Keep a Changelog
  mkdocs.yml                  # seeded once by `kiln generate package`; no managed block
  docs/
    index.md
    changelog.md              # includes CHANGELOG.md through pymdownx.snippets
    guides/                   # kebab-case pages
    reference/                # mkdocstrings pages; treated as generated
```

The root `docs/_areas.yml` declares the package sites as an area that is not a
directory:

```yaml
- key: packages
  title: Packages
  nav: include
```

The derived nav renders that area as one entry per `config.packages` entry, in
config order: `- <pkg dir name>: '!include packages/<pkg>/mkdocs.yml'`.

**How links resolve.** The monorepo plugin mounts each included site at
`<site_name>/` in the root site. A root page's link whose resolved path starts
with a package's `site_name` segment is therefore a link into that package's
`docs_dir`. The reverse holds inside a package: a link that resolves outside
that package's `docs/` is an error, even when the target exists on disk. That is
the rule a standalone strict build enforces, checked without a build.

**Only what ships is checked.** The link, anchor and orphan checks skip every
page that `mkdocs.yml`'s `exclude_docs` excludes. For a package page, that is
the package's own `mkdocs.yml`. The patterns are read with `pathspec`, the
library MkDocs itself uses for this key.

**URLs.** `kiln generate package` reads `git remote get-url origin` once, when
it writes the package, and derives the following from
`https://github.com/<owner>/<repo>`:

| `[project.urls]` key | Value |
| -- | -- |
| `Documentation` | `https://<owner>.github.io/<repo>/packages/<pkg>/latest/` |
| `Source` | `https://github.com/<owner>/<repo>` |
| `Changelog` | `https://github.com/<owner>/<repo>/blob/main/packages/<pkg>/CHANGELOG.md` |
| `Issues` | `https://github.com/<owner>/<repo>/issues` |

These values are written into a seeded, repo-owned file and nothing managed
reads them, so this does not bend [ADR-0004](../../../adr/ADR-0004.md).

## Acceptance

E11 is done when every feature's acceptance block passes. This block re-proves
the epic end to end afterwards.

```bash
set -euo pipefail
cd rn-forge/kiln
kiln_dir=$PWD
kiln() { uv run --project "$kiln_dir" kiln "$@"; }
task validate
s=$(mktemp -d)
kiln new "$s/lib" --archetype python-lib --docs mkdocs --yes </dev/null
cd "$s/lib"
git init -q && git remote add origin https://github.com/rn-forge/e11-proof
kiln generate package e11-alpha
kiln generate package e11-beta
uv sync
task validate
kiln doctor
```
