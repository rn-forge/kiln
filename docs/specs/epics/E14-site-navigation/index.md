# E14 — Docs site navigation and work summaries

|  |  |
| -- | -- |
| **State** | New |

Decisions: [ADR-0013](../../../adr/ADR-0013.md) (proposed)

The docs site's single sidebar stacks every area's pages on top of each other.
No page lists all the epics, and an epic or feature page shows the state of its
children only in scattered headings. This epic makes each area a top tab with
its own sidebar. The specs tab lists every epic, grouped in ranges of ten, and
an epic list page tabulates them all. Every epic and feature page then opens
with a derived summary of its features or stories. All of it is written by
`task docs:generate` and checked by `task lint`, like the board.

**Dependencies.** Nothing starts before the owner accepts ADR-0013, which its
status line records. F14.2 builds on S14.1.2, which first extends the
derived-region generator. **Goldens:** the hand-authored goldens have left git
(S4.4.9), so a template change here is reviewed in the rendered cells
(`task self:golden:compare`).

## Features

| ID | Feature | Release | Depends on | State |
| -- | -- | -- | -- | -- |
| [F14.1](F14.1-tabbed-navigation.md) | Area tabs, the epic ranges and the epic list | release-1 | ADR-0013 | New |
| [F14.2](F14.2-work-summaries.md) | Epic and feature summary tables | release-1 | S14.1.2 | New |

**Out of scope.**

- ADR range groups. The decision log's index table is its way in, and it has 13
  entries.
- Tabs for package sites (`package/mkdocs.yml.j2`). They are standalone sites
  with their own nav.
- Moving any other repository's existing site onto the new layout. A repository
  adopts it on its own, through kiln ([ADR-0009](../../../adr/ADR-0009.md)).
- Paginating long feature pages.

## Acceptance

E14 is done when both features' acceptance blocks pass. This block re-proves the
epic end to end afterwards.

```bash
set -euo pipefail
cd rn-forge/kiln
uv run kiln doctor . --only docs-generate
uv run kiln doctor . --only docs-structure
task validate
s=$(mktemp -d)
uv run kiln new "$s/tool" --archetype python-tool --docs mkdocs --yes </dev/null
(cd "$s/tool" && uv sync && task validate)
grep -q 'navigation.tabs' "$s/tool/mkdocs.yml"
test -f "$s/tool/docs/specs/epics/index.md"
```
