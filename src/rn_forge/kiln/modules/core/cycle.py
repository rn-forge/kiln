"""The apply cycle: kiln's config and modules, handed to tooling's generation engine.

Every artifact is rendered and classified before anything is written; the
engine then stages, backs up and swaps them in, and writes `state.json` last.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path

from rn_forge.commons import generation
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.hashing import ContentHash
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import (
    Action,
    ApplyResult,
    ArtifactKind,
    Plan,
    StateEntry,
)
from rn_forge.commons.lang.types import JsonValue
from rn_forge.tooling.install.home import rnf_home

from rn_forge.kiln import __version__
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig
from rn_forge.kiln.modules.base import ModuleRegistry
from rn_forge.kiln.modules.core import umbrella
from rn_forge.kiln.modules.core.config.manager import PROVENANCE_KEY, ConfigManager

__all__ = ["CycleRefused", "adoption_plan", "apply", "fence", "plan", "unfenced"]

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
    adopt: bool = False,
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
        adopt: Plan as the first apply of an existing repository (`kiln init`):
            any recorded state is ignored, and a managed file already equal to
            its render is `unchanged` instead of a conflict.

    Raises:
        CycleRefused: A legacy kiln tree is present.
        AppException: The config is invalid.
    """
    return _prepare(root, force, registry, home, provenance, adopt)[1]


def adoption_plan(
    root: Path, config: KilnConfig, *, registry: ModuleRegistry | None = None
) -> Plan:
    """The first-apply plan for an existing repository under *config*, writing nothing.

    Unlike :func:`plan` this needs no `config.toml` on disk, and ignores any
    `state.json`: a byte-identical whole file is `unchanged`, and every other
    existing artifact is a `conflict`.
    """
    artifacts = _artifacts(ConfigManager(registry), config, root)
    return _adopted(root, generation.plan(root, artifacts, {}))


def apply(
    root: Path,
    *,
    force: Iterable[str] = (),
    dry_run: bool = False,
    registry: ModuleRegistry | None = None,
    home: Path | None = None,
    verify: Callable[[], None] | None = None,
    provenance: Mapping[str, JsonValue] | None = None,
    adopt: bool = False,
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
    store, planned = _prepare(root, force, registry, home, provenance, adopt)
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
    adopt: bool = False,
) -> tuple[StateStore[StateEntry], Plan]:
    refused = umbrella.legacy(root / umbrella.UMBRELLA, (home or rnf_home()) / "kiln")
    if refused:
        raise CycleRefused(refused)

    manager = ConfigManager(registry)
    config = manager.load(root)
    artifacts = _artifacts(manager, config, root)
    unfenced = _unfenced(root, artifacts)
    if unfenced:
        raise CycleRefused(unfenced)

    state_path = root / umbrella.STATE_PATH
    metadata: dict[str, JsonValue] = {
        "kiln_version": __version__,
        "config_hash": ContentHash.of((root / CONFIG_PATH).read_text(encoding="utf-8")),
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
    entries = {} if adopt else _without_converted(store.load(), artifacts)
    planned = generation.plan(root, artifacts, entries, force=force)
    return store, _adopted(root, planned) if adopt else planned


def _artifacts(
    manager: ConfigManager, config: KilnConfig, root: Path
) -> list[generation.Artifact]:
    return [
        artifact
        for module in manager.modules_for(config)
        for artifact in module.artifacts(config, root)
    ]


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


def unfenced(root: Path, config: KilnConfig) -> list[Finding]:
    """The `core.block-unfenced` findings for *config* in *root*, as `plan` would raise them."""
    return _unfenced(root, _artifacts(ConfigManager(), config, root))


def fence(root: Path, config: KilnConfig) -> list[str]:
    """Fence each unfenced file `_unfenced` would report; return the paths rewritten.

    The file becomes kiln's empty block, a blank line, then the file without
    its `[importlinter]` section: that line and every line after it up to,
    not including, the next line that starts with `[`.
    """
    artifacts = {a.path: a for a in _artifacts(ConfigManager(), config, root)}
    rewritten = sorted(str(finding.path) for finding in unfenced(root, config))
    for path in rewritten:
        block = artifacts[path].block
        assert block is not None
        kept: list[str] = []
        skipping = False
        for line in _text(root / path).splitlines(keepends=True):
            if line.rstrip("\r\n") == "[importlinter]":
                skipping = True
            elif skipping and line.startswith("["):
                skipping = False
            if not skipping:
                kept.append(line)
        (root / path).write_text(
            block.begin.strip() + "\n" + block.end.strip() + "\n\n" + "".join(kept),
            encoding="utf-8",
        )
    return rewritten


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


def _adopted(root: Path, planned: Plan) -> Plan:
    """*planned* with each byte-identical whole-file conflict settled as unchanged."""
    changes = tuple(
        dataclasses.replace(change, action=Action.UNCHANGED)
        if change.action is Action.CONFLICT
        and change.kind is ArtifactKind.MANAGED
        and change.artifact is not None
        and _bytes(root / change.path) == change.artifact.content.encode("utf-8")
        else change
        for change in planned.changes
    )
    return Plan(changes)


def _bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None
