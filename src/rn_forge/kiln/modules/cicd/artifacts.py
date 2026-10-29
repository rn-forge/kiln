"""The artifacts `cicd` renders: the workflows, the setup action, Sonar's properties and `node-lib`'s `tools/ci/` helpers."""

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
from rn_forge.kiln.modules.cicd.config import CiConfig

__all__ = ["SONAR_ORGANIZATION", "load_pins", "render"]

SONAR_ORGANIZATION = "rn-forge"
"""The SonarCloud organization every rendered repo reports to."""

_PACKAGE = "rn_forge.kiln.modules.cicd"

_NX_CLOUD_IMAGE = "ubuntu22.04-node24.14-v1"

_NODE_HELPERS = (
    "resolve-dist-workspace-deps",
    "verify-dist-manifest",
    "assemble-site",
    "release-notes",
)

_PLAN_KEYS = (
    "release-order",
    "packages",
    "postgres",
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


def _ci_config(config: KilnConfig) -> CiConfig:
    section = getattr(config.document, "ci", None)
    return section if isinstance(section, CiConfig) else CiConfig()


def render(config: KilnConfig) -> list[Artifact]:
    """Render the setup action, `ci.yml`, `dependabot.yml`, `docs.yml`, `sonar-project.properties` and, for `node-lib`, `.nx/workflows/agents.yaml` and `tools/ci/*.mjs`.

    A `python-lib` and a `node-lib` render no `docs.yml`: their `ci.yml` has the one Pages deploy.

    Raises:
        AppException: `ci.provider` is `ado`, which is reserved, or `ci.hooks.docs` is set without a docs site.
        ValueError: `ci.release` is `pypi` outside a library workspace.
    """
    ci = _ci_config(config)
    if ci.provider == "ado":
        raise AppException(
            "cicd.render: ci.provider = 'ado' is reserved for E8 and renders nothing yet"
        )
    docs = config.docs_profile == "mkdocs"
    if ci.release == "pypi" and config.archetype != "python-lib":
        raise ValueError("ci.release = 'pypi' needs a library workspace")
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
        "sonar": ci.sonar,
        "release": ci.release,
        "doctor_full": ci.doctor_full,
        "plan_keys": _PLAN_KEYS,
        "pins": load_pins(),
        "organization": SONAR_ORGANIZATION,
        "web": web,
        "web_app": web_app,
        "node_lib": node_lib,
        "nx_cloud_image": _NX_CLOUD_IMAGE,
        "hooks": ci.hooks,
        "jobs": ci.jobs,
        "api_dir": config.api_dir,
        "web_dir": config.web_dir,
    }
    # GitHub's own `${{ }}` expressions fill these templates, so Jinja's variables use `[[ ]]`.
    engine = TemplateEngine.cached(
        package=_PACKAGE, variable_start_string="[[", variable_end_string="]]"
    )
    rows = [
        (".github/actions/setup/action.yml", "action.yml.j2", True),
        (".github/workflows/ci.yml", "ci.yml.j2", True),
        (".github/dependabot.yml", "dependabot.yml.j2", True),
        (
            ".github/workflows/docs.yml",
            "docs.yml.j2",
            docs and not workspace and not node_lib,
        ),
        (".nx/workflows/agents.yaml", "agents.yaml.j2", node_lib),
        ("sonar-project.properties", "sonar-project.properties.j2", ci.sonar),
        *(
            (f"tools/ci/{name}.mjs", f"tools/ci/{name}.mjs.j2", node_lib)
            for name in _NODE_HELPERS
        ),
    ]
    return render_artifacts(
        engine,
        context,
        [
            TemplateArtifact(path, template=template, enabled=enabled)
            for path, template, enabled in rows
        ],
    )
