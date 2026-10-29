#!/usr/bin/env bash
# Build an ngkit-shaped node-lib repository from a fresh `kiln new` (kiln S9.1.6).
# The skeleton is kiln's; the repository-owned files (manifests, Nx workspace,
# lint and format config, projects and docs content) are ngkit's, read at a ref with
# `git archive`, so the checkout and its working tree are never touched. kiln is this
# checkout, installed editable.
# The generated Taskfile runs `kiln doctor` with `uvx` from the GitHub-pinned
# `[kiln] ref`, which does not ship `node-lib` until it is pushed. The script
# snapshots this checkout (uncommitted work too) as that ref in a local bare
# repository and writes <scratch dir>/../kiln-local.env; source it before the
# shaped repository's `task` commands so `uvx` fetches the snapshot instead.
# Usage: tests/e2e/ngkit_shape.sh <scratch dir> <kiln checkout> [ngkit ref, default 0c2cd2a]
# NGKIT_REPO overrides the checkout read, default ../ngkit beside the kiln checkout.
set -euo pipefail
dir=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
kiln_root=$(cd "$2" && pwd)
ngkit_ref=${3:-0c2cd2a}
ngkit_repo=${NGKIT_REPO:-$kiln_root/../ngkit}
ngkit_repo=$(cd "$ngkit_repo" && pwd)
kiln() { uv run --project "$kiln_root" kiln "$@"; }

# `kiln new` stages under the directory it runs in; keep that out of the checkout.
(cd "$(dirname "$dir")" && kiln new "$dir" --archetype node-lib --docs mkdocs --yes </dev/null)
[ -d "$dir/.git" ] || git -C "$dir" init -q
git -C "$dir" remote remove origin 2>/dev/null || true
git -C "$dir" remote add origin https://github.com/rn-forge/ngkit-shape

# The pages are ngkit's alone: the scaffold's starter pages go, its _structure.md stay.
find "$dir/docs" -type f ! -name _structure.md -delete

# ngkit's repository-owned files over the scaffold's. Its docs/ content pages come
# too, but not the _structure.md files: those are kiln's.
git -C "$ngkit_repo" archive "$ngkit_ref" \
  package.json pnpm-lock.yaml pnpm-workspace.yaml nx.json project.json \
  tsconfig.base.json eslint.config.mjs .prettierrc .prettierignore .nvmrc \
  .verdaccio apps libs tools/scripts docs |
  tar -x -C "$dir" --exclude '_structure.md'

# `apply` rewrites mkdocs.yml without its derived nav and then reports the nav stale;
# `docs-generate` writes it back and the second `apply` must pass. Generation runs
# until a pass changes nothing, as one pass writes what the next one lists.
(cd "$dir" && kiln apply </dev/null) || echo "first apply reported the nav stale, as expected" >&2
while [ "$(cd "$dir" && kiln docs-generate . | tail -n 1)" != "no change" ]; do :; done
(cd "$dir" && kiln apply </dev/null)

# ngkit's prose is not mdformat-clean (82 files at 0c2cd2a), and `task lint` checks
# it. Reformatting it is ngkit's own step at its cutover, not something kiln hides.
(cd "$dir" && task format)

# Snapshot this checkout as the pinned ref, without touching its index or refs.
ref=$(sed -n 's/^ref = "\(.*\)"$/\1/p' "$dir/.rn-forge/kiln/config.toml")
snapshot=$(dirname "$dir")/kiln-local.git
git init -q --bare "$snapshot"
index=$(mktemp -u)
tree=$(GIT_INDEX_FILE=$index git -C "$kiln_root" add -A && GIT_INDEX_FILE=$index git -C "$kiln_root" write-tree)
rm -f "$index"
commit=$(git -C "$kiln_root" commit-tree "$tree" -p HEAD -m "kiln checkout snapshot")
git -C "$kiln_root" push -q --force "$snapshot" "$commit:refs/heads/$ref"
cat >"$(dirname "$dir")/kiln-local.env" <<ENV
export UV_NO_GITHUB_FAST_PATH=1
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=url.file://$snapshot.insteadOf
export GIT_CONFIG_VALUE_0=https://github.com/rn-forge/kiln
ENV
echo "source $(dirname "$dir")/kiln-local.env before running task in $dir"
