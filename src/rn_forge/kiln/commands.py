"""The commands kiln's CLI exposes.

A command function is all that is written here. `CliApp.from_config` builds
the application around it — the root callback, the standard
`--log-level`/`--json` flags, the error-to-exit-code mapping — from the
declaration in `cli.toml`.

Nothing here imports Typer: a parameter without a default is a positional
argument, one with a default is an option. Failure is an `AppException`,
which `CliApp` maps to exit code 1.
"""

from __future__ import annotations

import difflib
from collections.abc import Sequence
from importlib import metadata
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import ConfigFormat, DocumentUtils
from rn_forge.commons.lang.collections import DictUtils
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.tooling import generation
from rn_forge.tooling.generation import StateEntry
from rn_forge.tooling.install import doctor as lifecycle_doctor
from rn_forge.tooling.state import StateStore

from rn_forge.kiln import archetypes, checks
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig
from rn_forge.kiln.modules.core import cycle, umbrella
from rn_forge.kiln.modules.core.config.manager import ConfigManager
from rn_forge.kiln.modules.core.config.sources import Source
from rn_forge.kiln.modules.docs.nav import update_nav
from rn_forge.kiln.modules.docs.scaffold import scaffold as docs_scaffold
from rn_forge.kiln.modules.instructions.scaffold import (
    scaffold as instructions_scaffold,
)
from rn_forge.kiln.modules.python.scaffold import scaffold as python_scaffold
from rn_forge.kiln.modules.registry import builtin
from rn_forge.kiln.product import PRODUCT

__all__ = [
    "apply",
    "config_update",
    "config_upgrade",
    "diff",
    "docs_nav",
    "doctor",
    "new",
    "self_doctor",
    "version",
]

_DISTRIBUTION = "rn-forge-kiln"

_CONFIG_HEADER = (
    "# The one hand-authored input kiln reads (kiln ADR-0004). Edit this, then run\n"
    "# `kiln apply`. Everything else under .rn-forge/kiln/ is kiln's.\n"
)

# `new`'s config-setting flags: every one of them must be backed by a
# registered module's `Option`, verified by `tests/test_new.py`.
_FLAG_NAMES = ("archetype", "docs", "backend", "frontend")


def doctor(path: Path, only: str | None = None) -> None:
    """Run the render-free checks over PATH's committed files.

    Prints each finding and raises `AppException` if any is an error.
    """
    findings = checks.run(path.resolve(), only)

    for finding in findings:
        console.error("{}", finding)

    errors = [finding for finding in findings if finding.is_error]
    if errors:
        raise AppException("{} check(s) failed in {}", len(errors), path)


def self_doctor(json: bool = False) -> None:
    """Check kiln's own install and health — the lifecycle `doctor` verb.

    `[cli.lifecycle]` excludes `doctor`, since `kiln doctor` already means
    inspecting a generated repository; this reaches the same install checks
    `rn_forge.tooling.install.lifecycle.doctor` gives every other lifecycle
    tool, under a name that does not collide.

    Raises:
        AppException: Any finding is an error.
    """
    if json:
        console.set_mode(OutputMode.JSON)
    findings = lifecycle_doctor(PRODUCT)
    if console.mode is OutputMode.JSON:
        console.json({"findings": [finding.as_dict() for finding in findings]})
    else:
        for finding in findings:
            console.print(f"{finding.severity}: {finding}", markup=False)

    errors = [finding for finding in findings if finding.is_error]
    if errors:
        raise AppException("{} check(s) failed", len(errors))


def docs_nav(path: Path) -> None:
    """Regenerate the nav block in PATH's `mkdocs.yml` from its docs tree.

    `kiln doctor --only docs-nav` is the check that the block is current.
    """
    mkdocs_path = path / "mkdocs.yml"
    updated, changed = update_nav(mkdocs_path, path / "docs")
    if not changed:
        console.info("no change")
        return
    mkdocs_path.write_text(updated, encoding="utf-8")
    console.success("updated {}", mkdocs_path)


def new(
    directory: Path,
    archetype: str = "",
    docs: str = "mkdocs",
    backend: str | None = None,
    frontend: str | None = None,
    config: str | None = None,
    allow_untested: bool = False,
    dry_run: bool = False,
    yes: bool = False,
    json: bool = False,
) -> None:
    """Create a repository at DIRECTORY, previewing unless `--yes` is given.

    Without `--yes`, prints the resolved config and the artifacts it would
    produce, and writes nothing. With `--yes`, writes `config.toml`, scaffolds
    the tree and applies it (kiln ADR-0004).

    `--backend` and `--frontend` are omitted (left `None`) unless given, so a
    config-selected value or the archetype's own default survives; passing
    either for an archetype that does not declare it is refused, naming the
    key.

    Raises:
        AppException: `--archetype` is missing or unknown, a flag names an
            untested value without `--allow-untested`, DIRECTORY is non-empty,
            or the config, scaffold, apply or check step fails.
    """
    if json:
        console.set_mode(OutputMode.JSON)
    if not archetype:
        raise AppException("--archetype is required")

    manifest = archetypes.load(archetype)
    flags = _flag_layer(
        archetype=archetype,
        docs=docs,
        manifest=manifest,
        allow_untested=allow_untested,
        backend=backend,
        frontend=frontend,
    )
    DictUtils.set(flags, "repository.name", directory.name)

    manager = ConfigManager()
    source = Source.parse(config) if config else None
    resolution = manager.resolve(flags=flags, source=source)
    resolved = resolution.config

    if not yes or dry_run:
        rows = _preview_rows(directory, resolved, manager)
        _report(directory, resolved, rows)
        return

    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise AppException("{} is not empty", directory)

    _write_config(directory, resolved)

    python_scaffold(directory, resolved)
    docs_scaffold(directory, resolved)
    instructions_scaffold(directory, resolved)

    result = cycle.apply(directory, provenance=resolution.provenance_metadata())
    rows = _change_rows(result.changes)
    _report(directory, resolved, rows)
    _fail_on_errors(directory)


def apply(
    force: list[str] | None = None, dry_run: bool = False, json: bool = False
) -> None:
    """Reconcile the current repository's rendered artifacts (kiln ADR-0004).

    Plans first, refusing any `--force` value that does not name a reported,
    blocking change; then applies, then runs `kiln doctor`'s checks.

    Raises:
        AppException: A `--force` value names no reported change or a
            non-blocking one, an unforced change is blocking, or a check
            after the apply reports an error.
    """
    if json:
        console.set_mode(OutputMode.JSON)
    root = umbrella.find_root(Path.cwd())
    force_values = tuple(force or ())

    planned = cycle.plan(root, force=force_values)
    _validate_force(planned, force_values)

    result = cycle.apply(root, force=force_values, dry_run=dry_run)
    rows = _change_rows(result.changes)
    _emit({"root": str(root), "artifacts": rows}, rows)

    if not dry_run:
        _fail_on_errors(root)


def config_update(
    dry_run: bool = False, apply: bool = False, json: bool = False
) -> None:
    """Re-resolve the committed config against this kiln's current defaults.

    Prints the artifacts that would change and writes nothing. `--apply`
    writes the re-merged `config.toml` and runs the full `kiln apply` (kiln
    ADR-0004, the config lifecycle).

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


def diff(artifact: str | None = None, json: bool = False) -> None:
    """Unified diff of on-disk content against a fresh render, writing nothing.

    With no `--artifact`, every managed and block artifact whose disk content
    differs from its fresh render is diffed; `--artifact` (a key or a path)
    limits it to one. A defaulted parameter is always an option in this
    framework without a `typer.Argument` marker (see `new`'s own
    `--archetype`), which kiln's commands never import, so this is `--artifact`
    rather than the design table's bare positional.

    Raises:
        AppException: ARTIFACT names no known artifact, or a difference was
            found — `diff(1)`'s own exit-1 convention.
    """
    if json:
        console.set_mode(OutputMode.JSON)
    root = umbrella.find_root(Path.cwd())
    changes = cycle.plan(root).changes

    if artifact is not None:
        changes = [c for c in changes if artifact in (c.key, c.path)]
        if not changes:
            raise AppException("{} is not a known artifact", artifact)

    diffs = _diffs(root, changes)
    if console.mode is OutputMode.JSON:
        console.json({"diffs": [{"path": path, "diff": text} for path, text in diffs]})
    else:
        for _, text in diffs:
            console.print(text, markup=False)

    if diffs:
        raise AppException("{} artifact(s) differ from disk", len(diffs))


def version(json: bool = False) -> None:
    """Print kiln's installed distribution version."""
    installed = metadata.version(_DISTRIBUTION)
    if json:
        console.set_mode(OutputMode.JSON)
    if console.mode is OutputMode.JSON:
        console.json({"version": installed})
    else:
        console.print(installed)


def _diffs(root: Path, changes: Sequence[generation.Change]) -> list[tuple[str, str]]:
    """`(path, unified diff)` for every managed/block change that differs from disk."""
    results: list[tuple[str, str]] = []
    for change in changes:
        artifact = change.artifact
        if artifact is None or artifact.kind is generation.ArtifactKind.SEEDED:
            continue
        disk = _disk_content(root, artifact)
        fresh = artifact.content
        if disk == fresh:
            continue
        text = "".join(
            difflib.unified_diff(
                (disk or "").splitlines(keepends=True),
                fresh.splitlines(keepends=True),
                fromfile=artifact.path,
                tofile=artifact.path,
            )
        )
        results.append((artifact.path, text))
    return results


def _disk_content(root: Path, artifact: generation.Artifact) -> str | None:
    """*artifact*'s current on-disk content — a block's body, for a block artifact."""
    path = root / artifact.path
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if artifact.block is None:
        return text
    return artifact.block.extract(text)


def _flag_layer(
    *,
    archetype: str,
    docs: str,
    manifest: archetypes.Archetype,
    allow_untested: bool,
    backend: str | None = None,
    frontend: str | None = None,
) -> dict[str, object]:
    """The dotted-key mapping `new`'s flags set, refusing an untested value.

    `backend`/`frontend` are omitted from the map entirely when `None`, so a
    config value or the archetype's own default survives an omitted CLI
    selector.
    """
    all_options = {
        option.flag: option
        for module in builtin().modules
        for option in module.options()
    }
    provided: dict[str, str | None] = {
        "archetype": archetype,
        "docs": docs,
        "backend": backend,
        "frontend": frontend,
    }
    untested: list[str] = []
    flags: dict[str, object] = {}
    for flag_name in _FLAG_NAMES:
        value = provided[flag_name]
        if value is None:
            continue
        if value in manifest.untested.get(flag_name, []) and not allow_untested:
            untested.append(f"--{flag_name}={value}")
            continue
        option = all_options[flag_name]
        key = option.key.replace("<archetype>", archetype)
        DictUtils.set(flags, key, value)
    if untested:
        raise AppException(
            "untested value(s) {} — pass --allow-untested to proceed",
            ", ".join(untested),
        )
    return flags


def _preview_rows(
    directory: Path, config: KilnConfig, manager: ConfigManager
) -> list[dict[str, str]]:
    """One row per artifact `kiln new` would render, classified against nothing."""
    rows: list[dict[str, str]] = []
    for module in manager.modules_for(config):
        for artifact in module.artifacts(config, directory):
            action = generation.classify(directory, artifact, None)
            rows.append(
                {
                    "key": artifact.key,
                    "path": artifact.path,
                    "kind": artifact.kind.value,
                    "action": action.value,
                }
            )
    return rows


def _change_rows(changes: Sequence[generation.Change]) -> list[dict[str, str]]:
    """`ApplyResult.changes` (or a `Plan`'s), as `{key, path, kind, action}` rows."""
    return [
        {
            "key": change.key,
            "path": change.path,
            "kind": change.kind.value,
            "action": change.action.value,
        }
        for change in changes
    ]


def _write_config(directory: Path, config: KilnConfig) -> None:
    """Write *config* as `directory`'s committed `config.toml`, with kiln's header."""
    config_path = directory / CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        _CONFIG_HEADER + DocumentUtils.dumps(config.to_document(), ConfigFormat.TOML),
        encoding="utf-8",
    )


def _config_reresolve(
    *, allow_schema_upgrade: bool, dry_run: bool, run_apply: bool, json: bool
) -> None:
    """Shared body of `config-update` and `config-upgrade` (kiln ADR-0004)."""
    if json:
        console.set_mode(OutputMode.JSON)
    root = umbrella.find_root(Path.cwd())
    manager = ConfigManager()
    resolution = manager.reresolve(root, allow_schema_upgrade=allow_schema_upgrade)
    rows = _config_change_rows(root, manager, resolution.config)
    payload = {
        "root": str(root),
        "overrides": list(resolution.overrides),
        "artifacts": rows,
    }
    if console.mode is OutputMode.JSON:
        console.json(payload)
    else:
        for path in resolution.overrides:
            console.info("override {}", path)
        for row in rows:
            console.info("{} {} {}", row["key"], row["kind"], row["action"])

    if dry_run or not run_apply:
        return

    _write_config(root, resolution.config)
    result = cycle.apply(root, provenance=resolution.provenance_metadata())
    change_rows = _change_rows(result.changes)
    _emit({"root": str(root), "artifacts": change_rows}, change_rows)
    _fail_on_errors(root)


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
    planned = generation.plan(root, artifacts, store.load())
    settled = (generation.Action.UNCHANGED, generation.Action.SKIP)
    changed = [c for c in planned.changes if c.action not in settled]
    return _change_rows(changed)


def _report(directory: Path, config: KilnConfig, rows: list[dict[str, str]]) -> None:
    """Print or emit *rows*: JSON in JSON mode, else the resolved TOML and a line each."""
    payload = {
        "root": str(directory.resolve()),
        "config": config.to_document(),
        "artifacts": rows,
    }
    if console.mode is OutputMode.JSON:
        console.json(payload)
        return
    console.print(DocumentUtils.dumps(config.to_document(), ConfigFormat.TOML))
    for row in rows:
        console.info("{} {} {}", row["key"], row["kind"], row["action"])


def _emit(payload: dict[str, object], rows: list[dict[str, str]]) -> None:
    """Print or emit `apply`'s result: JSON in JSON mode, else a line per artifact."""
    if console.mode is OutputMode.JSON:
        console.json(payload)
        return
    for row in rows:
        console.info("{} {} {}", row["key"], row["kind"], row["action"])


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


def _fail_on_errors(root: Path) -> None:
    """Run `kiln doctor`'s checks over *root*, raising if any is an error."""
    findings = checks.run(root)
    for finding in findings:
        console.error("{}", finding)
    errors = [finding for finding in findings if finding.is_error]
    if errors:
        raise AppException("{} check(s) failed in {}", len(errors), root)
