"""The artifacts `tasks` renders: `Taskfile.yml`, `tasks/*.yml`, and includes."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.archetypes import PYKIT_GIT, RN_FORGE_TAGS
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.config import DocsConfig
from rn_forge.kiln.modules.python.artifacts import root_package
from rn_forge.kiln.modules.tasks.config import TasksConfig

__all__ = ["render"]

_WORKSPACE_TASKS = (
    "workspace:install",
    "workspace:version",
    "workspace:build",
    "workspace:clean",
)
_QUALITY_TASKS = (
    "quality:lint:python",
    "quality:lint:markdown",
    "quality:lint:toml",
    "quality:lint:generated",
    "quality:lint:rn-forge-deps",
    "quality:lint:imports",
    "quality:lint:task-layout",
    "quality:lint:audit",
    "quality:format:python",
    "quality:format:markdown",
    "quality:format:toml",
    "quality:typecheck:python",
    "quality:test:python",
    "quality:test:coverage",
)
_CI_TASKS = (
    "ci:lint:entrypoint",
    "ci:lint:pins",
    "ci:lint:hooks",
    "ci:lint:workflows",
)
_DOCS_TASKS = (
    "docs:build",
    "docs:serve",
    "docs:generate",
    "docs:lint:site",
    "docs:lint:structure",
    "docs:lint:generate",
)


def _tasks_config(config: KilnConfig) -> TasksConfig:
    section = getattr(config.document, "tasks", None)
    return section if isinstance(section, TasksConfig) else TasksConfig()


def _site_dir(config: KilnConfig) -> str:
    docs = getattr(config.document, "docs", None)
    return docs.site_dir if isinstance(docs, DocsConfig) else ".docs-site"


def render(config: KilnConfig) -> list[Artifact]:
    """Render `Taskfile.yml`, `tasks/*.yml`, and one seeded file per include."""
    workspace = config.archetype == "python-lib"
    web = config.archetype in {"python-web-api", "python-web-app"}
    web_app = config.archetype == "python-web-app"
    packages = [Path(package).name for package in config.packages]
    api_package = f"{config.name}-api" if web else None
    web_dir = config.web_dir
    docs = config.docs_profile == "mkdocs"
    tasks_config = _tasks_config(config)

    known = {
        *_WORKSPACE_TASKS,
        *_QUALITY_TASKS,
        *_CI_TASKS,
        *(_DOCS_TASKS if docs else ()),
    }
    for key in tasks_config.command_overrides:
        if key not in known:
            raise AppException(
                "tasks.command_overrides.{}: unknown task — this archetype renders {}",
                key,
                ", ".join(sorted(known)),
            )

    devops_name = "rn-forge-devops"
    if devops_name in packages:
        devops = f"uv run {devops_name}"
    else:
        source = (
            f"{devops_name} @ {PYKIT_GIT}@{RN_FORGE_TAGS[devops_name]}"
            f"#subdirectory=packages/{devops_name}"
        )
        devops = f'uvx --from "{source}" {devops_name}'

    context: dict[str, object] = {
        "devops": devops,
        "kiln_version": __version__,
        "name": config.name,
        "package": config.module,
        "workspace": workspace,
        "packages": packages,
        "package_dirs": list(config.packages),
        "docs": docs,
        "site_dir": _site_dir(config),
        "includes": tasks_config.includes,
        "extra_refs": tasks_config.extra_refs,
        "overrides": tasks_config.command_overrides,
        "audit_ignore": [entry.id for entry in tasks_config.audit.ignore],
        "audit_excluded": [*sorted(RN_FORGE_TAGS), "rn-forge-kiln"],
        "web": web,
        "web_app": web_app,
        "backend": config.backend,
        "api_dir": config.api_dir,
        "api_package": api_package,
        "api_module": root_package(api_package) if api_package else None,
        "web_dir": web_dir,
        "web_project": Path(web_dir).name if web_dir else None,
    }
    engine = TemplateEngine(
        package="rn_forge.kiln.modules.tasks",
        variable_start_string="[[",
        variable_end_string="]]",
    )
    artifacts = [
        Artifact(
            "Taskfile.yml",
            ArtifactKind.MANAGED,
            engine.render("Taskfile.yml.j2", context),
        ),
        Artifact(
            "tasks/workspace.yml",
            ArtifactKind.MANAGED,
            engine.render("tasks/workspace.yml.j2", context),
        ),
        Artifact(
            "tasks/quality.yml",
            ArtifactKind.MANAGED,
            engine.render("tasks/quality.yml.j2", context),
        ),
    ]
    if docs:
        artifacts.append(
            Artifact(
                "tasks/docs.yml",
                ArtifactKind.MANAGED,
                engine.render("tasks/docs.yml.j2", context),
            )
        )
    if web:
        artifacts.append(
            Artifact(
                "tasks/api.yml",
                ArtifactKind.MANAGED,
                engine.render("tasks/api.yml.j2", context),
            )
        )
    if web_app:
        artifacts.append(
            Artifact(
                "tasks/web.yml",
                ArtifactKind.MANAGED,
                engine.render("tasks/web.yml.j2", context),
            )
        )
    artifacts.append(
        Artifact(
            "tasks/ci.yml",
            ArtifactKind.MANAGED,
            engine.render("tasks/ci.yml.j2", context),
        )
    )
    for include in tasks_config.includes:
        artifacts.append(
            Artifact(
                include.taskfile,
                ArtifactKind.SEEDED,
                engine.render("tasks/include.yml.j2", {"kiln_version": __version__}),
            )
        )
    return artifacts
