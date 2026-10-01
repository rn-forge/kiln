# E13 — The docs work model and derived regions

**Status:** planned · **Release:**
[release-1](../../../releases/release-1/index.md) · **Decisions:**
[ADR-0003](../../../adr/ADR-0003.md) (revised),
[ADR-0011](../../../adr/ADR-0011.md), [ADR-0012](../../../adr/ADR-0012.md)

kiln's docs model has two weaknesses. The `mkdocs.yml` nav is generated, but
`state.json` hashes it as a kiln-owned block, so every new page makes the
baseline stale. Spec and release status is also written twice, on the feature
and on its release page's scope row, and only a reviewer's eye keeps the two in
step. This epic makes the nav, the spec board and each release's Scope table
**derived regions**: derived from the repository's own pages, checked by
regenerating them, never hashed. It also moves the seeded rules, and kiln's own
docs, to Azure DevOps-shaped work items. [design.md](design.md) holds the keys,
the rules, the finding codes and the region shapes, verbatim.

**Dependencies.** F13.1 depends on the owner accepting ADR-0003's revision,
ADR-0011 and ADR-0012; their status lines record it, and no story starts before
then. F13.2 needs S13.1.1. F13.3 needs F13.2. Downstream,
[S11.1.1](../E11-package-docs/F11.1-checks-learn-package-sites.md) needs
S13.1.1, and
[S11.4.2](../E11-package-docs/F11.4-cross-repository-rule.md#s1142-kiln-owns-the-_structuremd-files)
needs S13.3.1, so that kiln starts owning the `_structure.md` files only once
they carry the new rules.

**Goldens first.** While `tests/fixtures/golden/` is in git, a template change
starts in the golden it reproduces
([render-matrix policy](../E4-generator/F4.4-render-matrix.md#template-review-policy)).
S13.1.1 and S13.3.1 change all three goldens before any template.

**Build order.** E13 is built before E11's F11.1–F11.3, and so before F4.4.

## Features

| ID | Feature | Release | Depends on |
| -- | -- | -- | -- |
| [F13.1](F13.1-derived-regions.md) | Derived regions, starting with the nav | release-1 | S4.3.2 (done) |
| [F13.2](F13.2-board-and-scope.md) | The board and Scope regions, and metadata checks | release-1 | S13.1.1 |
| [F13.3](F13.3-adopt-the-model.md) | The seeded rules and kiln's own docs adopt the model | release-1 | F13.2 |

**Out of scope.** Moving pykit and ngkit onto the model. Each repository does
that in its own specs ([ADR-0009](../../../adr/ADR-0009.md)), once it adopts
kiln. Assembling native reference sites for Node and Java repositories (see
[design](design.md#one-site-per-repository)).

## Acceptance

E13 is done when every feature's acceptance block passes. This block re-proves
the epic end to end afterwards.

```bash
set -euo pipefail
cd rn-forge/kiln
absent() { local rc=0; rg -q --hidden --glob '!.git' "$@" </dev/null || rc=$?; [ "$rc" -eq 1 ]; }
absent -e 'docs-nav|docs:nav|docs_nav|nav block' --glob '!docs/specs/**' --glob '!docs/plans/**' \
  --glob '!adr-refactor.md' --glob '!tests/modules/core/checks/test_generated.py' .
absent -F 'generated nav' --glob '*.json' .rn-forge tests/fixtures/golden
uv run kiln doctor . --only docs-generate
task validate
for g in python-app python-tool python-lib; do
  (cd "tests/fixtures/golden/$g" && task validate)
done
s=$(mktemp -d)
uv run kiln new "$s/tool" --archetype python-tool --docs mkdocs --yes </dev/null
(cd "$s/tool" && uv sync && task validate)
```
