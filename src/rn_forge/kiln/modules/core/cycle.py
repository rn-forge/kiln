"""The apply cycle: kiln's config and modules, handed to tooling's generation engine.

Every artifact is rendered and classified before anything is written; the
engine then stages, backs up and swaps them in, and writes `state.json` last.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding
from rn_forge.commons.fs.hashing import ContentHash
from rn_forge.commons.lang.types import JsonValue
from rn_forge.tooling import generation
from rn_forge.tooling.generation import ApplyResult, Plan, StateEntry
from rn_forge.tooling.install.home import rnf_home
from rn_forge.tooling.state import StateStore

from rn_forge.kiln import __version__
from rn_forge.kiln.config import CONFIG_PATH
from rn_forge.kiln.modules.base import ModuleRegistry
from rn_forge.kiln.modules.core import umbrella
from rn_forge.kiln.modules.core.config.manager import PROVENANCE_KEY, ConfigManager

__all__ = ["CycleRefused", "apply", "plan"]

STATE_SCHEMA_VERSION = "1"


class CycleRefused(AppException):
    """kiln refused to plan: :attr:`findings` says why."""

    findings: tuple[Finding, ...]

    def __init__(self, findings: Iterable[Finding]) -> None:
        self.findings = tuple(findings)
        super().__init__(
            "Refusing to apply: {}",
            "; ".join(str(finding) for finding in self.findings),
        )


def plan(
    root: Path,
    *,
    force: Iterable[str] = (),
    registry: ModuleRegistry | None = None,
    home: Path | None = None,
) -> Plan:
    """Render every enabled module's artifacts and classify them, writing nothing.

    Args:
        root: The repo root.
        force: Paths or artifact keys whose blocking classification is approved.
        registry: The modules to draw from; this kiln's own by default.
        home: `$RNF_HOME`, checked for a legacy tree; resolved from the
            environment by default.

    Raises:
        CycleRefused: A legacy kiln tree is present.
        AppException: The config is invalid.
    """
    return _prepare(root, force, registry, home)[1]


def apply(
    root: Path,
    *,
    force: Iterable[str] = (),
    dry_run: bool = False,
    registry: ModuleRegistry | None = None,
    home: Path | None = None,
    verify: Callable[[], None] | None = None,
) -> ApplyResult:
    """Plan, then apply transactionally; see :func:`plan` for the arguments.

    Args:
        dry_run: Classify and report, write nothing.
        verify: Called after every write and before `state.json` is written;
            raising from it rolls the whole apply back.

    Raises:
        CycleRefused: A legacy kiln tree is present.
        AppException: The config is invalid, the plan has an unapproved
            conflict, drift or missing artifact, or a write failed (after the
            tree and `state.json` were restored).
    """
    store, planned = _prepare(root, force, registry, home)
    return generation.apply(
        root,
        planned,
        store,
        staging_dir=root / umbrella.RENDERED,
        backup_dir=root / umbrella.BACKUPS,
        verify=verify,
        dry_run=dry_run,
    )


def _prepare(
    root: Path,
    force: Iterable[str],
    registry: ModuleRegistry | None,
    home: Path | None,
) -> tuple[StateStore[StateEntry], Plan]:
    refused = umbrella.legacy(root / umbrella.UMBRELLA, (home or rnf_home()) / "kiln")
    if refused:
        raise CycleRefused(refused)

    manager = ConfigManager(registry)
    config = manager.load(root)
    artifacts = [
        artifact
        for module in manager.modules_for(config)
        for artifact in module.artifacts(config)
    ]

    state_path = root / umbrella.STATE_PATH
    metadata: dict[str, JsonValue] = {
        "kiln_version": __version__,
        "config_hash": ContentHash.of((root / CONFIG_PATH).read_text(encoding="utf-8")),
    }
    if state_path.is_file():
        previous = StateStore(
            state_path, entry_type=StateEntry, schema_version=STATE_SCHEMA_VERSION
        )
        recorded = previous.metadata.get(PROVENANCE_KEY)
        if recorded is not None:
            metadata[PROVENANCE_KEY] = recorded

    store = StateStore(
        state_path,
        entry_type=StateEntry,
        schema_version=STATE_SCHEMA_VERSION,
        metadata=metadata,
    )
    return store, generation.plan(root, artifacts, store.load(), force=force)
