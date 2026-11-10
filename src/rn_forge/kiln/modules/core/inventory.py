"""The cutover inventory: every file of a reference repository and of an old one, classed."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils

from rn_forge.kiln.modules.core import umbrella
from rn_forge.kiln.modules.core.cycle import SCAFFOLDED_KEY

__all__ = ["KINDS", "Row", "inventory"]

KINDS = ("managed", "block", "seeded", "scaffolded", "old-only")


@dataclass(frozen=True, slots=True)
class Row:
    """One path of the inventory: its class and whether the two bytes match."""

    path: str
    kind: str
    status: str


def inventory(reference: Path, old: Path) -> list[Row]:
    """List the union of *reference*'s kiln-known files and *old*'s tracked files.

    Args:
        reference: A repository holding `.rn-forge/kiln/state.json`.
        old: A git checkout.

    Returns:
        One row per path, ordered by kind (`KINDS`) and then path.

    Raises:
        AppException: *old* is not a git repository.
    """
    state = DocumentUtils.read(reference / umbrella.STATE_PATH)
    known = {entry["path"]: entry["kind"] for entry in state["entries"].values()}
    for path in state["metadata"].get(SCAFFOLDED_KEY, []):
        known.setdefault(path, "scaffolded")
    listed = subprocess.run(
        ["git", "-C", str(old), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode != 0:
        raise AppException("inventory.not-a-git-repo: {}", old)

    prefix = f"{umbrella.UMBRELLA}/"
    in_old = {p for p in listed.stdout.split("\0") if p and not p.startswith(prefix)}
    in_reference = {p for p in known if not p.startswith(prefix)}

    rows: list[Row] = []
    for path in in_old | in_reference:
        if path in in_reference and path in in_old:
            same = (reference / path).read_bytes() == (old / path).read_bytes()
            rows.append(Row(path, known[path], "same" if same else "differs"))
        elif path in in_reference:
            rows.append(Row(path, known[path], "reference-only"))
        else:
            rows.append(Row(path, "old-only", "old-only"))
    return sorted(rows, key=lambda row: (KINDS.index(row.kind), row.path))
