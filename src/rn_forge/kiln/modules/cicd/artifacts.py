"""The artifacts `cicd` renders: the workflows, the setup action, Sonar's properties and `node-lib`'s Nx Cloud agents."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import cast

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.generation import Artifact
from rn_forge.commons.generation.templated import TemplateArtifact, render_artifacts
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd import registry
from rn_forge.kiln.modules.cicd.config import CiConfig
from rn_forge.kiln.modules.core.versions import PYTHON_VERSION

__all__ = ["SONAR_ORGANIZATION", "load_pins", "render"]

SONAR_ORGANIZATION = "rn-forge"
"""The SonarCloud organization every rendered repo reports to."""

_PACKAGE = "rn_forge.kiln.modules.cicd"

_NX_CLOUD_IMAGE = "ubuntu22.04-node24.14-v1"

# The scaffold's `--name`. Angular writes coverage under it, and moving the app
# to another `web_dir` does not rename the project.
_WEB_PROJECT = "web"

_NODE_LIB_EXCLUSIONS = (
    "**/node_modules/**",
    "**/dist/**",
    "**/*.stories.ts",
    "**/.storybook/**",
    "**/.venv/**",
)
_WEB_APP_EXCLUSIONS = ("**/node_modules/**", "**/dist/**", "**/*.spec.ts")

_PLAN_KEYS = (
    "release-order",
    "packages",
    "integration",
    "smoke",
    "suites",
    "pytest-args",
    "cov-args",
    "test-paths",
    "sonar-sources",
    "sonar-tests",
    "sonar",
    "docs",
)


def load_pins() -> dict[str, dict[str, str]]:
    """The pinned action set, one table per action, from `pins.toml`."""
    return cast(
        "dict[str, dict[str, str]]",
        DocumentUtils.read(files(_PACKAGE).joinpath("pins.toml")),
    )


def pinned_actions() -> list[str]:
    """The `owner/repo` of every pinned action, sorted: Dependabot's
    `dependency-name` for a sub-path action (`github/codeql-action/upload-sarif`)
    is its repository."""
    return sorted(
        {
            "/".join(table["uses"].split("/")[:2])
            for table in load_pins().values()
            if "uses" in table
        }
    )


def _ci_config(config: KilnConfig) -> CiConfig:
    section = getattr(config.document, "ci", None)
    return section if isinstance(section, CiConfig) else CiConfig()


def render(config: KilnConfig) -> list[Artifact]:
    """Render the setup action, `ci.yml` and its reusable stage workflows `_<stage>.yml`, `dependabot.yml`, `scorecard.yml` (when `ci.checks.scorecard` is on), `sonar-project.properties` and, for `node-lib`, `.nx/workflows/agents.yaml`.

    Raises:
        AppException: `ci.provider` is `ado`, which is reserved, or `ci.hooks.docs` is set without a docs site.
        ValueError: `ci.release` does not fit the archetype.
    """
    ci = _ci_config(config)
    if ci.provider == "ado":
        raise AppException(
            "cicd.render: ci.provider = 'ado' is reserved for E8 and renders nothing yet"
        )
    docs = config.docs_profile == "mkdocs"
    release = config.release
    checks = registry.enabled_names(ci, config.archetype, len(config.packages))
    if "umbrella-release" in checks and ci.release == "none":
        raise AppException(
            "cicd.render: ci.checks.umbrella-release needs [ci] release other than none"
        )
    if ci.hooks.docs and not docs:
        raise AppException(
            "cicd.render: ci.hooks.docs is set but nothing deploys Pages (docs profile is not mkdocs)"
        )
    workspace = config.archetype == "python-lib"
    web = config.archetype in {"python-web-api", "python-web-app"}
    web_app = config.archetype == "python-web-app"
    node_lib = config.archetype == "node-lib"
    context: dict[str, object] = {
        "kiln_version": __version__,
        "name": config.name,
        "workspace": workspace,
        "packages": [Path(package).name for package in config.packages],
        "docs": docs,
        "python_version": PYTHON_VERSION,
        "site_dir": config.docs_site_dir,
        "sonar": ci.sonar,
        "sonar_exclusions": [
            *(_NODE_LIB_EXCLUSIONS if node_lib else ()),
            *(_WEB_APP_EXCLUSIONS if web_app else ()),
            *ci.sonar_exclusions,
        ],
        "sonar_coverage_exclusions": list(ci.sonar_coverage_exclusions),
        "release": release,
        "doctor_full": ci.doctor_full,
        "checks": checks,
        "plan_keys": _PLAN_KEYS,
        "pins": load_pins(),
        "pinned_actions": pinned_actions(),
        "organization": SONAR_ORGANIZATION,
        "web": web,
        "web_app": web_app,
        "node_lib": node_lib,
        "node": web_app or node_lib,
        "nx_cloud_image": _NX_CLOUD_IMAGE,
        "hooks": ci.hooks,
        "jobs": ci.jobs,
        "required_jobs": [job.name for job in ci.jobs if job.required],
        "check_jobs": [
            check.job
            for check in registry.CHECKS
            if check.gates and check.job and check.name in checks
        ],
        "api_dir": config.api_dir,
        "web_dir": config.web_dir,
        "web_project": _WEB_PROJECT,
    }
    # GitHub's own `${{ }}` expressions fill these templates, so Jinja's variables use `[[ ]]`.
    engine = TemplateEngine.cached(
        package=_PACKAGE, variable_start_string="[[", variable_end_string="]]"
    )
    stages = {
        "integration": not node_lib,
        "smoke": True,
        "sonar": ci.sonar,
        "release": release != "none",
        "verify-release": release != "none",
        "docs": docs,
    }
    rows = [
        (".github/actions/setup/action.yml", "action.yml.j2", True),
        (".github/workflows/ci.yml", "ci.yml.j2", True),
        *(
            (f".github/workflows/_{stage}.yml", f"workflows/_{stage}.yml.j2", enabled)
            for stage, enabled in stages.items()
        ),
        (".github/dependabot.yml", "dependabot.yml.j2", True),
        (
            ".github/workflows/scorecard.yml",
            "scorecard.yml.j2",
            "scorecard" in checks,
        ),
        (".nx/workflows/agents.yaml", "agents.yaml.j2", node_lib),
        ("sonar-project.properties", "sonar-project.properties.j2", ci.sonar),
    ]
    return render_artifacts(
        engine,
        context,
        [
            TemplateArtifact(path, template=template, enabled=enabled)
            for path, template, enabled in rows
        ],
    )
