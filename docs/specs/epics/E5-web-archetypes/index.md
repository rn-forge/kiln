# E5 — The web archetypes

**Status:** planned · **Release:**
[release-2](../../../releases/release-2/index.md) · **Phase:** E · **Estimate:**
2 weeks

Repo `rn-forge/kiln`. **Gated on `rn-forge-fastapi`** reaching its plan's
acceptance in pykit; `rn-forge-web` already exists. There are no hand-authored
goldens: templates are written directly and approved through the render matrix
([ADR-0005](../../../adr/0005-archetypes.md)).

## Features

| ID | Feature | Depends on |
| -- | -- | -- |
| [F5.1](F5.1-web-library-sets-and-modules.md) | Library sets, and the modules gain the web shapes | E4; `rn-forge-fastapi` |
| [F5.2](F5.2-kiln-new-web-end-to-end.md) | `kiln new` end to end for the web archetypes | F5.1; S5.2.1 on S5.2.2 |
| [F5.3](F5.3-shipped-web-cells.md) | The shipped web cells | F5.2; its open question |

## Acceptance

E5 is done when every feature's acceptance block passes. This block re-proves
the epic end to end afterwards.

```bash
set -euo pipefail
cd rn-forge/kiln
task self:golden:render && task self:golden:validate   # all web cells pass
scratch=$(mktemp -d)
uv run kiln new "$scratch/web" --archetype python-web-app --framework fastapi --frontend angular --docs mkdocs --yes </dev/null
(cd "$scratch/web" && uv sync && pnpm install && task validate && uv run --project "$OLDPWD" kiln doctor)
```
