"""The apply cycle: kiln's config and modules, handed to tooling's generation engine.

Every artifact is rendered and classified before anything is written; the
engine then stages, backs up and swaps them in, and writes `state.json` last.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path

from rn_forge.commons import generation
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.fs.hashing import ContentHash
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import (
    ApplyResult,
    ArtifactKind,
    Plan,
    StateEntry,
)
from rn_forge.commons.lang.types import JsonValue
from rn_forge.tooling.install.home import rnf_home

from rn_forge.kiln import __version__
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig
from rn_forge.kiln.modules.base import ModuleRegistry, StarterModule
from rn_forge.kiln.modules.core import settle, umbrella
from rn_forge.kiln.modules.core.config.manager import PROVENANCE_KEY, ConfigManager

__all__ = [
    "CycleRefused",
    "apply",
    "classify",
    "plan",
]

STATE_SCHEMA_VERSION = "1"

UNFENCED_CODE = "core.block-unfenced"

_NO_APPEND = frozenset({".importlinter"})
"""Files a block may not be appended to: a second `[importlinter]` section is
a `configparser` error, so an unfenced file is refused instead."""


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
    provenance: Mapping[str, JsonValue] | None = None,
) -> Plan:
    """Render every enabled module's artifacts and classify them, writing nothing.

    Args:
        root: The repo root.
        force: Paths or artifact keys whose blocking classification is approved.
        registry: The modules to draw from; this kiln's own by default.
        home: `$RNF_HOME`, checked for a legacy tree; resolved from the
            environment by default.
        provenance: `config_provenance` metadata to record on the next apply,
            in :meth:`~rn_forge.kiln.modules.core.config.manager.Resolution.provenance_metadata`'s
            shape — `kiln new` and `kiln config-update`/`config-upgrade` pass their
            fresh `Resolution`'s, overriding any value carried forward from a
            previous `state.json`.

    Raises:
        CycleRefused: A legacy kiln tree is present.
        AppException: The config is invalid.
    """
    return _prepare(root, force, registry, home, provenance)[1]


def apply(
    root: Path,
    *,
    force: Iterable[str] = (),
    dry_run: bool = False,
    registry: ModuleRegistry | None = None,
    home: Path | None = None,
    verify: Callable[[], None] | None = None,
    provenance: Mapping[str, JsonValue] | None = None,
    starters: str | None = None,
) -> ApplyResult:
    """Plan, then apply transactionally; see :func:`plan` for the arguments.

    Args:
        dry_run: Classify and report, write nothing.
        verify: Called after every write and before `state.json` is written;
            raising from it rolls the whole apply back.
        starters: The path prefix under which an absent starter file may be
            created: `""` for the whole repository, `None` for nowhere.

    Raises:
        CycleRefused: A legacy kiln tree is present.
        AppException: The config is invalid, the plan has an unapproved
            conflict, drift or missing artifact, or a write failed (after the
            tree and `state.json` were restored).
    """
    store, planned = _prepare(root, force, registry, home, provenance, starters)
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
    provenance: Mapping[str, JsonValue] | None = None,
    starters: str | None = None,
) -> tuple[StateStore[StateEntry], Plan]:
    refused = umbrella.legacy(root / umbrella.UMBRELLA, (home or rnf_home()) / "kiln")
    if refused:
        raise CycleRefused(refused)

    manager = ConfigManager(registry)
    config = manager.load(root)
    artifacts = _artifacts(manager, config, root, starters=starters)
    unfenced = _unfenced(root, artifacts)
    if unfenced:
        raise CycleRefused(unfenced)

    state_path = root / umbrella.STATE_PATH
    metadata: dict[str, JsonValue] = {
        "kiln_version": __version__,
        "config_hash": ContentHash.of(
            json.dumps(
                DocumentUtils.read(root / CONFIG_PATH),
                sort_keys=True,
                separators=(",", ":"),
            )
        ),
    }
    if provenance is not None:
        metadata[PROVENANCE_KEY] = dict(provenance)
    elif state_path.is_file():
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
    entries = _without_converted(store.load(), artifacts)
    planned = classify(root, artifacts, entries, force=force)
    return store, planned


def classify(
    root: Path,
    artifacts: Iterable[generation.Artifact],
    entries: Mapping[str, StateEntry],
    *,
    force: Iterable[str] = (),
) -> Plan:
    """Classify *artifacts* against *entries* as the engine does, then settle derived files.

    The one place kiln calls the engine's planner. A file with a derived region
    (see :mod:`~rn_forge.kiln.modules.core.derived`) is compared with that
    region emptied.
    """
    return settle.settle(
        root, generation.plan(root, artifacts, entries, force=force), entries
    )


def _artifacts(
    manager: ConfigManager,
    config: KilnConfig,
    root: Path,
    *,
    starters: str | None = None,
) -> list[generation.Artifact]:
    kept: list[generation.Artifact] = []
    for module in manager.modules_for(config):
        held: set[str] = set()
        if isinstance(module, StarterModule):
            held.update(module.starters(config, root))
        kept += [
            artifact
            for artifact in module.artifacts(config, root)
            if artifact.path not in held
            or (root / artifact.path).exists()
            or (starters is not None and artifact.path.startswith(starters))
        ]
    return kept


def _unfenced(root: Path, artifacts: Sequence[generation.Artifact]) -> list[Finding]:
    """A `core.block-unfenced` error for each `_NO_APPEND` file with content but no markers.

    A blank file holds nothing the block could duplicate, so it is appended to.
    """
    message = (
        "kiln's part of this file is not fenced — put `# BEGIN rn-forge kiln` "
        "above its first line and `# END rn-forge kiln` after kiln's last "
        "contract, move any contract of your own below the END marker, then "
        "run `kiln apply --force .importlinter`"
    )
    return [
        Finding(UNFENCED_CODE, Severity.ERROR, message, path=artifact.path)
        for artifact in artifacts
        if artifact.block is not None
        and artifact.path in _NO_APPEND
        and (root / artifact.path).is_file()
        and _text(root / artifact.path).strip()
        and artifact.block.extract(_text(root / artifact.path)) is None
    ]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _without_converted(
    entries: Mapping[str, StateEntry], artifacts: Sequence[generation.Artifact]
) -> dict[str, StateEntry]:
    """*entries* without the whole-file entries of files kiln now owns a block of.

    A file kiln used to own whole and now owns a block of is forgotten as a
    whole file, so the plan does not delete it.
    """
    converted = {a.path for a in artifacts if a.block is not None}
    return {
        key: entry
        for key, entry in entries.items()
        if entry.kind is ArtifactKind.BLOCK or entry.path not in converted
    }
