"""`kiln config-update`, `config-upgrade` and `pin`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rn_forge.commons import generation
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.runtime.console import console

from rn_forge.kiln import archetypes
from rn_forge.kiln.commands import output
from rn_forge.kiln.config import CONFIG_PATH
from rn_forge.kiln.modules.core import cycle, kiln_ref, umbrella
from rn_forge.kiln.modules.core.config.manager import ConfigManager
from rn_forge.kiln.modules.docs.generate import finalizer

__all__ = ["config_update", "config_upgrade", "pin"]


def config_update(
    dry_run: bool = False, apply: bool = False, json: bool = False
) -> None:
    """Re-resolve the committed config against this kiln's current defaults.

    Prints the artifacts that would change and writes nothing. `--apply`
    writes the re-merged `config.toml` and runs the full `kiln apply`.

    Raises:
        AppException: The committed config was written for a different
            `schema_version` (naming `kiln config-upgrade`), its recorded
            `[source]` cannot be read, or (with `--apply`) the apply or check
            step fails.
    """
    _config_reresolve(
        allow_schema_upgrade=False, dry_run=dry_run, run_apply=apply, json=json
    )


def config_upgrade(
    dry_run: bool = False, apply: bool = False, json: bool = False
) -> None:
    """As `config-update`, also migrating a config from an older `schema_version`.

    Raises:
        AppException: The committed config needs a newer kiln, its recorded
            `[source]` cannot be read, or (with `--apply`) the apply or check
            step fails.
    """
    _config_reresolve(
        allow_schema_upgrade=True, dry_run=dry_run, run_apply=apply, json=json
    )


def _config_reresolve(
    *, allow_schema_upgrade: bool, dry_run: bool, run_apply: bool, json: bool
) -> None:
    """Shared body of `config-update` and `config-upgrade`."""
    output.use_json(json)
    root = umbrella.find_root(Path.cwd())
    manager = ConfigManager()
    resolution = manager.reresolve(root, allow_schema_upgrade=allow_schema_upgrade)
    prepared = cycle.prepare(
        root,
        config=resolution.config,
        provenance=resolution.provenance_metadata(),
    )
    settled = (generation.Action.UNCHANGED, generation.Action.SKIP)
    rows = output.change_rows(
        [change for change in prepared.plan.changes if change.action not in settled]
    )
    payload = {
        "root": str(root),
        "overrides": list(resolution.overrides),
        "artifacts": rows,
    }

    def text() -> None:
        for path in resolution.overrides:
            console.info("override {}", path)
        for row in rows:
            console.info("{} {} {}", row["key"], row["kind"], row["action"])

    output.emit(payload, text)

    if dry_run or not run_apply:
        return

    result = cycle.execute(
        root,
        prepared,
        finalize=finalizer(root, prepared.config),
        post=lambda: output.fail_on_errors(root),
    )
    change_rows = output.change_rows(result.changes)
    output.emit_rows({"root": str(root), "artifacts": change_rows}, change_rows)


def pin(ref: str = "", show: bool = False) -> None:
    """Pin the repository's `[kiln]` table to a commit, and write nothing else.

    A branch pins its newest commit and is recorded as `track`. A tag or SHA
    pins itself and drops `track`. Without `--ref`, follows `track`. `--show`
    prints the current `ref` and writes nothing. Reads only the `[kiln]` table,
    so a repository whose `ref` is still a branch can migrate. Does not apply;
    `task kiln:pin` does.

    Raises:
        AppException: `kiln.track-missing`, no `--ref` and no `track`; or the ref is
            not a branch or tag at kiln's remote.
    """
    path = umbrella.find_root(Path.cwd()) / CONFIG_PATH
    document = DocumentUtils.read_document(path)
    table: dict[str, Any] = document.get("kiln") or {}
    if show:
        console.print(table.get("ref", archetypes.KILN_REF))
        return
    new, track = kiln_ref.target(ref, table.get("track"))
    old = kiln_ref.write_pin(path, new, track)
    console.info("kiln ref {} \u2192 {}", old, new)
