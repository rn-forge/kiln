#!/usr/bin/env bash
# Build a pykit-shaped python-lib repository from a fresh `kiln new` (kiln S6.1.1).
# The skeleton is kiln's; each member's pyproject.toml, src/ and tests/ are pykit's,
# because kiln imports commons, cli and tooling and the overrides below make it take
# the workspace copies. kiln is this checkout, installed editable.
# Usage: tests/e2e/pykit_shape.sh <scratch dir> <kiln checkout> [pykit ref, default main]
# PYKIT_REPO overrides the clone source, e.g. a local checkout to test unpushed work.
set -euo pipefail
dir=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
kiln_root=$(cd "$2" && pwd)
pykit_ref=${3:-main}
pykit_repo=${PYKIT_REPO:-https://github.com/rn-forge/pykit}
kiln() { uv run --project "$kiln_root" kiln "$@"; }
kiln_python() { uv run --project "$kiln_root" python "$@"; }

# `kiln new` stages under the directory it runs in; keep that out of the checkout.
(cd "$(dirname "$dir")" && kiln new "$dir" --archetype python-lib --docs mkdocs --yes </dev/null)
[ -d "$dir/.git" ] || git -C "$dir" init -q
git -C "$dir" remote remove origin 2>/dev/null || true
git -C "$dir" remote add origin https://github.com/rn-forge/pykit-shape

pykit=$(mktemp -d)/pykit
# A local path clones through file://, so --depth is honoured and the ref is a branch.
case $pykit_repo in /*) pykit_repo=file://$pykit_repo ;; esac
git clone -q --depth 1 --branch "$pykit_ref" "$pykit_repo" "$pykit"

# kiln (a dev dependency) requires commons, cli and tooling from pykit's git
# source; the overrides make it take the workspace copies (ADR-0006). They go in
# before the first member, or uv sees two URLs for one package.
python3 - "$dir/pyproject.toml" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
# commons keeps pykit's `[all]`: an override replaces the requirement, extras included.
line = 'override-dependencies = ["rn-forge-commons[all]", "rn-forge-cli", "rn-forge-tooling"]\n'
assert "[tool.uv]\n" in text and "override-dependencies" not in text
open(path, "w", encoding="utf-8").write(text.replace("[tool.uv]\n", "[tool.uv]\n" + line, 1))
PY

# The members are pykit's own list, so a new package needs no edit here.
packages=()
while read -r p; do packages+=("$p"); done < <(python3 - "$pykit/pyproject.toml" <<'PY'
import sys, tomllib
for m in tomllib.load(open(sys.argv[1], "rb"))["tool"]["uv"]["workspace"]["members"]:
    print(m.removeprefix("packages/"))
PY
)
for p in "${packages[@]}"; do
  # pykit's members are namespace packages: rn-forge-cli is rn_forge.cli (S6.1.3).
  kiln generate package "$p" --path "$dir" --module "rn_forge.${p#rn-forge-}"
  # pykit's code, with its own dependency declarations: a pinned direct URL for
  # each sibling, and a `{ workspace = true }` source for local development.
  # docs/ and its mkdocs.yml (seeded, so repo-owned) too: the guides carry
  # examples the tests execute, and the nav lists every page.
  rm -rf "$dir/packages/$p/src" "$dir/packages/$p/tests" "$dir/packages/$p/docs"
  for f in pyproject.toml README.md CHANGELOG.md mkdocs.yml src tests docs; do
    cp -R "$pykit/packages/$p/$f" "$dir/packages/$p/$f"
  done
done

# A cutover keeps pykit's root pyproject.toml, which kiln never rewrites: its ruff
# tables replace kiln's, and its pytest markers join kiln's ini options.
kiln_python - "$pykit/pyproject.toml" "$dir/pyproject.toml" <<'PY'
import sys, tomlkit
pykit = tomlkit.parse(open(sys.argv[1], encoding="utf-8").read())
path = sys.argv[2]
shape = tomlkit.parse(open(path, encoding="utf-8").read())
shape["tool"]["ruff"] = pykit["tool"]["ruff"]
shape["tool"]["pytest"]["ini_options"]["markers"] = pykit["tool"]["pytest"]["ini_options"]["markers"]
open(path, "w", encoding="utf-8").write(tomlkit.dumps(shape))
PY

# pykit owns its import contracts (S6.1.4): kiln renders the root packages only,
# and pykit's contracts go below the END marker.
kiln_python - "$dir/.rn-forge/kiln/config.toml" <<'PY'
import sys, tomlkit
path = sys.argv[1]
config = tomlkit.parse(open(path, encoding="utf-8").read())
config["archetype"]["python-lib"]["import_contracts"] = "own"
open(path, "w", encoding="utf-8").write(tomlkit.dumps(config))
PY
(cd "$dir" && kiln apply </dev/null)
{
  echo
  sed -n '/^\[importlinter:contract:/,$p' "$pykit/.importlinter"
} >>"$dir/.importlinter"

# pykit's root conftest.py holds fixtures its member tests use (`scaffold_venv`).
cp "$pykit/conftest.py" "$dir/conftest.py"

# The root's dependency groups take what pykit's tests need: the members with
# pykit's extras, and pykit's third-party dev and docs tools (its member
# mkdocs.yml files use mike).
python3 - "$pykit/pyproject.toml" "$dir/pyproject.toml" >"$dir/.pykit-groups" <<'PY'
import re, sys, tomllib
pykit = tomllib.load(open(sys.argv[1], "rb"))["dependency-groups"]
shape = tomllib.load(open(sys.argv[2], "rb")).get("dependency-groups", {})
name = lambda r: re.match(r"[A-Za-z0-9._-]+", r).group(0).lower()
have = {name(r) for g in shape.values() for r in g if isinstance(r, str)}
for r in pykit["workspace"]:
    print("workspace", r)
for group in ("dev", "docs"):
    for r in pykit[group]:
        if isinstance(r, str) and not name(r).startswith("rn-forge-") and name(r) not in have:
            print(group, r)
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
