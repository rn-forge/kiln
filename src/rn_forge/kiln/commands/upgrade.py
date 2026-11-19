"""Upgrade a repository with the kiln at its new pin."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.runtime.console import console

from rn_forge.kiln import archetypes
from rn_forge.kiln.commands import output
from rn_forge.kiln.config import CONFIG_PATH
from rn_forge.kiln.modules.core import cycle, kiln_ref, process, umbrella
from rn_forge.kiln.modules.docs.generate import finalizer
from rn_forge.kiln.modules.python import ranges

__all__ = ["upgrade"]


def upgrade(
    ref: str = "", force: bool = False, target_ref: str = "", target_track: str = ""
) -> None:
    """`kiln repo-upgrade`: pin kiln to a ref, apply its standard and range changes, and validate.

    With no ref, follow the current tracking branch. A failed gate restores
    the previous pin, files and locks unless `--force` keeps the applied upgrade.
    The launcher sets the internal options `--target-ref` and `--target-track`.
    """
    root = umbrella.find_root(Path.cwd())
    if target_ref:
        _apply(root, target_ref, target_track or None, force)
        return

    document = DocumentUtils.read_document(root / CONFIG_PATH)
    table: dict[str, Any] = document.get("kiln") or {}
    new, track = kiln_ref.target(ref, table.get("track"))
    rc = process.run(
        "kiln-upgrade",
        "uvx",
        "--from",
        f"rn-forge-kiln @ {archetypes.KILN_GIT}@{new}",
        "kiln",
        "repo-upgrade",
        "--target-ref",
        new,
        *(("--target-track", track) if track else ()),
        *(("--force",) if force else ()),
        cwd=root,
        check=False,
        capture_output=False,
    ).return_code
    if rc:
        raise AppException("upgrade.target-failed: the kiln at {} exited {}", new, rc)


def _status(root: Path) -> list[str]:
    status = process.run(
        "git-status", "git", "status", "--porcelain", "--untracked-files=all", cwd=root
    ).stdout
    return (status or "").splitlines()


def _task(root: Path, verb: str) -> int:
    return process.run(
        f"task-{verb}", "task", verb, cwd=root, check=False, capture_output=False
    ).return_code


def _apply(root: Path, target_ref: str, target_track: str | None, force: bool) -> None:
    if _status(root):
        raise AppException(
            "upgrade.dirty: the working tree has uncommitted or untracked changes "
            "— commit or stash them, so a failed upgrade can be restored"
        )

    pinned = cycle.Footprint(root, {CONFIG_PATH})
    old = kiln_ref.write_pin(root / CONFIG_PATH, target_ref, target_track)
    footprint = None
    try:
        prepared = cycle.prepare(root)
        prepared.plan.check()
        moves = ranges.plan(prepared.config, root)
        footprint = cycle.Footprint(
            root,
            prepared.write_paths()
            | {Path(move.path) for move in moves}
            | {Path("uv.lock"), Path("pnpm-lock.yaml")},
        )
        console.info("kiln ref {} → {}", old, target_ref)
        rows = output.change_rows(prepared.plan.changes)
        output.emit_rows({"root": str(root), "artifacts": rows}, rows)
        for move in moves:
            breaking = " (breaking range)" if move.breaking else ""
            console.info("{}: {} → {}{}", move.path, move.old, move.new, breaking)

        cycle.execute(
            root,
            prepared,
            finalize=finalizer(root, prepared.config),
            post=lambda: output.fail_on_errors(root),
        )
        ranges.write(root, moves)
    except BaseException:
        if footprint is not None:
            footprint.restore()
        pinned.restore()
        raise

    for move in moves:
        console.info("{}:", move.distribution)
        console.print(ranges.release_notes(move), markup=False)

    for verb in ("setup", "validate"):
        if _task(root, verb):
            break
    else:
        return

    if force:
        raise AppException(
            "upgrade.kept: task {} failed; the upgrade is kept because of --force "
            "— fix what it reports",
            verb,
        )

    footprint.restore()
    pinned.restore()
    recovery = (
        "; recovery task setup also failed — run it again"
        if _task(root, "setup")
        else ""
    )
    paths = ", ".join(line[3:] for line in _status(root))
    residual = f"; still changed: {paths}" if paths else ""
    raise AppException(
        "upgrade.failed: task {} failed; the previous pin, files and locks "
        "are restored{}{}",
        verb,
        recovery,
        residual,
    )
