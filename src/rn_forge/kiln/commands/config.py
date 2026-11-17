"""`kiln config-update`, `config-upgrade` and `pin`."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from rn_forge.commons import generation
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import StateEntry
from rn_forge.commons.runtime.console import console

from rn_forge.kiln import archetypes
from rn_forge.kiln.commands import output
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle, umbrella
from rn_forge.kiln.modules.core.config import catalog
from rn_forge.kiln.modules.core.config.manager import ConfigManager
from rn_forge.kiln.modules.core.config.schema import KilnPin

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
    rows = _config_change_rows(root, manager, resolution.config)
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


def _config_change_rows(
    root: Path, manager: ConfigManager, config: KilnConfig
) -> list[dict[str, str]]:
    """The artifacts a fresh `config.toml` matching *config* would change on apply."""
    artifacts = [
        artifact
        for module in manager.modules_for(config)
        for artifact in module.artifacts(config, root)
    ]
    store = StateStore(
        root / umbrella.STATE_PATH,
        entry_type=StateEntry,
        schema_version=cycle.STATE_SCHEMA_VERSION,
    )
    planned = cycle.classify(root, artifacts, store.load())
    settled = (generation.Action.UNCHANGED, generation.Action.SKIP)
    changed = [c for c in planned.changes if c.action not in settled]
    return output.change_rows(changed)


def pin(ref: str) -> None:
    """Set the current repository's `[kiln] ref` to REF, and write nothing else.

    Does not apply and does not check that REF exists; `task kiln:pin` does both.

    Raises:
        AppException: REF is empty or only whitespace.
    """
    ref = ref.strip()
    if not ref:
        raise AppException("a kiln ref is required")
    root = umbrella.find_root(Path.cwd())
    config = ConfigManager().load(root)
    old = config.document.kiln.ref if config.document.kiln else archetypes.KILN_REF
    document = config.document.model_copy(update={"kiln": KilnPin(ref=ref)})
    catalog.write(root, dataclasses.replace(config, document=document))
    console.info("kiln ref {} \u2192 {}", old, ref)
