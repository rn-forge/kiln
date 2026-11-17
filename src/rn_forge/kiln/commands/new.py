"""`kiln new`: create a repository from an archetype."""

from __future__ import annotations

import shutil
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import ConfigFormat, DocumentUtils
from rn_forge.commons.lang.collections import DictUtils
from rn_forge.commons.runtime.console import console

from rn_forge.kiln import archetypes
from rn_forge.kiln.commands import output
from rn_forge.kiln.commands.generate import add_package
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.core.config import catalog
from rn_forge.kiln.modules.core.config.manager import ConfigManager, Resolution
from rn_forge.kiln.modules.core.config.sources import Source, fetch
from rn_forge.kiln.modules.core.names import module_name
from rn_forge.kiln.modules.core.process import run
from rn_forge.kiln.modules.docs import generate as docs_generator
from rn_forge.kiln.modules.instructions import scaffold as instructions_scaffold
from rn_forge.kiln.modules.node import scaffold as node_scaffold
from rn_forge.kiln.modules.python import scaffold as python_scaffold
from rn_forge.kiln.modules.python import starter as python_starter
from rn_forge.kiln.modules.registry import builtin

__all__ = ["FLAG_NAMES", "STAGING", "flag_layer", "new"]


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
    the tree and applies it. A `python-lib` config's `packages`
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
    output.use_json(json)
    if not archetype:
        raise AppException("--archetype is required")

    resolution = _resolve_config(
        directory.name,
        archetype=archetype,
        docs=docs,
        backend=backend,
        frontend=frontend,
        module=module,
        config=config,
        owner=owner,
        allow_untested=allow_untested,
    )
    resolved = resolution.config
    members = resolved.docs_packages
    declared = python_scaffold.declared_modules(resolved)
    bare = python_scaffold.without_members(resolved)

    if not yes or dry_run:
        rows = output.change_rows(cycle.preview(directory, resolved))
        _report(directory, resolved, rows)
        return

    if directory.exists() and any(directory.iterdir()):
        raise AppException("{} is not empty", directory)

    workspace = _stage(directory.name)
    catalog.write(workspace, bare)

    raw_backend = workspace.parent / "backend"
    raw_frontend = workspace.parent / "frontend"
    python_scaffold.scaffold_backend(raw_backend, bare)
    frontend_workspace = node_scaffold.scaffold_node(raw_frontend, bare)
    python_scaffold.reconcile_backend(raw_backend, workspace, bare)
    if frontend_workspace is not None:
        node_scaffold.reconcile_node(workspace, frontend_workspace, bare)
    instructions_scaffold.scaffold(workspace, bare)

    result = cycle.apply(
        workspace, provenance=resolution.provenance_metadata(), starters=""
    )
    for member in members:
        add_package(workspace, Path(member).name, declared.get(member))
    if resolved.docs_profile == "mkdocs":
        packages = KilnConfig.load(workspace).packages if resolved.is_workspace else ()
        docs_generator.generate(workspace, packages)
    if frontend_workspace is not None:
        node_scaffold.format_node(workspace)
    output.fail_on_errors(workspace)

    directory.mkdir(parents=True, exist_ok=True)
    shutil.copytree(workspace, directory, symlinks=True, dirs_exist_ok=True)
    # Last, so a failed run leaves no repository; the file linters need a root.
    run("git-init", "git", "init", "-q", cwd=directory)
    cycle.record_scaffolded(directory)
    rows = output.change_rows(result.changes)
    _report(directory, resolved, rows)


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
    allow_untested: bool,
) -> Resolution:
    """Merge defaults, the `--config` layer and the flags for a repository called *name*.

    The owner is *owner* (`--owner`), else the `--config` layer's.

    Raises:
        AppException: The archetype is unknown, no owner is given
            (`new.owner-required`), a flag names an untested value, or the
            config is invalid.
    """
    layer_pins_kiln = False
    layer_owner: object = None
    source = Source.parse(config) if config else None
    if source is not None:
        fetched = fetch(source, Path.cwd())
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
    flags = flag_layer(
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
        raise AppException(
            "new.owner-required: pass --owner <owner> or set "
            "repository.owner in --config"
        )
    if chosen:
        DictUtils.set(flags, "repository.owner", chosen)
    if not layer_pins_kiln:
        DictUtils.set(flags, "kiln.ref", archetypes.KILN_REF)
    if module is not None:
        DictUtils.set(flags, f"archetype.{archetype}.module", module)
    package = module or module_name(name)
    for key, value in python_starter.starter_flags(archetype, name, package).items():
        DictUtils.set(flags, key, value)

    return ConfigManager().resolve(flags=flags, source=source)


def _report(directory: Path, config: KilnConfig, rows: list[dict[str, str]]) -> None:
    """Print or emit *rows*: JSON in JSON mode, else the resolved TOML and a line each."""
    payload = {
        "root": str(directory.resolve()),
        "config": config.to_document(),
        "artifacts": rows,
    }

    def text() -> None:
        console.print(DocumentUtils.dumps(config.to_document(), ConfigFormat.TOML))
        for row in rows:
            console.info("{} {} {}", row["key"], row["kind"], row["action"])

    output.emit(payload, text)


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


# `new`'s config-setting flags: every one of them must be backed by a
# registered module's `Option`, verified by `tests/commands/test_new_flags.py`.
FLAG_NAMES = ("archetype", "docs", "backend", "frontend")


def flag_layer(
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
    for flag_name in FLAG_NAMES:
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
