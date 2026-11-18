"""The artifacts `tasks` renders: `Taskfile.yml`, `tasks/*.yml`, and includes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.commons.generation.templated import TemplateArtifact, render_artifacts
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.archetypes import KILN_GIT, KILN_REF, kiln_command
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.pins import load_pins

__all__ = ["render"]

_WORKSPACE_TASKS = ("workspace:clean",)
_QUALITY_TASKS = (
    "quality:lint:markdown",
    "quality:lint:toml",
    "quality:lint:yaml",
    "quality:format:markdown",
    "quality:format:toml",
    "quality:format:yaml",
)
_PYTHON_TASKS = (
    "python:install",
    "python:lint",
    "python:lint:imports",
    "python:format",
    "python:typecheck",
    "python:test",
    "python:test:coverage",
    "python:build",
    "python:version",
)
_CI_TASKS = ("ci:lint:workflows",)
_GITLEAKS_PLATFORMS = (
    ("Linux-x86_64", "linux_x64"),
    ("Darwin-arm64", "darwin_arm64"),
)
# Dual-licensed Artistic or GPL, taken under Artistic; reached through the
# rendered docs group (mkdocs-monorepo-plugin -> python-slugify).
_LICENSES_ALWAYS_IGNORED = ("text-unidecode",)
_NODE_TASKS = (
    "node:install",
    "node:lint",
    "node:test",
    "node:build",
    "node:typecheck",
    "node:e2e",
    "node:format",
    "node:lint:format",
)
_DOCS_TASKS = ("docs:build", "docs:serve", "docs:generate")


def _validate_overrides(config: KilnConfig, known: set[str]) -> None:
    for key in config.tasks.command_overrides:
        if key not in known:
            raise AppException(
                "tasks.command_overrides.{}: unknown task — this archetype renders {}",
                key,
                ", ".join(sorted(known)),
            )


def _kiln_commands(config: KilnConfig) -> tuple[str, str]:
    """The `kiln` and `kiln-devops` command lines the Taskfiles call."""
    if config.module == "rn_forge.kiln":
        return "uv run kiln", "uv run kiln-devops"
    pin = config.kiln_pin
    ref = pin.ref if pin is not None else KILN_REF
    return kiln_command(ref), kiln_command(ref, "kiln-devops")


def _context(config: KilnConfig, *, docs: bool, node: bool) -> dict[str, object]:
    packages = [Path(package).name for package in config.packages]
    api_package = config.api_package
    tasks_config = config.tasks
    ci = config.ci
    policy = ci.licenses_policy()
    gitleaks = cast("dict[str, Any]", load_pins()["gitleaks"])
    kiln, devops = _kiln_commands(config)
    return {
        "devops": devops,
        "kiln": kiln,
        "kiln_git": KILN_GIT,
        "kiln_own": config.module == "rn_forge.kiln",
        "kiln_version": __version__,
        "name": config.name,
        "package": config.module,
        "workspace": config.is_workspace,
        "packages": packages,
        "package_dirs": list(config.packages),
        "docs": docs,
        "release": config.release,
        "site_dir": config.docs_site_dir,
        "includes": tasks_config.includes,
        "extra_refs": tasks_config.extra_refs,
        "overrides": tasks_config.command_overrides,
        "checks": config.ci_checks,
        "gitleaks": [
            {
                "uname": uname,
                "url": gitleaks[platform]["url"],
                "sha256": gitleaks[platform]["sha256"],
            }
            for uname, platform in _GITLEAKS_PLATFORMS
        ],
        "licenses_deny": policy.deny,
        "licenses_ignore": [
            *policy.ignore,
            *sorted({config.name, *packages, *([api_package] if api_package else [])}),
            *_LICENSES_ALWAYS_IGNORED,
        ],
        "licenses_ignore_node": list(policy.ignore),
        "audit_ignore": [entry.id for entry in ci.audit_policy().ignore],
        "sonar": ci.sonar,
        "web": config.is_web,
        "web_app": config.is_web_app,
        "node": node,
        "node_lib": config.is_node_lib,
        "release_group": config.release_group,
        "backend": config.backend,
        "api_dir": config.api_dir,
        "api_package": api_package,
        "api_module": config.api_module,
        "web_dir": config.web_dir,
        "web_project": config.web_project,
    }


def render(config: KilnConfig) -> list[Artifact]:
    """Render `Taskfile.yml`, `tasks/*.yml`, and one seeded file per include."""
    web = config.is_web
    web_app = config.is_web_app
    node = web_app or config.is_node_lib
    docs = config.docs_profile == "mkdocs"
    tasks_config = config.tasks
    ci = config.ci
    known = {
        *_WORKSPACE_TASKS,
        *_QUALITY_TASKS,
        *_PYTHON_TASKS,
        *_CI_TASKS,
        *(_DOCS_TASKS if docs else ()),
        *(_NODE_TASKS if node else ()),
    }
    _validate_overrides(config, known)
    context = _context(config, docs=docs, node=node)
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
            TemplateArtifact("tasks/node.yml", enabled=node),
            TemplateArtifact("tasks/ci.yml"),
            TemplateArtifact("tasks/sonar.yml", enabled=ci.sonar),
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
