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

import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from importlib import metadata
from importlib.resources import files
from pathlib import Path

from rn_forge.cli import CliApp
from rn_forge.commons import generation
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import ConfigFormat, DocumentError, DocumentUtils
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import StateEntry
from rn_forge.commons.lang.collections import DictUtils
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import archetypes, checks
from rn_forge.kiln import doctor as doctor_module
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig
from rn_forge.kiln.modules.core import cycle, umbrella
from rn_forge.kiln.modules.core.artifacts import GITIGNORE_BLOCK
from rn_forge.kiln.modules.core.config.manager import ConfigManager, Resolution
from rn_forge.kiln.modules.core.config.sources import Source, fetch
from rn_forge.kiln.modules.docs import generate
from rn_forge.kiln.modules.docs.nav import NAV_BLOCK, mark_nav
from rn_forge.kiln.modules.docs.scaffold import add_package as docs_add_package
from rn_forge.kiln.modules.docs.scaffold import scaffold as docs_scaffold
from rn_forge.kiln.modules.instructions.scaffold import (
    scaffold as instructions_scaffold,
)
from rn_forge.kiln.modules.node.scaffold import (
    reconcile_node,
    scaffold_node,
)
from rn_forge.kiln.modules.python.artifacts import root_package
from rn_forge.kiln.modules.python.config import MODULE_PATTERN
from rn_forge.kiln.modules.python.scaffold import (
    add_package as python_add_package,
)
from rn_forge.kiln.modules.python.scaffold import (
    add_task_tools,
    github_remote,
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
    "init",
    "new",
    "prompt",
    "version",
]

_DISTRIBUTION = "rn-forge-kiln"

_CONFIG_HEADER = (
    "The one hand-authored input kiln reads (kiln ADR-0004). Edit this, then run\n"
    "`kiln apply`. Everything else under .rn-forge/kiln/ is kiln's."
)

_INIT_FILES = ("pyproject.toml",)

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
    allow_untested: bool = False,
    dry_run: bool = False,
    yes: bool = False,
    json: bool = False,
) -> None:
    """Create a repository at DIRECTORY, previewing unless `--yes` is given.

    The repository's name is `--config`'s `[repository] name`, else the
    directory's.

    Without `--yes`, prints the resolved config and the artifacts it would
    produce, and writes nothing. With `--yes`, writes `config.toml`, scaffolds
    the tree and applies it (kiln ADR-0004).

    `--backend` and `--frontend` are omitted (left `None`) unless given, so a
    config-selected value or the archetype's own default survives; passing
    either for an archetype that does not declare it is refused, naming the
    key. `--module` sets the dotted import module of a `python-app` or
    `python-tool` repository (a namespace package such as `rn_forge.agentkit`)
    in place of the one derived from the name.

    Raises:
        AppException: `--archetype` is missing or unknown, a flag names an
            untested value without `--allow-untested`, a `python-lib` config
            lists packages (`config.packages-at-new`), DIRECTORY is non-empty,
            or the config, scaffold, apply or check step fails.
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
        allow_untested=allow_untested,
        allow_packages=False,
    )
    resolved = resolution.config

    if not yes or dry_run:
        rows = _preview_rows(directory, resolved, manager)
        _report(directory, resolved, rows)
        return

    if directory.exists() and any(directory.iterdir()):
        raise AppException("{} is not empty", directory)

    workspace = _stage(directory.name)
    _write_config(workspace, resolved)

    raw_backend = workspace.parent / "backend"
    raw_frontend = workspace.parent / "frontend"
    scaffold_backend(raw_backend, resolved)
    frontend_workspace = scaffold_node(raw_frontend, resolved)
    reconcile_backend(raw_backend, workspace, resolved)
    if frontend_workspace is not None:
        reconcile_node(workspace, frontend_workspace, resolved)
    docs_scaffold(workspace, resolved)
    instructions_scaffold(workspace, resolved)

    result = cycle.apply(workspace, provenance=resolution.provenance_metadata())
    if resolved.docs_profile == "mkdocs":
        packages = resolved.packages if resolved.archetype == "python-lib" else ()
        generate.generate(workspace, packages)
    _fail_on_errors(workspace)

    directory.mkdir(parents=True, exist_ok=True)
    shutil.copytree(workspace, directory, symlinks=True, dirs_exist_ok=True)
    rows = _change_rows(result.changes)
    _report(directory, resolved, rows)


def init(
    archetype: str = "",
    docs: str = "mkdocs",
    backend: str | None = None,
    frontend: str | None = None,
    module: str | None = None,
    config: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    yes: bool = False,
    json: bool = False,
) -> None:
    """Bring the existing standard repository in the current directory under kiln.

    The repository's name is `--config`'s `[repository] name`, else the
    directory's.

    `new`'s configuration and first-apply flow, run in place and never
    scaffolding. `--module` sets the dotted import module of a `python-app` or
    `python-tool` repository in place of the one derived from the name.
    Requires a `.git` entry and a `pyproject.toml`; kiln renders every managed
    path that is missing. Without `--yes` (or with `--dry-run`)
    prints the resolved config and the artifact plan, and writes nothing. With
    `--yes`, the Git
    working tree must be clean (`init.dirty-tree`); it then writes
    `config.toml`, then applies, recording byte-identical managed files in the
    baseline without rewriting them, then runs `kiln doctor`'s ownership checks.

    A `python-lib` workspace is adopted with its members: unlike `new`, the
    `--config` layer may list `packages`, each an existing directory with a
    `pyproject.toml` (S6.1.5).

    An existing `mkdocs.yml` without the derived-nav markers is refused
    (`init.nav-unmarked`); under `--force` it is archived and the markers are
    placed around the nav's entries, which `docs-generate` then replaces
    (S6.1.9).

    `--force` first fences an unfenced `.importlinter` (S6.1.7): kiln's
    `[importlinter]` section is dropped, the rest kept below the markers, and
    the original archived. It also approves every conflict at once: each
    conflicting target, and a prior `config.toml` and `state.json`, is first
    copied to `.rn-forge/kiln/backups/<UTC timestamp>/`. It never implies
    `--yes`.

    Raises:
        AppException: `--archetype` is missing, the current directory fails the
            preflight (each failed condition is named), a listed package has
            no `pyproject.toml` (`init.package-missing`), `state.json` already
            exists, a conflict exists without `--force`, or the config, apply
            or check step fails.
    """
    if json:
        console.set_mode(OutputMode.JSON)
    if not archetype:
        raise AppException("--archetype is required")
    root = Path.cwd()
    _init_preflight(root)
    if yes and not dry_run:
        _require_clean(root)

    state_path = root / umbrella.STATE_PATH
    if state_path.exists() and not force:
        raise AppException(
            "{} already exists; this repository is under kiln — pass --force "
            "to archive it and initialise again",
            state_path,
        )

    _, resolution = _resolve_config(
        root.name,
        archetype=archetype,
        docs=docs,
        backend=backend,
        frontend=frontend,
        module=module,
        config=config,
        allow_untested=False,
        allow_packages=True,
    )
    resolved = resolution.config
    _require_packages(root, resolved.packages)
    if yes and not dry_run:
        unfenced = cycle.unfenced(root, resolved)
        if unfenced and not force:
            raise cycle.CycleRefused(unfenced)
        if unfenced:
            _archive(root, [str(finding.path) for finding in unfenced], tag="-unfenced")
            cycle.fence(root, resolved)
    if yes and not dry_run and resolved.docs_profile == "mkdocs":
        _settle_nav(root, force)
    planned = cycle.adoption_plan(root, resolved)

    if not yes or dry_run:
        _report(root, resolved, _change_rows(planned.changes))
        return

    config_path = root / CONFIG_PATH
    conflicts = [
        change
        for change in planned.changes
        if change.action is generation.Action.CONFLICT
    ]
    conflicting = {change.path for change in conflicts}
    if config_path.exists():
        conflicting.add(CONFIG_PATH.as_posix())
    if conflicting and not force:
        raise AppException(
            "{} conflict(s), nothing written: {} — pass --force to archive "
            "them and overwrite",
            len(conflicting),
            ", ".join(sorted(conflicting)),
        )
    if force:
        if state_path.exists():
            conflicting.add(umbrella.STATE_PATH.as_posix())
        _archive(root, sorted(conflicting))

    _write_config(root, resolved)
    result = cycle.apply(
        root,
        force=[change.key for change in conflicts],
        provenance=resolution.provenance_metadata(),
        adopt=True,
    )
    removed = _dedupe_gitignore(root)
    if removed:
        console.info(
            "removed {} line(s) from .gitignore that kiln's block holds", len(removed)
        )
    if resolved.docs_profile == "mkdocs" and (root / "mkdocs.yml").is_file():
        packages = resolved.packages if resolved.archetype == "python-lib" else ()
        generate.generate(root, packages)
    if "python" in archetypes.for_config(resolved).modules:
        added = add_task_tools(root, resolved)
        if added:
            console.info(
                "added {} to pyproject.toml's dependency groups", ", ".join(added)
            )
    _fail_on_errors(root)
    _report(root, resolved, _change_rows(result.changes))


def _settle_nav(root: Path, force: bool) -> None:
    """Refuse an unmarked `mkdocs.yml`, or under *force* archive it and mark its nav (S6.1.9)."""
    path = root / "mkdocs.yml"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if NAV_BLOCK.extract(text) is not None:
        return
    if not force:
        raise AppException(
            "init.nav-unmarked: mkdocs.yml has no '# BEGIN derived nav' / "
            "'# END derived nav' markers — add them around nav's entries, or "
            "pass --force to have kiln place them and derive the nav"
        )
    _archive(root, ["mkdocs.yml"], tag="-nav")
    path.write_text(mark_nav(text), encoding="utf-8")


def _dedupe_gitignore(root: Path) -> list[str]:
    """Drop the lines outside kiln's `.gitignore` block that the block already holds.

    A pattern is a stripped line that is not blank and not a comment; its key
    is the pattern without one trailing `/`. Any `!` pattern, inside or outside
    the block, makes order matter, so the file is left alone.

    Returns:
        The dropped lines, without their line endings; empty when nothing was
        removed.
    """
    path = root / ".gitignore"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    body = GITIGNORE_BLOCK.extract(text)
    if body is None:
        return []

    def pattern(line: str) -> str | None:
        stripped = line.strip()
        return stripped if stripped and not stripped.startswith("#") else None

    outside = GITIGNORE_BLOCK.remove(text)
    patterns = [p for line in (body + outside).splitlines() if (p := pattern(line))]
    if any(p.startswith("!") for p in patterns):
        return []
    held = {p.removesuffix("/") for line in body.splitlines() if (p := pattern(line))}
    dropped: list[str] = []
    groups: list[list[str]] = [[]]
    for line in outside.splitlines(keepends=True):
        if not line.strip():
            groups.append([])
            continue
        found = pattern(line)
        if found is not None and found.removesuffix("/") in held:
            dropped.append(line.rstrip("\r\n"))
            groups[-1].append("")
        else:
            groups[-1].append(line)
    if not dropped:
        return []
    kept = [
        "".join(lines)
        for group in groups
        if (lines := _surviving_group(group, pattern))
    ]
    path.write_text(GITIGNORE_BLOCK.render("\n".join(kept), body), encoding="utf-8")
    return dropped


def _surviving_group(
    group: list[str], pattern: Callable[[str], str | None]
) -> list[str]:
    """The lines of a `.gitignore` *group* to keep; `""` marks a dropped pattern.

    A group that lost a pattern and has none left loses its comments too.
    """
    lines = [line for line in group if line]
    lost = len(lines) < len(group)
    if lost and not any(pattern(line) for line in lines):
        return []
    return lines


def _require_packages(root: Path, packages: tuple[str, ...]) -> None:
    """Refuse a listed package that is not an existing member of *root*.

    Raises:
        AppException: Naming every package directory without a `pyproject.toml`.
    """
    missing = [p for p in packages if not (root / p / "pyproject.toml").is_file()]
    if missing:
        raise AppException(
            "init.package-missing: no pyproject.toml in {}", ", ".join(missing)
        )


def _require_clean(root: Path) -> None:
    """Refuse *root* unless its Git working tree has no changes.

    Raises:
        AppException: `init.not-a-repository` if git fails; `init.dirty-tree`
            naming every changed or untracked path.
    """
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0:
        raise AppException("init.not-a-repository: {}", status.stderr.strip())
    paths = [line[3:] for line in status.stdout.splitlines() if line]
    if paths:
        raise AppException(
            "init.dirty-tree: commit or stash first (git stash -u), so the "
            "review is kiln's change alone: {}",
            ", ".join(paths),
        )


def _init_preflight(root: Path) -> None:
    """Refuse *root* unless it is a standard repository's Git worktree root.

    Raises:
        AppException: Naming every failed condition at once.
    """
    failed: list[str] = []
    if not (root / ".git").exists():
        failed.append("not a Git worktree root (no .git entry here)")
    if _project_name(root / "pyproject.toml") == _canonical(_own_name()):
        failed.append("kiln's own source checkout")
    failed.extend(
        f"missing {name}" for name in _INIT_FILES if not (root / name).is_file()
    )
    if failed:
        raise AppException("kiln init cannot run in {}: {}", root, "; ".join(failed))


def _own_name() -> str:
    """kiln's distribution name, as its `pyproject.toml` declared it at build."""
    return metadata.metadata(_DISTRIBUTION)["Name"]


def _canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _project_name(pyproject: Path) -> str | None:
    """`[project].name` of *pyproject*, canonicalised; `None` if absent or unreadable."""
    if not pyproject.is_file():
        return None
    try:
        document = DocumentUtils.read(pyproject)
    except DocumentError:
        return None
    name = document.get("project", {}).get("name")
    return _canonical(name) if isinstance(name, str) else None


def _archive(root: Path, paths: Sequence[str], tag: str = "") -> None:
    """Warn, then copy each existing repo-relative *paths* under a fresh timestamped backup directory.

    *tag* is appended to the directory name, so a copy that `generation.apply`'s
    own backup (named by the bare timestamp) must not overwrite stays apart.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base = root / umbrella.BACKUPS
    archive = base / f"{stamp}{tag}"
    suffix = 0
    while archive.exists():
        suffix += 1
        archive = base / f"{stamp}{tag}-{suffix}"
    console.warning(
        "--force: archiving {} target(s) to {} before overwriting",
        len(paths),
        archive,
    )
    for relative in paths:
        source = root / relative
        if source.is_file():
            destination = archive / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def _resolve_config(
    name: str,
    *,
    archetype: str,
    docs: str,
    backend: str | None,
    frontend: str | None,
    module: str | None,
    config: str | None,
    allow_untested: bool,
    allow_packages: bool,
) -> tuple[ConfigManager, Resolution]:
    """Merge defaults, the `--config` layer and the flags for a repository called *name*.

    `new` starts a `python-lib` repository empty; `init` adopts one with its
    members, so only it passes *allow_packages*.

    Raises:
        AppException: The archetype is unknown, a flag names an untested value,
            the config is invalid, or a `python-lib` config lists packages
            without *allow_packages*.
    """
    layer_pins_kiln = False
    if config:
        fetched = fetch(Source.parse(config), Path.cwd())
        layer_pins_kiln = bool(DictUtils.get(fetched.document, "kiln.ref"))
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
    resolution = manager.resolve(flags=flags, source=source)
    resolved = resolution.config
    if resolved.archetype == "python-lib" and resolved.packages and not allow_packages:
        raise AppException(
            "config.packages-at-new: a python-lib repository starts with no "
            "packages; add each with 'kiln generate package <name>'"
        )

    return manager, resolution


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
            `origin` is not a GitHub remote (`generate.no-remote`), or a step
            or the apply fails.
    """
    if json:
        console.set_mode(OutputMode.JSON)
    root = umbrella.find_root(path.resolve())
    config = ConfigManager().load(root)
    remote = _package_preflight(root, config, name, module)
    relative = f"packages/{name}"

    section: dict[str, object] = {"packages": [*config.packages, relative]}
    if module is not None and module != root_package(name):
        section["modules"] = {relative: module}
    DocumentUtils.update(root / CONFIG_PATH, {"archetype": {"python-lib": section}})
    config = ConfigManager().load(root)
    python_add_package(root, config, name, remote)
    docs_add_package(root, config, name)
    result = cycle.apply(root)
    generate.generate(root, config.packages)

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
    remote = github_remote(root)
    if remote is None:
        raise AppException(
            "generate.no-remote: a published package needs the repository's "
            "GitHub remote: git remote add origin https://github.com/<owner>/<repo>"
        )
    return remote


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
        DocumentUtils.dumps(
            config.to_document(),
            ConfigFormat.TOML,
            header=_CONFIG_HEADER,
            multiline_arrays=True,
        ),
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
