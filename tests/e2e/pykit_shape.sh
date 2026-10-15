#!/usr/bin/env bash
# Build a pykit-shaped python-lib repository from a fresh `kiln new` (kiln S6.1.1).
# The skeleton is kiln's; each member's pyproject.toml, src/ and tests/ are pykit's,
# because kiln imports commons, cli and tooling and the overrides below make it take
# the workspace copies. kiln is this checkout, installed editable.
# Usage: tests/e2e/pykit_shape.sh <scratch dir> <kiln checkout> [pykit ref, default main]
set -euo pipefail
dir=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
kiln_root=$(cd "$2" && pwd)
pykit_ref=${3:-main}
kiln() { uv run --project "$kiln_root" kiln "$@"; }

# `kiln new` stages under the directory it runs in; keep that out of the checkout.
(cd "$(dirname "$dir")" && kiln new "$dir" --archetype python-lib --docs mkdocs --yes </dev/null)
[ -d "$dir/.git" ] || git -C "$dir" init -q
git -C "$dir" remote remove origin 2>/dev/null || true
git -C "$dir" remote add origin https://github.com/rn-forge/pykit-shape

pykit=$(mktemp -d)/pykit
git clone -q --depth 1 --branch "$pykit_ref" https://github.com/rn-forge/pykit "$pykit"

# kiln (a dev dependency) requires commons, cli and tooling from pykit's git
# source; the overrides make it take the workspace copies (ADR-0006). They go in
# before the first member, or uv sees two URLs for one package.
python3 - "$dir/pyproject.toml" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
line = 'override-dependencies = ["rn-forge-commons", "rn-forge-cli", "rn-forge-tooling"]\n'
assert "[tool.uv]\n" in text and "override-dependencies" not in text
open(path, "w", encoding="utf-8").write(text.replace("[tool.uv]\n", "[tool.uv]\n" + line, 1))
PY

packages=(rn-forge-commons rn-forge-cli rn-forge-tooling rn-forge-web
          rn-forge-django rn-forge-fastapi rn-forge-sqlalchemy)
for p in "${packages[@]}"; do
  kiln generate package "$p" --path "$dir"
  # pykit's code, with its own dependency declarations: a pinned direct URL for
  # each sibling, and a `{ workspace = true }` source for local development.
  rm -rf "$dir/packages/$p/src" "$dir/packages/$p/tests"
  for f in pyproject.toml README.md CHANGELOG.md src tests; do
    cp -R "$pykit/packages/$p/$f" "$dir/packages/$p/$f"
  done
done

# The root's dependency groups take what pykit's tests need: the members with
# pykit's extras, and pykit's third-party dev tools.
python3 - "$pykit/pyproject.toml" "$dir/pyproject.toml" >"$dir/.pykit-groups" <<'PY'
import re, sys, tomllib
pykit = tomllib.load(open(sys.argv[1], "rb"))["dependency-groups"]
shape = tomllib.load(open(sys.argv[2], "rb")).get("dependency-groups", {})
name = lambda r: re.match(r"[A-Za-z0-9._-]+", r).group(0).lower()
have = {name(r) for g in shape.values() for r in g if isinstance(r, str)}
for r in pykit["workspace"]:
    print("workspace", r)
for r in pykit["dev"]:
    if isinstance(r, str) and not name(r).startswith("rn-forge-") and name(r) not in have:
        print("dev", r)
PY
while read -r group req; do
  (cd "$dir" && uv add --quiet --no-sync --group "$group" "$req")
done <"$dir/.pykit-groups"
rm "$dir/.pykit-groups"

# This checkout's kiln, not the pushed branch the template pins.
(cd "$dir" && uv add --quiet --no-sync --dev --editable "$kiln_root")

{
  printf '# Packages\n\nEach package has its own site.\n\n'
  for p in "${packages[@]}"; do
    printf -- '- [%s](../%s/index.md)\n' "$p" "$p"
  done
} >"$dir/docs/guides/packages.md"

(cd "$dir" && uv sync --quiet && task docs:generate)
