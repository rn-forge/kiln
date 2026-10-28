"""The artifacts `tasks` renders: `Taskfile.yml`, `tasks/*.yml`, and includes."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.commons.generation.templated import TemplateArtifact, render_artifacts
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.archetypes import KILN_REF, RN_FORGE_TAGS, kiln_command
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.config import DocsConfig
from rn_forge.kiln.modules.python.artifacts import root_package
from rn_forge.kiln.modules.tasks.config import TasksConfig

__all__ = ["render"]

_WORKSPACE_TASKS = ("workspace:clean",)
_QUALITY_TASKS = (
    "quality:lint:markdown",
    "quality:lint:toml",
    "quality:format:markdown",
    "quality:format:toml",
)
_PYTHON_TASKS = (
    "python:install",
    "python:lint",
    "python:lint:imports",
    "python:lint:audit",
    "python:format",
    "python:typecheck",
    "python:test",
    "python:test:coverage",
    "python:build",
    "python:version",
)
_CI_TASKS = ("ci:lint:workflows",)
_NODE_TASKS = ("node:install", "node:lint", "node:test", "node:build")
_DOCS_TASKS = ("docs:build", "docs:serve", "docs:generate")


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
        *_PYTHON_TASKS,
        *_CI_TASKS,
        *(_DOCS_TASKS if docs else ()),
        *(_NODE_TASKS if web_app else ()),
    }
    for key in tasks_config.command_overrides:
        if key not in known:
            raise AppException(
                "tasks.command_overrides.{}: unknown task — this archetype renders {}",
                key,
                ", ".join(sorted(known)),
            )

    # Kiln's own repository runs its working tree.
    pin = getattr(config.document, "kiln", None)
    ref = pin.ref if pin is not None else KILN_REF
    if config.module == "rn_forge.kiln":
        kiln = "uv run kiln"
        devops = "uv run kiln-devops"
    else:
        kiln = kiln_command(ref)
        devops = kiln_command(ref, "kiln-devops")

    context: dict[str, object] = {
        "devops": devops,
        "kiln": kiln,
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
        "audit_excluded": sorted(RN_FORGE_TAGS),
        "web": web,
        "web_app": web_app,
        "backend": config.backend,
        "api_dir": config.api_dir,
        "api_package": api_package,
        "api_module": root_package(api_package) if api_package else None,
        "web_dir": web_dir,
        "web_project": Path(web_dir).name if web_dir else None,
    }
    engine = TemplateEngine.cached(
        package="rn_forge.kiln.modules.tasks",
        variable_start_string="[[",
        variable_end_string="]]",
    )
    return render_artifacts(
        engine,
        context,
        [
            TemplateArtifact("Taskfile.yml"),
            TemplateArtifact("tasks/workspace.yml"),
            TemplateArtifact("tasks/quality.yml"),
            TemplateArtifact("tasks/python.yml"),
            TemplateArtifact("tasks/kiln.yml"),
            TemplateArtifact("tasks/docs.yml", enabled=docs),
            TemplateArtifact("tasks/api.yml", enabled=web),
            TemplateArtifact("tasks/web.yml", enabled=web_app),
            TemplateArtifact("tasks/node.yml", enabled=web_app),
            TemplateArtifact("tasks/ci.yml"),
            *(
                TemplateArtifact(
                    include.taskfile,
                    ArtifactKind.SEEDED,
                    template="tasks/include.yml.j2",
                    context={"kiln_version": __version__},
                )
                for include in tasks_config.includes
            ),
        ],
    )
