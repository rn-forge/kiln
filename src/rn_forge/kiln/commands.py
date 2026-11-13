"""The commands kiln's CLI exposes.

A command function is all that is written here. `build_tool_app` builds
the application around it — the root callback, the standard
`--log-level`/`--json` flags, the error-to-exit-code mapping — from the
declaration in `cli.toml`.

Nothing here imports Typer: a parameter without a default is a positional
argument, one with a default is an option. Failure is an `AppException`,
which `CliApp` maps to exit code 1.
"""

from __future__ import annotations

import dataclasses
import re
import shutil
import subprocess
from collections.abc import Sequence
from importlib import metadata
from importlib.resources import files
from pathlib import Path

from rn_forge.cli import CliApp
from rn_forge.commons import generation
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import ConfigFormat, DocumentUtils
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import ApplyResult, StateEntry
from rn_forge.commons.lang.collections import DictUtils
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.commons.runtime.subprocess import Process

from rn_forge.kiln import archetypes, checks
from rn_forge.kiln import doctor as doctor_module
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig
from rn_forge.kiln.modules.core import cycle, umbrella
from rn_forge.kiln.modules.core.config import catalog
from rn_forge.kiln.modules.core.config.manager import ConfigManager, Resolution
from rn_forge.kiln.modules.core.config.schema import KilnPin
from rn_forge.kiln.modules.core.config.sources import Source, fetch
from rn_forge.kiln.modules.core.inventory import KINDS, inventory
from rn_forge.kiln.modules.docs import generate
from rn_forge.kiln.modules.docs.scaffold import add_package as docs_add_package
from rn_forge.kiln.modules.instructions.scaffold import (
    scaffold as instructions_scaffold,
)
from rn_forge.kiln.modules.node.scaffold import (
    format_node,
    reconcile_node,
    scaffold_node,
)
from rn_forge.kiln.modules.python.artifacts import root_package
from rn_forge.kiln.modules.python.config import MODULE_PATTERN, ArchetypeConfig
from rn_forge.kiln.modules.python.scaffold import (
    add_package as python_add_package,
)
from rn_forge.kiln.modules.python.scaffold import (
    reconcile_backend,
    scaffold_backend,
)
from rn_forge.kiln.modules.registry import builtin

__all__ = [
    "apply",
    "config_update",
    "config_upgrade",
    "diff",
    "docs_generate",
    "doctor",
    "generate_app",
    "generate_package",
    "new",
    "pin",
    "prompt",
    "version",
]

_DISTRIBUTION = "rn-forge-kiln"

_CONFIG_HEADER = (
    "The one hand-authored input kiln reads (kiln ADR-0004). Edit this, then run\n"
    "`kiln apply`. Everything else under .rn-forge/kiln/ is kiln's."
)

_PACKAGE_NAME = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

# `new`'s config-setting flags: every one of them must be backed by a
# registered module's `Option`, verified by `tests/test_new.py`.
_FLAG_NAMES = ("archetype", "docs", "backend", "frontend")


def _findings(path: Path, full: bool) -> list[Finding]:
    root = path.resolve()
    findings = checks.run(root)
    if full:
        findings.extend(doctor_module.full(root))
    return findings


def _finding_json(finding: Finding) -> dict[str, str | None]:
    return {
        "code": finding.code,
        "severity": finding.severity.value,
        "message": finding.message,
        "path": finding.path,
    }


def doctor(
    paths: list[Path],
    full: bool = False,
    json: bool = False,
    all: bool = False,
) -> None:
    """Run every render-free check over each of PATHS' committed files.

    Prints each finding and raises `AppException` if any is an error. `--full`
    also reports every managed artifact and block a fresh render would change.
    `--json` prints the findings as one JSON object. More than one path needs
    `--all`, which checks each independently, reports a path whose config will
    not load as a `config.load` error for that path alone, and prints a table of
    paths with their error and warning counts.

    Raises:
        AppException: several paths are given without `--all`, or a finding is an
            error.
    """
    if len(paths) > 1 and not all:
        raise AppException("several paths need --all")
    if json:
        console.set_mode(OutputMode.JSON)

    if not all:
        findings = _findings(paths[0], full)
        if console.mode is OutputMode.JSON:
            console.json({"findings": [_finding_json(f) for f in findings]})
        else:
            for finding in findings:
                console.error("{}", finding)
        errors = [finding for finding in findings if finding.is_error]
        if errors:
            raise AppException("{} check(s) failed in {}", len(errors), paths[0])
        return

    reports: list[tuple[Path, list[Finding]]] = []
    for path in paths:
        try:
            reports.append((path, _findings(path, full)))
        except AppException as exc:
            reports.append(
                (path, [Finding("config.load", Severity.ERROR, str(exc), path=None)])
            )
    error_counts = [sum(f.is_error for f in found) for _, found in reports]
    warning_counts = [len(found) - n for (_, found), n in zip(reports, error_counts)]
    if console.mode is OutputMode.JSON:
        console.json(
            {
                "repos": [
                    {"path": str(path), "findings": [_finding_json(f) for f in found]}
                    for path, found in reports
                ],
                "summary": {
                    "repos": len(reports),
                    "errors": sum(error_counts),
                    "warnings": sum(warning_counts),
                },
            }
        )
    else:
        console.table(
            "repo",
            "errors",
            "warnings",
            rows=[
                (path, errors, warnings)
                for (path, _), errors, warnings in zip(
                    reports, error_counts, warning_counts
                )
            ],
        )
        for path, found in reports:
            if found:
                console.print("{}", path, markup=False)
            for finding in found:
                console.error("{}", finding)
    if sum(error_counts):
        raise AppException(
            "{} check(s) failed across {} repo(s)",
            sum(error_counts),
            sum(1 for n in error_counts if n),
        )


def docs_generate(path: Path) -> None:
    """Regenerate the derived regions of PATH's docs, such as `mkdocs.yml`'s nav.

    `kiln doctor` checks that they are current.
    """
    config = ConfigManager().load(path)
    packages = config.packages if config.archetype == "python-lib" else ()
    written, findings = generate.generate(path, packages)
    if not written:
        console.info("no change")
    for file in written:
        console.success("updated {}", file)
    for finding in findings:
        console.error("{}", finding)
    errors = [finding for finding in findings if finding.is_error]
    if errors:
        raise AppException("{} finding(s) in {}", len(errors), path)


def new(
    directory: Path,
    archetype: str = "",
    docs: str = "mkdocs",
    backend: str | None = None,
    frontend: str | None = None,
    module: str | None = None,
    config: str | None = None,
    owner: str | None = None,
    allow_untested: bool = False,
    dry_run: bool = False,
    yes: bool = False,
    json: bool = False,
) -> None:
    """Create a repository at DIRECTORY, previewing unless `--yes` is given.

    The repository's name is `--config`'s `[repository] name`, else the
    directory's. Its GitHub owner is `--owner`, else `--config`'s
    `[repository] owner`; there is no default (`new.owner-required`).

    Without `--yes`, prints the resolved config and the artifacts it would
    produce, and writes nothing. With `--yes`, writes `config.toml`, scaffolds
    the tree and applies it (kiln ADR-0004). A `python-lib` config's `packages`
    are then generated in order, as `kiln generate package` would; if any
    fails, DIRECTORY is not created.

    `--backend` and `--frontend` are omitted (left `None`) unless given, so a
    config-selected value or the archetype's own default survives; passing
    either for an archetype that does not declare it is refused, naming the
    key. `--module` sets the dotted import module of a `python-app` or
    `python-tool` repository (a namespace package such as `rn_forge.agentkit`)
    in place of the one derived from the name.

    Raises:
        AppException: `--archetype` is missing or unknown, no owner is given
            (`new.owner-required`), a flag names an
            untested value without `--allow-untested`, DIRECTORY is non-empty,
            or the config, scaffold, apply or check step fails, including a
            `generate.*` error from one of a `python-lib` config's packages.
    """
    if json:
        console.set_mode(OutputMode.JSON)
    if not archetype:
        raise AppException("--archetype is required")

    manager, resolution = _resolve_config(
        directory.name,
        archetype=archetype,
        docs=docs,
        backend=backend,
        frontend=frontend,
        module=module,
        config=config,
        owner=owner,
        owner_error="new.owner-required: pass --owner <owner> or set "
        "repository.owner in --config",
        allow_untested=allow_untested,
    )
    resolved = resolution.config
    members = resolved.packages if resolved.archetype == "python-lib" else ()
    declared = _declared_modules(resolved)
    bare = _without_members(resolved)

    if not yes or dry_run:
        rows = _preview_rows(directory, resolved, manager)
        _report(directory, resolved, rows)
        return

    if directory.exists() and any(directory.iterdir()):
        raise AppException("{} is not empty", directory)

    workspace = _stage(directory.name)
    _write_config(workspace, bare)

    raw_backend = workspace.parent / "backend"
    raw_frontend = workspace.parent / "frontend"
    scaffold_backend(raw_backend, bare)
    frontend_workspace = scaffold_node(raw_frontend, bare)
    reconcile_backend(raw_backend, workspace, bare)
    if frontend_workspace is not None:
        reconcile_node(workspace, frontend_workspace, bare)
    instructions_scaffold(workspace, bare)

    result = cycle.apply(
        workspace, provenance=resolution.provenance_metadata(), starters=""
    )
    for member in members:
        _add_package(workspace, Path(member).name, declared.get(member))
    if resolved.docs_profile == "mkdocs":
        packages = (
            KilnConfig.load(workspace).packages
            if resolved.archetype == "python-lib"
            else ()
        )
        generate.generate(workspace, packages)
    if frontend_workspace is not None:
        format_node(workspace)
    _fail_on_errors(workspace)

    directory.mkdir(parents=True, exist_ok=True)
    shutil.copytree(workspace, directory, symlinks=True, dirs_exist_ok=True)
    # Last, so a failed run leaves no repository; the file linters need a root.
    Process.execute("git-init", "git", "init", "-q", cwd=str(directory))
    _record_scaffolded(directory)
    rows = _change_rows(result.changes)
    _report(directory, resolved, rows)


def _record_scaffolded(directory: Path) -> None:
    """Record in `state.json` the files `kiln new` wrote that no artifact owns.

    Args:
        directory: The new repository, already `git init`-ed.
    """
    listed = subprocess.run(
        [
            "git",
            "-C",
            str(directory),
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    state_path = directory / ".rn-forge" / "kiln" / "state.json"
    state = DocumentUtils.read(state_path)
    owned = {entry["path"] for entry in state["entries"].values()}
    state["metadata"]["scaffolded"] = sorted(
        path
        for path in listed.split("\0")
        if path and path not in owned and not path.startswith(".rn-forge/")
    )
    state_path.write_text(
        DocumentUtils.dumps(state, ConfigFormat.JSON), encoding="utf-8"
    )


def _resolve_config(
    name: str,
    *,
    archetype: str,
    docs: str,
    backend: str | None,
    frontend: str | None,
    module: str | None,
    config: str | None,
    owner: str | None,
    owner_error: str,
    allow_untested: bool,
) -> tuple[ConfigManager, Resolution]:
    """Merge defaults, the `--config` layer and the flags for a repository called *name*.

    The owner is *owner* (`--owner`), else the `--config` layer's; with neither,
    *owner_error* is raised.

    Raises:
        AppException: The archetype is unknown, a flag names an untested value,
            or the config is invalid.
    """
    layer_pins_kiln = False
    layer_owner: object = None
    if config:
        fetched = fetch(Source.parse(config), Path.cwd())
        layer_pins_kiln = bool(DictUtils.get(fetched.document, "kiln.ref"))
        layer_owner = DictUtils.get(fetched.document, "repository.owner")
        configured = DictUtils.get(fetched.document, "repository.name")
        if isinstance(configured, str):
            if configured != name:
                console.info(
                    "repository name {} from --config (the directory is {})",
                    configured,
                    name,
                )
            name = configured
    manifest = archetypes.load(archetype)
    flags = _flag_layer(
        archetype=archetype,
        docs=docs,
        manifest=manifest,
        allow_untested=allow_untested,
        backend=backend,
        frontend=frontend,
    )
    DictUtils.set(flags, "repository.name", name)
    chosen = owner
    if not chosen and not layer_owner:
        raise AppException(owner_error)
    if chosen:
        DictUtils.set(flags, "repository.owner", chosen)
    if not layer_pins_kiln:
        DictUtils.set(flags, "kiln.ref", archetypes.KILN_REF)
    if module is not None:
        DictUtils.set(flags, f"archetype.{archetype}.module", module)
    package = module or root_package(name)
    if archetype in {"python-tool", "python-app"}:
        DictUtils.set(
            flags,
            "cli",
            {
                "name": name,
                "help": f"The {name} command line.",
                "commands": [{"name": "hello", "target": f"{package}.commands:hello"}],
            },
        )
    if archetype == "python-tool":
        DictUtils.set(flags, "lifecycle", {"product": f"{package}.product:PRODUCT"})

    manager = ConfigManager()
    source = Source.parse(config) if config else None
    return manager, manager.resolve(flags=flags, source=source)


def apply(
    force: list[str] | None = None, dry_run: bool = False, json: bool = False
) -> None:
    """Reconcile the current repository's rendered artifacts (kiln ADR-0004).

    Plans first, refusing any `--force` value that does not name a reported,
    blocking change; then applies, then runs `kiln doctor`'s ownership checks.

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


def generate_package(
    name: str,
    path: Path = Path(),
    json: bool = False,
    module: str | None = None,
) -> None:
    """Add the package NAME to the `python-lib` repository at `--path`.

    Writes the package, its docs site, changelog and README, and updates the
    config, the workspace and the managed files that list packages. Everything
    is checked before anything is written. `--module` sets a dotted import
    module (a namespace package such as `rn_forge.cli`) in place of the one
    derived from NAME.

    Raises:
        AppException: The archetype is not `python-lib`
            (`generate.unsupported-archetype`), NAME is not a kebab-case
            distribution name (`generate.invalid-name`), `--module` is not a
            dotted import module (`generate.invalid-module`), NAME is already a
            package or `packages/NAME` exists (`generate.package-exists`),
            or a step or the apply fails.
    """
    if json:
        console.set_mode(OutputMode.JSON)
    root = umbrella.find_root(path.resolve())
    result = _add_package(root, name, module)
    relative = f"packages/{name}"

    written = sorted(
        file.relative_to(root).as_posix()
        for file in (root / relative).rglob("*")
        if file.is_file() and "__pycache__" not in file.parts
    )
    rows = _change_rows(result.changes)
    _emit(
        {
            "root": str(root),
            "written": [CONFIG_PATH.as_posix(), "pyproject.toml", *written],
            "artifacts": rows,
        },
        rows,
    )


def _add_package(root: Path, name: str, module: str | None) -> ApplyResult:
    """Add the package NAME to the `python-lib` repository at *root*; see `generate_package`."""
    config = ConfigManager().load(root)
    remote = _package_preflight(root, config, name, module)
    relative = f"packages/{name}"

    section: dict[str, object] = {"packages": [*config.packages, relative]}
    if module is not None and module != root_package(name):
        section["modules"] = {relative: module}
    DocumentUtils.update(root / CONFIG_PATH, {"archetype": {"python-lib": section}})
    config = ConfigManager().load(root)
    _write_config(root, config)
    python_add_package(root, config, name, remote)
    docs_add_package(root, config, name)
    result = cycle.apply(root)
    generate.generate(root, config.packages)
    return result


def _declared_modules(config: KilnConfig) -> dict[str, str]:
    """A `python-lib` config's `modules` table; empty for any other archetype."""
    section = getattr(config.document, "archetype", None)
    lib = section.python_lib if isinstance(section, ArchetypeConfig) else None
    return dict(lib.modules) if config.archetype == "python-lib" and lib else {}


def _without_members(config: KilnConfig) -> KilnConfig:
    """*config* with a `python-lib`'s `packages` and `modules` emptied."""
    section = getattr(config.document, "archetype", None)
    if not isinstance(section, ArchetypeConfig) or section.python_lib is None:
        return config
    lib = section.python_lib.model_copy(update={"packages": [], "modules": {}})
    bare = config.document.model_copy(
        update={"archetype": section.model_copy(update={"python_lib": lib})}
    )
    return dataclasses.replace(config, document=bare)


def _package_preflight(
    root: Path, config: KilnConfig, name: str, module: str | None = None
) -> str:
    """The repository's GitHub URL, after refusing every case `generate package` cannot write."""
    if config.archetype != "python-lib":
        raise AppException(
            "generate.unsupported-archetype: kiln generate package supports "
            "python-lib only, not {}",
            config.archetype,
        )
    if not _PACKAGE_NAME.match(name):
        raise AppException(
            "generate.invalid-name: {!r} is not a kebab-case distribution name", name
        )
    if module is not None and not MODULE_PATTERN.match(module):
        raise AppException(
            "generate.invalid-module: {!r} is not a dotted import module name",
            module,
        )
    relative = f"packages/{name}"
    if relative in config.packages or (root / relative).exists():
        raise AppException("generate.package-exists: {} already exists", relative)
    return f"https://github.com/{config.owner}/{config.name}"


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


def diff(
    artifact: str | None = None, old: str | None = None, json: bool = False
) -> None:
    """Unified diff of on-disk content against a fresh render, writing nothing.

    With no `--artifact`, every managed and block artifact whose disk content
    differs from its fresh render is diffed; `--artifact` (a key or a path)
    limits it to one. A defaulted parameter is always an option in this
    framework without a `typer.Argument` marker (see `new`'s own
    `--archetype`), which kiln's commands never import, so this is `--artifact`
    rather than the design table's bare positional.

    `--old` is another repository's checkout: instead of diffing the artifacts,
    list every file of this (reference) repository and of that one with its
    class and whether the bytes match; exits 0.

    Raises:
        AppException: ARTIFACT names no known artifact, a difference was
            found — `diff(1)`'s own exit-1 convention — or `--old` is not a git
            repository or is given with `--artifact`.
    """
    if json:
        console.set_mode(OutputMode.JSON)
    if old is not None:
        if artifact is not None:
            raise AppException(
                "inventory.artifact-with-old: --artifact and --old exclude each other"
            )
        rows = inventory(umbrella.find_root(Path.cwd()), Path(old))
        if console.mode is OutputMode.JSON:
            console.json({"inventory": [dataclasses.asdict(row) for row in rows]})
            return
        for row in rows:
            console.print(f"{row.kind:<11} {row.status:<15} {row.path}", markup=False)
        console.print(
            ", ".join(f"{sum(r.kind == kind for r in rows)} {kind}" for kind in KINDS),
            markup=False,
        )
        return
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


def prompt(name: str = "", json: bool = False) -> None:
    """Print the shipped prompt `--name`, or list the prompts when it is not given.

    A prompt is a one-time procedure shipped in the distribution; printing one
    reads no repository and writes nothing. A defaulted parameter is always an
    option in this framework without a `typer.Argument` marker, which kiln's
    commands never import, so this is `--name` rather than a bare positional.

    Raises:
        AppException: NAME is not a shipped prompt.
    """
    if json:
        console.set_mode(OutputMode.JSON)
    directory = files("rn_forge.kiln").joinpath("prompts")
    available = {
        entry.name.removesuffix(".md"): entry.read_text(encoding="utf-8")
        for entry in directory.iterdir()
        if entry.name.endswith(".md")
    }
    if not name:
        rows = [
            {"name": key, "summary": _prompt_summary(text)}
            for key, text in sorted(available.items())
        ]
        if console.mode is OutputMode.JSON:
            console.json({"prompts": rows})
        else:
            for row in rows:
                console.print(f"{row['name']}: {row['summary']}", markup=False)
        return
    if name not in available:
        raise AppException(
            "no prompt named {}; available: {}", name, ", ".join(sorted(available))
        )
    if console.mode is OutputMode.JSON:
        console.json({"name": name, "text": available[name]})
    else:
        console.print(available[name], markup=False)


def _prompt_summary(text: str) -> str:
    """The first paragraph after the title, on one line."""
    paragraphs = [part for part in text.split("\n\n") if part.strip()]
    return " ".join(paragraphs[1].split())


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
        text = generation.diff(root, change)
        if text:
            results.append((artifact.path, text))
    return results


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


STAGING = ".staging"
"""Where `kiln new` builds a repository, beneath the invocation directory."""


def _stage(name: str) -> Path:
    """Create `.staging/<name>/{backend,frontend,workspace}`; return `workspace`.

    Staging is review state: it is never reused, cleaned or moved here.

    Raises:
        AppException: `.staging/<name>/` already exists.
    """
    staging = Path.cwd() / STAGING
    run = staging / name
    if run.exists():
        raise AppException("{} already exists; staging is never reused", run)
    staging.mkdir(exist_ok=True)
    # Anchor the rule so Nx's scanner does not ignore every descendant file.
    (staging / ".gitignore").write_text("/*\n", encoding="utf-8")
    for part in ("backend", "frontend", "workspace"):
        (run / part).mkdir(parents=True)
    return run / "workspace"


def _write_config(directory: Path, config: KilnConfig) -> None:
    """Write *config* as `directory`'s committed `config.toml`, with kiln's header."""
    config_path = directory / CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        catalog.render(config, header=_CONFIG_HEADER), encoding="utf-8"
    )


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
    _write_config(root, dataclasses.replace(config, document=document))
    console.info("kiln ref {} \u2192 {}", old, ref)


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
    planned = cycle.classify(root, artifacts, store.load())
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
    """Run `kiln doctor`'s ownership checks over *root*, raising if any is an error."""
    findings = checks.run(root, scope="ownership")
    for finding in findings:
        console.error("{}", finding)
    errors = [finding for finding in findings if finding.is_error]
    if errors:
        raise AppException("{} check(s) failed in {}", len(errors), root)


generate_app = CliApp("kiln", "Generate parts of a repository.")
"""The `generate` namespace; each generator is a command on it."""
generate_app.command(name="package")(generate_package)
