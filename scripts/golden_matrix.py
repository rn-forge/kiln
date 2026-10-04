"""Render and validate every shipped archetype x flag cell of kiln's templates.

Usage: golden_matrix.py {render,validate,compare} [REF]

Cells land in `.goldens/<ref_dir>/<cell name>/`, beneath the repository root.
`compare` diffs the python-app, python-tool and python-lib cells against the
hand-authored goldens in `tests/fixtures/golden/`.
"""

from __future__ import annotations

import difflib
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDENS = ROOT / ".goldens"
LIB_ORIGIN = "https://github.com/rn-forge/golden-lib"
LIB_PACKAGES = ("golden-alpha", "golden-beta")
GOLDEN_FIXTURES = ROOT / "tests" / "fixtures" / "golden"
COMPARED: tuple[tuple[str, str], ...] = (
    ("python-app", "golden-app"),
    ("python-tool", "golden-tool"),
    ("python-lib", "golden-lib"),
)
_SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        ".docs-site",
        ".uv-cache",
        ".ruff_cache",
        ".pytest_cache",
        ".import_linter_cache",
        "__pycache__",
        "node_modules",
    }
)
_SKIP_FILES = frozenset(
    {
        ".DS_Store",
        ".coverage",
        "coverage.xml",
        "uv.lock",
        ".rn-forge/kiln/state.json",
        ".rn-forge/kiln/state.lock",
    }
)
# kiln's own working copies beside state.json, not rendered output.
_SKIP_PREFIXES = (".rn-forge/kiln/rendered/", ".rn-forge/kiln/backups/")


@dataclass(frozen=True)
class Cell:
    """One archetype at one set of flags, at the default docs profile."""

    name: str
    archetype: str
    flags: tuple[tuple[str, str], ...] = ()


def _cell(archetype: str, *flags: tuple[str, str]) -> Cell:
    name = archetype + "".join(f"-{flag}={value}" for flag, value in flags)
    return Cell(name, archetype, flags)


CELLS: tuple[Cell, ...] = (
    _cell("python-app"),
    _cell("python-tool"),
    _cell("python-lib"),
    _cell("python-web-api", ("backend", "fastapi")),
    _cell("python-web-app", ("backend", "fastapi"), ("frontend", "angular")),
)


def run(cmd: list[str], cwd: Path) -> bool:
    """Run *cmd* in *cwd*, streaming its output; True when it exits 0."""
    return subprocess.run(cmd, cwd=cwd, check=False).returncode == 0


def ref_dir(ref: str) -> str:
    """The directory name for *ref*; the current checkout is `working`."""
    return ref.replace("/", "-") if ref else "working"


def _require(cmd: list[str], cwd: Path) -> None:
    if not run(cmd, cwd):
        raise RuntimeError(f"failed in {cwd}: {' '.join(cmd)}")


def render_cell(cell: Cell, dest: Path, kiln_cmd: list[str]) -> None:
    """Render *cell* into *dest*, replacing what is there.

    Raises:
        RuntimeError: A step failed.
    """
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # The directory name becomes the repository name, which cannot hold `=`.
    built = dest.parent / dest.name.replace("=", "-")
    if built.exists():
        shutil.rmtree(built)
    shutil.rmtree(dest.parent / ".staging" / built.name, ignore_errors=True)
    new = [*kiln_cmd, "new", built.name, "--archetype", cell.archetype]
    for flag, value in cell.flags:
        new += [f"--{flag}", value]
    _require([*new, "--yes"], dest.parent)
    if cell.archetype == "python-lib":
        _require(["git", "init", "-q"], built)
        _require(["git", "remote", "add", "origin", LIB_ORIGIN], built)
        for package in LIB_PACKAGES:
            _require([*kiln_cmd, "generate", "package", package], built)
    if built != dest:
        built.rename(dest)
    shutil.rmtree(dest.parent / ".staging", ignore_errors=True)


def render(ref: str, out_root: Path) -> list[Path]:
    """Render every cell of *ref* (the working tree when empty) beneath *out_root*.

    Raises:
        RuntimeError: A step failed.
    """
    target = out_root / ref_dir(ref)
    if not ref:
        return _render_all(target, ["uv", "run", "--project", str(ROOT), "kiln"])
    temp = Path(tempfile.mkdtemp(prefix="kiln-golden-"))
    worktree = temp / "tree"
    try:
        _require(["git", "worktree", "add", "--detach", str(worktree), ref], ROOT)
        try:
            _require(["uv", "sync"], worktree)
            return _render_all(
                target, ["uv", "run", "--project", str(worktree), "kiln"]
            )
        finally:
            run(["git", "worktree", "remove", "--force", str(worktree)], ROOT)
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _render_all(target: Path, kiln_cmd: list[str]) -> list[Path]:
    paths: list[Path] = []
    for cell in CELLS:
        render_cell(cell, target / cell.name, kiln_cmd)
        paths.append(target / cell.name)
    return paths


def _check(cell_dir: Path) -> tuple[bool, bool, bool]:
    if not cell_dir.is_dir():
        return False, False, False
    # `-t` stops a cell with no Taskfile from running an ancestor's.
    task = ["task", "-t", "Taskfile.yml"]
    synced = run(["uv", "sync"], cell_dir) and run([*task, "validate"], cell_dir)
    return synced, run(["actionlint"], cell_dir), run([*task, "docs:build"], cell_dir)


def validate(ref: str, out_root: Path) -> int:
    """Validate every rendered cell of *ref*, print one table, and return 1 on any failure."""
    target = out_root / ref_dir(ref)
    mark = {True: "PASS", False: "FAIL"}
    rows: list[tuple[str, ...]] = [
        ("cell", "sync+validate", "actionlint", "docs", "result")
    ]
    failed = False
    for cell in CELLS:
        results = _check(target / cell.name)
        failed = failed or not all(results)
        rows.append((cell.name, *(mark[r] for r in results), mark[all(results)]))
    widths = [max(len(row[i]) for row in rows) for i in range(5)]
    for row in rows:
        print(" | ".join(text.ljust(width) for text, width in zip(row, widths)))
    return 1 if failed else 0


def normalize(text: str, name: str, target: str) -> str:
    """Rename *name* (and its module form) to *target*, and blank provenance versions.

    Only the golden's name is mapped, onto the cell's: a cell's name can equal
    its archetype (`python-app`), which a placeholder would also replace.
    """
    text = text.replace(name, target)
    text = text.replace(name.replace("-", "_"), target.replace("-", "_"))
    return re.sub(r"\b(Generated|Seeded) by kiln \S+", r"\1 by kiln <version>", text)


def _files(root: Path, name: str, target: str) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if not path.is_file() or _SKIP_DIRS.intersection(relative.parts):
            continue
        key = relative.as_posix()
        if key in _SKIP_FILES or path.name in _SKIP_FILES:
            continue
        if key.startswith(_SKIP_PREFIXES):
            continue
        found[normalize(key, name, target)] = path
    return found


def compare_cell(
    cell_dir: Path, golden_dir: Path, cell_name: str, golden_name: str
) -> list[str]:
    """Differences between a rendered cell and its golden, one line each, sorted."""
    if not cell_dir.is_dir():
        return [f"missing cell: {cell_dir}"]
    golden = _files(golden_dir, golden_name, cell_name)
    cell = _files(cell_dir, cell_name, cell_name)
    groups: dict[str, list[str]] = {}
    for key in golden.keys() - cell.keys():
        groups[f"only in golden: {key}"] = []
    for key in cell.keys() - golden.keys():
        groups[f"only in cell: {key}"] = []
    for key in golden.keys() & cell.keys():
        try:
            old = golden[key].read_text(encoding="utf-8")
            new = cell[key].read_text(encoding="utf-8")
            old = normalize(old, golden_name, cell_name)
            new = normalize(new, cell_name, cell_name)
        except UnicodeDecodeError:
            if golden[key].read_bytes() != cell[key].read_bytes():
                groups[f"differs: {key}"] = []
            continue
        if old != new:
            groups[f"differs: {key}"] = list(
                difflib.unified_diff(
                    old.splitlines(),
                    new.splitlines(),
                    fromfile=f"golden/{key}",
                    tofile=f"cell/{key}",
                    lineterm="",
                )
            )
    return [line for head in sorted(groups) for line in (head, *groups[head])]


def compare(ref: str, out_root: Path, golden_root: Path = GOLDEN_FIXTURES) -> int:
    """Diff each compared cell of *ref* against its golden, print one table, and return 1 on any difference."""
    target = out_root / ref_dir(ref)
    mark = {True: "PASS", False: "FAIL"}
    rows: list[tuple[str, ...]] = [("cell", "result")]
    failed = False
    for cell, golden_name in COMPARED:
        lines = compare_cell(target / cell, golden_root / cell, cell, golden_name)
        print("\n".join(lines))
        failed = failed or bool(lines)
        rows.append((cell, mark[not lines]))
    widths = [max(len(row[i]) for row in rows) for i in range(2)]
    for row in rows:
        print(" | ".join(text.ljust(width) for text, width in zip(row, widths)))
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    """Run `render`, `validate` or `compare` with an optional REF."""
    if not argv or argv[0] not in ("render", "validate", "compare") or len(argv) > 2:
        print("usage: golden_matrix.py {render,validate,compare} [REF]", file=sys.stderr)
        return 2
    ref = argv[1] if len(argv) == 2 else ""
    if argv[0] == "validate":
        return validate(ref, GOLDENS)
    if argv[0] == "compare":
        return compare(ref, GOLDENS)
    try:
        render(ref, GOLDENS)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
