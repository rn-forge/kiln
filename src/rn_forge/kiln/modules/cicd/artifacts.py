"""The artifacts `cicd` renders: the workflows, the setup action, and Sonar's properties."""

from __future__ import annotations

import tomllib
from importlib.resources import files
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.config import CiConfig

__all__ = ["SONAR_ORGANIZATION", "load_pins", "render"]

SONAR_ORGANIZATION = "rn-forge"
"""The SonarCloud organization every rendered repo reports to."""

_PACKAGE = "rn_forge.kiln.modules.cicd"


def load_pins() -> dict[str, dict[str, str]]:
    """The pinned action set, one table per action, from `pins.toml`."""
    text = files(_PACKAGE).joinpath("pins.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)


def _ci_config(config: KilnConfig) -> CiConfig:
    section = getattr(config.document, "ci", None)
    return section if isinstance(section, CiConfig) else CiConfig()


def render(config: KilnConfig) -> list[Artifact]:
    """Render the setup action, `ci.yml`, `docs.yml` and `sonar-project.properties`.

    Raises:
        AppException: `ci.provider` is `ado`, which is reserved.
    """
    ci = _ci_config(config)
    if ci.provider == "ado":
        raise AppException(
            "cicd.render: ci.provider = 'ado' is reserved for E8 and renders nothing yet"
        )
    docs = config.docs_profile == "mkdocs"
    web = config.archetype in {"python-web-api", "python-web-app"}
    web_app = config.archetype == "python-web-app"
    context: dict[str, object] = {
        "kiln_version": __version__,
        "name": config.name,
        "workspace": config.archetype == "python-lib",
        "packages": [Path(package).name for package in config.packages],
        "docs": docs,
        "sonar": ci.sonar,
        "release": ci.release,
        "pins": load_pins(),
        "organization": SONAR_ORGANIZATION,
        "web": web,
        "web_app": web_app,
        "api_dir": config.api_dir,
        "web_dir": config.web_dir,
    }
    # GitHub's own `${{ }}` expressions fill these templates, so Jinja's variables use `[[ ]]`.
    engine = TemplateEngine(
        package=_PACKAGE, variable_start_string="[[", variable_end_string="]]"
    )
    rows = [
        (".github/actions/setup/action.yml", "action.yml.j2", True),
        (".github/workflows/ci.yml", "ci.yml.j2", True),
        (".github/workflows/docs.yml", "docs.yml.j2", docs),
        ("sonar-project.properties", "sonar-project.properties.j2", ci.sonar),
    ]
    return [
        Artifact(path, ArtifactKind.MANAGED, engine.render(template, context))
        for path, template, enabled in rows
        if enabled
    ]
