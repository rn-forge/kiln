"""The apply cycle: kiln's config and modules, handed to tooling's generation engine.

Every artifact is rendered and classified before anything is written; the
engine then stages, backs up and swaps them in, and writes `state.json` last.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rn_forge.commons import generation
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import ConfigFormat, DocumentUtils
from rn_forge.commons.fs.hashing import ContentHash
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import (
    ApplyResult,
    ArtifactKind,
    Plan,
    StateEntry,
)
from rn_forge.commons.lang.collections import DictUtils
from rn_forge.commons.lang.types import JsonValue
from rn_forge.tooling.install.home import rnf_home

from rn_forge.kiln import __version__
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig
from rn_forge.kiln.modules.base import ModuleRegistry, StarterModule
from rn_forge.kiln.modules.core import settle, umbrella
from rn_forge.kiln.modules.core.config import catalog
from rn_forge.kiln.modules.core.config.manager import (
    PROVENANCE_KEY,
    REPO_LAYER,
    ConfigManager,
)
from rn_forge.kiln.modules.core.process import run

__all__ = [
    "SCAFFOLDED_KEY",
    "CycleRefused",
    "Footprint",
    "Prepared",
    "apply",
    "classify",
    "execute",
    "plan",
    "prepare",
    "record_scaffolded",
]

SCAFFOLDED_KEY = "scaffolded"

UNFENCED_CODE = "core.block-unfenced"

_NO_APPEND = frozenset({".importlinter"})
"""Files a block may not be appended to: a second `[importlinter]` section is
a `configparser` error, so an unfenced file is refused instead."""


@dataclass(frozen=True)
class Prepared:
    """A classified apply and the config and state store it uses."""

    store: StateStore[StateEntry]
    plan: Plan
    config: KilnConfig
    candidate: bool

    def write_paths(self) -> set[Path]:
        """Return the repository-relative footprint of this apply."""
        paths = {Path(change.path) for change in self.plan.changes}
        paths.add(umbrella.STATE_PATH)
        if self.candidate:
            paths.add(CONFIG_PATH)
        if self.config.docs_profile == "mkdocs":
            paths.update((Path("docs"), Path("mkdocs.yml")))
        return paths


class Footprint:
    """Snapshot repository-relative files and directory trees for recovery."""

    def __init__(self, root: Path, paths: Iterable[Path]) -> None:
        self._paths = tuple(root / path for path in paths)
        files, self._directories = self._contents()
        self._files = {path: path.read_bytes() for path in files}

    def _contents(self) -> tuple[set[Path], set[Path]]:
        files: set[Path] = set()
        directories: set[Path] = set()
        for path in self._paths:
            if path.is_dir():
                directories.add(path)
                for child in path.rglob("*"):
                    (directories if child.is_dir() else files).add(child)
            elif path.is_file():
                files.add(path)
        return files, directories

    def restore(self) -> None:
        """Restore original bytes and remove files and directories created within the footprint."""
        files, directories = self._contents()
        for path in files - self._files.keys():
            path.unlink()
        for path in sorted(directories - self._directories, reverse=True):
            path.rmdir()
        for path in self._directories:
            path.mkdir(parents=True, exist_ok=True)
        for path, content in self._files.items():
            if not path.is_file() or path.read_bytes() != content:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)


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
    return prepare(
        root, force=force, registry=registry, home=home, provenance=provenance
    ).plan


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
    return execute(
        root,
        prepare(
            root,
            force=force,
            registry=registry,
            home=home,
            provenance=provenance,
            starters=starters,
        ),
        dry_run=dry_run,
        finalize=verify,
    )


def execute(
    root: Path,
    prepared: Prepared,
    *,
    dry_run: bool = False,
    finalize: Callable[[], None] | None = None,
    post: Callable[[], None] | None = None,
) -> ApplyResult:
    """Execute a prepared plan, with callbacks before and after the state write."""
    footprint = None if dry_run else Footprint(root, prepared.write_paths())
    try:
        if prepared.candidate and not dry_run:
            catalog.write(root, prepared.config)
        result = generation.apply(
            root,
            prepared.plan,
            prepared.store,
            staging_dir=root / umbrella.RENDERED,
            backup_dir=root / umbrella.BACKUPS,
            verify=finalize,
            dry_run=dry_run,
        )
        if post is not None and not dry_run:
            post()
        return result
    except BaseException:
        if footprint is not None:
            footprint.restore()
        raise


def _refreshed(
    recorded: Mapping[str, JsonValue], document: Mapping[str, Any]
) -> dict[str, JsonValue]:
    """*recorded* provenance, with each key the committed *document* changed re-attributed to the repo."""
    committed = DictUtils.flatten(document)
    refreshed: dict[str, JsonValue] = {}
    for path, entry in recorded.items():
        if (
            path in committed
            and isinstance(entry, Mapping)
            and entry.get("value") != committed[path]
        ):
            refreshed[path] = {"layer": REPO_LAYER, "value": committed[path]}
        else:
            refreshed[path] = entry
    return refreshed


def prepare(
    root: Path,
    *,
    config: KilnConfig | None = None,
    force: Iterable[str] = (),
    registry: ModuleRegistry | None = None,
    home: Path | None = None,
    provenance: Mapping[str, JsonValue] | None = None,
    starters: str | None = None,
) -> Prepared:
    """Classify the artifacts of the committed config or a validated candidate.

    Carried-forward provenance re-attributes a key whose committed value changed
    to the `repo` layer.
    """
    refused = umbrella.legacy(root / umbrella.UMBRELLA, (home or rnf_home()) / "kiln")
    if refused:
        raise CycleRefused(refused)

    manager = ConfigManager(registry)
    candidate = config is not None
    if config is None:
        config = manager.load(root)
        document = DocumentUtils.read(root / CONFIG_PATH)
    else:
        document = DocumentUtils.loads(
            catalog.render(config, header=catalog.CONFIG_HEADER), ConfigFormat.TOML
        )
    artifacts = _artifacts(manager, config, root, starters=starters)
    unfenced = _unfenced(root, artifacts)
    if unfenced:
        raise CycleRefused(unfenced)

    state_path = root / umbrella.STATE_PATH
    metadata: dict[str, JsonValue] = {
        "kiln_version": __version__,
        "config_hash": ContentHash.of(
            json.dumps(
                document,
                sort_keys=True,
                separators=(",", ":"),
            )
        ),
    }
    if provenance is not None:
        metadata[PROVENANCE_KEY] = dict(provenance)
    elif state_path.is_file():
        previous = StateStore(
            state_path,
            entry_type=StateEntry,
            schema_version=umbrella.STATE_SCHEMA_VERSION,
        )
        recorded = previous.metadata.get(PROVENANCE_KEY)
        if isinstance(recorded, Mapping):
            metadata[PROVENANCE_KEY] = _refreshed(recorded, document)
        elif recorded is not None:
            metadata[PROVENANCE_KEY] = recorded
        scaffolded = previous.metadata.get(SCAFFOLDED_KEY)
        if scaffolded is not None:
            metadata[SCAFFOLDED_KEY] = scaffolded

    store = StateStore(
        state_path,
        entry_type=StateEntry,
        schema_version=umbrella.STATE_SCHEMA_VERSION,
        metadata=metadata,
    )
    entries = _without_converted(store.load(), artifacts)
    planned = classify(root, artifacts, entries, force=force)
    return Prepared(store, planned, config, candidate)


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
    findings: list[Finding] = []
    for artifact in artifacts:
        path = root / artifact.path
        if (
            artifact.block is None
            or artifact.path not in _NO_APPEND
            or not path.is_file()
        ):
            continue
        text = _text(path)
        if text.strip() and artifact.block.extract(text) is None:
            findings.append(
                Finding(UNFENCED_CODE, Severity.ERROR, message, path=artifact.path)
            )
    return findings


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


def record_scaffolded(directory: Path) -> None:
    """Record in `state.json` the files `kiln new` wrote that no artifact owns.

    Args:
        directory: The new repository, already `git init`-ed.
    """
    listed = run(
        "git-ls-files",
        "git",
        "-C",
        directory,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    ).stdout
    state_path = directory / umbrella.STATE_PATH
    state = DocumentUtils.read(state_path)
    owned = {entry["path"] for entry in state["entries"].values()}
    state["metadata"][SCAFFOLDED_KEY] = sorted(
        path
        for path in (listed or "").split("\0")
        if path and path not in owned and not path.startswith(".rn-forge/")
    )
    state_path.write_text(
        DocumentUtils.dumps(state, ConfigFormat.JSON), encoding="utf-8"
    )
