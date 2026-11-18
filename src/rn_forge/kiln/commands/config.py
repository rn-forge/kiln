"""`kiln config-update`, `config-upgrade` and `pin`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rn_forge.commons import generation
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.runtime.console import console

from rn_forge.kiln import archetypes
from rn_forge.kiln.commands import output
from rn_forge.kiln.config import CONFIG_PATH
from rn_forge.kiln.modules.core import cycle, kiln_ref, umbrella
from rn_forge.kiln.modules.core.config import catalog
from rn_forge.kiln.modules.core.config.manager import ConfigManager

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
    settled = (generation.Action.UNCHANGED, generation.Action.SKIP)
    rows = output.change_rows(
        [
            change
            for change in cycle.preview(root, resolution.config)
            if change.action not in settled
        ]
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

    catalog.write(root, resolution.config)
    result = cycle.apply(root, provenance=resolution.provenance_metadata())
    change_rows = output.change_rows(result.changes)
    output.emit_rows({"root": str(root), "artifacts": change_rows}, change_rows)
    output.fail_on_errors(root)


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
    old = table.get("ref", archetypes.KILN_REF)
    if show:
        console.print(old)
        return
    ref = ref.strip()
    if not ref:
        track = table.get("track")
        if not track:
            raise AppException(
                "kiln.track-missing: no [kiln] track to follow "
                "\u2014 pass a branch, tag or SHA"
            )
        ref = str(track)
    if kiln_ref.SHA.match(ref):
        new, track = ref, None
    elif kiln_ref.TAG.match(ref):
        kiln_ref.resolve(ref)  # an unknown tag is an error
        new, track = ref, None
    else:
        new, track = kiln_ref.resolve(ref), ref
    if "kiln" not in document:
        document["kiln"] = {}
    document["kiln"]["ref"] = new
    if track is None:
        document["kiln"].pop("track", None)
    else:
        document["kiln"]["track"] = track
    DocumentUtils.write_document(path, document)
    console.info("kiln ref {} \u2192 {}", old, new)
