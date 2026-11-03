#!/usr/bin/env bash
# Build a minimal ngkit-shaped node-lib repository from a fresh `kiln new` (kiln S9.1.6):
# kiln's scaffold plus one publishable Angular library, added with Nx's generator and
# declared publishable as the standard's section 9 says. Nothing is read from ngkit;
# ngkit's own cutover is ngkit's (its kiln-adoption epic).
# The generated Taskfile runs `kiln doctor` with `uvx` from the GitHub-pinned
# `[kiln] ref`. The script snapshots this checkout (uncommitted work too) as that ref
# in a local bare repository and writes <scratch dir>/../kiln-local.env; source it
# before the shaped repository's `task` commands so `uvx` fetches the snapshot instead.
# Usage: tests/e2e/ngkit_shape.sh <scratch dir> <kiln checkout>
set -euo pipefail
dir=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
kiln_root=$(cd "$2" && pwd)
kiln() { uv run --project "$kiln_root" kiln "$@"; }

# `kiln new` stages under the directory it runs in; keep that out of the checkout.
(cd "$(dirname "$dir")" && kiln new "$dir" --archetype node-lib --docs mkdocs --yes </dev/null)
[ -d "$dir/.git" ] || git -C "$dir" init -q
git -C "$dir" remote remove origin 2>/dev/null || true
git -C "$dir" remote add origin https://github.com/rn-forge/ngkit-shape

(cd "$dir" && task setup)

# One library, with the scaffold's `nx.json` generator defaults (no test-runner flag).
(cd "$dir" && pnpm exec nx g @nx/angular:library libs/shape \
  --publishable --importPath=@ngkit-shape/shape --no-interactive)

# Publishable, as the standard's section 9 says; the scaffold has Node but no `jq`.
(cd "$dir" && node -e '
const fs = require("fs");
const path = "libs/shape/project.json";
const project = JSON.parse(fs.readFileSync(path, "utf8"));
project.tags = [...new Set([...(project.tags || []), "publishable"])];
project.targets = project.targets || {};
project.targets.pack = {};
project.targets["verify-dist"] = {};
const publish = project.targets["nx-release-publish"] || {};
publish.options = { ...(publish.options || {}), dryRun: true };
project.targets["nx-release-publish"] = publish;
fs.writeFileSync(path, JSON.stringify(project, null, 2) + "\n");
')

# As a developer would after generating code. The generator's package.json lists
# `@angular/common`, which its code does not use, and `@nx/dependency-checks` fails
# `task lint` on it until `--fix` drops it.
(cd "$dir" && pnpm exec nx lint shape --fix && task format)

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
