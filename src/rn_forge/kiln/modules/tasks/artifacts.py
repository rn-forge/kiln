"""The artifacts `tasks` renders: `Taskfile.yml`, `tasks/*.yml`, and includes."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln import __version__
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
    "quality:lint:generated",
    "quality:lint:rn-forge-deps",
    "quality:lint:imports",
    "quality:lint:task-layout",
    "quality:lint:ci-entrypoint",
    "quality:format:python",
    "quality:format:markdown",
    "quality:typecheck:python",
    "quality:test:python",
    "quality:test:coverage",
)
_QUALITY_DOCS_TASKS = (
    "quality:lint:docs",
    "quality:lint:docs-structure",
    "quality:lint:docs-nav",
)
_DOCS_TASKS = ("docs:build", "docs:serve", "docs:nav", "docs:structure")


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
    for package in config.packages:
        if not web and Path(package).parts[:-1] != ("packages",):
            raise AppException(
                "tasks.render: {} is not laid out as packages/<name>", package
            )
    packages = [Path(package).name for package in config.packages]
    api_package = f"{config.name}-api" if web else None
    web_dir = config.web_dir
    docs = config.docs_profile == "mkdocs"
    tasks_config = _tasks_config(config)

    known = {
        *_WORKSPACE_TASKS,
        *_QUALITY_TASKS,
        *(_QUALITY_DOCS_TASKS if docs else ()),
        *(_DOCS_TASKS if docs else ()),
    }
    for key in tasks_config.command_overrides:
        if key not in known:
            raise AppException(
                "tasks.command_overrides.{}: unknown task — this archetype renders {}",
                key,
                ", ".join(sorted(known)),
            )

    context: dict[str, object] = {
        "kiln_version": __version__,
        "name": config.name,
        "package": root_package(config.name),
        "workspace": workspace,
        "packages": packages,
        "docs": docs,
        "site_dir": _site_dir(config),
        "includes": tasks_config.includes,
        "extra_refs": tasks_config.extra_refs,
        "overrides": tasks_config.command_overrides,
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
    for include in tasks_config.includes:
        artifacts.append(
            Artifact(
                include.taskfile,
                ArtifactKind.SEEDED,
                engine.render("tasks/include.yml.j2", {"kiln_version": __version__}),
            )
        )
    return artifacts
