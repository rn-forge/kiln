"""`kiln apply`: reconcile the current repository's rendered artifacts."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons import generation
from rn_forge.commons.exceptions import AppException

from rn_forge.kiln.commands import output
from rn_forge.kiln.modules.core import cycle, umbrella
from rn_forge.kiln.modules.docs.generate import finalizer

__all__ = ["apply"]


def apply(
    force: list[str] | None = None, dry_run: bool = False, json: bool = False
) -> None:
    """Reconcile the current repository's rendered artifacts.

    Plans first, refusing any `--force` value that does not name a reported,
    blocking change; then applies, then runs `kiln doctor`'s ownership checks.

    Raises:
        AppException: A `--force` value names no reported change or a
            non-blocking one, an unforced change is blocking, or a check
            after the apply reports an error.
    """
    output.use_json(json)
    root = umbrella.find_root(Path.cwd())
    force_values = tuple(force or ())

    prepared = cycle.prepare(root, force=force_values)
    _validate_force(prepared.plan, force_values)

    result = cycle.execute(
        root,
        prepared,
        dry_run=dry_run,
        finalize=finalizer(root, prepared.config),
        post=lambda: output.fail_on_errors(root),
    )
    rows = output.change_rows(result.changes)
    output.emit_rows({"root": str(root), "artifacts": rows}, rows)


def _validate_force(planned: generation.Plan, force_values: tuple[str, ...]) -> None:
    """Refuse a `--force` value naming no reported change, or a non-blocking one."""
    by_name: dict[str, generation.Change] = {}
    for change in planned.changes:
        by_name[change.key] = change
        by_name[change.path] = change

    reported = sorted({change.path for change in planned.changes})
    blocking = sorted(
        change.path
        for change in planned.changes
        if change.action in generation.BLOCKING_ACTIONS
    )
    for value in force_values:
        change = by_name.get(value)
        if change is None:
            raise AppException(
                "--force {!r} does not name a reported change — reported: {}",
                value,
                ", ".join(reported),
            )
        if change.action not in generation.BLOCKING_ACTIONS:
            raise AppException(
                "--force {!r} is not a blocking change ({}) — blocking: {}",
                value,
                change.action.value,
                ", ".join(blocking),
            )
