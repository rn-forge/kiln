"""The artifacts `instructions` renders: the kiln block in `CLAUDE.md`, and `standard.md`."""

from __future__ import annotations

import re
from pathlib import Path

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.config import CiConfig
from rn_forge.kiln.modules.docs.config import DocsConfig

__all__ = ["KILN_BLOCK", "context", "render"]

KILN_BLOCK = ManagedBlock("rn-forge kiln", comment="<!--")
"""kiln's fenced block in the repo's `CLAUDE.md`."""

_PACKAGE = "rn_forge.kiln.modules.instructions"

_WRAP_FIRST = 80
"""The `wrap` the seeded `.mdformat.toml` sets, for a bullet's first line."""

_WRAP_REST = 78
"""A bullet's later lines: `mdformat-mkdocs` reserves four columns of indent for
a list item, so they hold two fewer characters than the first."""

_TOKEN = re.compile(r"(?:[^\s`]|`[^`]*`)+")
"""A word; a code span is one, spaces and all, as mdformat never breaks inside one."""

_ROOT_VERBS = (
    "`setup validate lint format typecheck test test:coverage build clean version`"
)
_DOCS_VERBS = "`docs:build docs:serve docs:generate docs:structure`"
_WEB_VERBS = "`web:lint web:test web:build web:dev`"


def _bullet(text: str) -> str:
    """*text* as one Markdown bullet, wrapped exactly as mdformat wraps it.

    The bullets that interpolate a name or a selector cannot be hand-wrapped in
    a template: the right break depends on the value. Filling them here keeps
    the block mdformat-clean for any value, so `task format` never rewrites it.
    """
    lines: list[str] = []
    line = "-"
    for token in _TOKEN.findall(text):
        limit = _WRAP_REST if lines else _WRAP_FIRST
        if len(line) + 1 + len(token) > limit and line.strip() != "-":
            lines.append(line)
            line = "  " + token
        else:
            line += " " + token
    lines.append(line)
    return "\n".join(lines)


def _paragraph(text: str) -> str:
    """*text* as one Markdown paragraph, wrapped exactly as mdformat wraps it."""
    lines: list[str] = []
    line = ""
    for token in _TOKEN.findall(text):
        if line and len(line) + 1 + len(token) > _WRAP_FIRST:
            lines.append(line)
            line = token
        else:
            line = f"{line} {token}" if line else token
    lines.append(line)
    return "\n".join(lines)


def context(config: KilnConfig) -> dict[str, object]:
    """The template context every `instructions` template renders with."""
    docs = getattr(config.document, "docs", None)
    ci = getattr(config.document, "ci", None)
    ci = ci if isinstance(ci, CiConfig) else CiConfig()
    lifecycle = config.lifecycle
    web = config.archetype in {"python-web-api", "python-web-app"}
    web_app = config.archetype == "python-web-app"
    web_dir = config.web_dir
    sonar = "on" if ci.sonar else "off"
    display = (
        "python-tool"
        if config.archetype == "python-app" and lifecycle
        else config.archetype
    )
    selectors = f" (backend: `{config.backend}`" if web else ""
    if web_app:
        selectors += f", frontend: `{config.frontend}`"
    selectors += ")" if web else ""
    api_module = f"{config.name}-api".replace("-", "_")
    tools = "`uv`, `pytest`, `ruff`, `pyright`"
    if config.docs_profile == "mkdocs":
        tools += ", `mkdocs`"
    if web_app:
        tools += ", `pnpm`, `npx`, `nx`, `ng`"
    verbs = ""
    if config.docs_profile == "mkdocs":
        verbs = f", plus {_DOCS_VERBS}"
    if web:
        verbs += (
            " and `api:dev`" if config.docs_profile == "mkdocs" else ", plus `api:dev`"
        )
        verbs += " `api:migrate`" if config.backend == "django" else ""
    if web_app:
        verbs += f", plus {_WEB_VERBS}"
    bullets = {
        "archetype_bullet": _bullet(
            f"**Archetype:** `{display}`{selectors} · **Docs profile:** "
            f"`{config.docs_profile}` · **CI:** GitHub Actions, Sonar {sonar}"
        ),
        "entrypoint_bullet": _bullet(
            f"**Entrypoint:** `task`. Never invoke {tools} "
            f"or `kiln` directly, in a workflow or in a document — the ten root "
            f"verbs are {_ROOT_VERBS}{verbs}."
        ),
        "frontend_bullet": _bullet(
            f"**Frontend:** `{config.frontend}`, managed by pnpm + Nx at "
            f"`{web_dir}` (project `{Path(web_dir).name if web_dir else ''}`). "
            "Every file the frontend scaffold wrote is repo-owned; kiln renders "
            f"nothing under `{web_dir}`."
        ),
        "api_paragraph": _paragraph(
            f"`task api:dev` serves `{config.api_dir}/src/{api_module}/app.py`, "
            "which must define the ASGI application as `app`. The application "
            "and its tests are repo-owned: kiln renders nothing under `src/` or "
            "`tests/`, so create that module yourself."
        ),
        "docs_bullet": _bullet(
            f"**Docs:** external, at [docs]({docs.external_url if isinstance(docs, DocsConfig) else ''})."
        ),
    }
    return {
        **bullets,
        "kiln_version": __version__,
        "name": config.name,
        "display_archetype": display,
        "lifecycle": lifecycle,
        "workspace": config.archetype == "python-lib",
        "packages": [Path(package).name for package in config.packages],
        "docs_profile": config.docs_profile,
        "docs": config.docs_profile == "mkdocs",
        "external_url": docs.external_url if isinstance(docs, DocsConfig) else "",
        "sonar": ci.sonar,
        "release": ci.release,
        "web": web,
        "web_app": web_app,
        "backend": config.backend,
        "frontend": config.frontend,
        "api_dir": config.api_dir,
        "web_dir": web_dir,
        "web_project": Path(web_dir).name if web_dir else None,
    }


def render(config: KilnConfig) -> list[Artifact]:
    """Render the kiln block in `CLAUDE.md` and `.rn-forge/kiln/standard.md`."""
    engine = TemplateEngine(package=_PACKAGE)
    values = context(config)
    return [
        Artifact(
            "CLAUDE.md",
            ArtifactKind.BLOCK,
            engine.render("block.md.j2", values),
            block=KILN_BLOCK,
        ),
        Artifact(
            ".rn-forge/kiln/standard.md",
            ArtifactKind.MANAGED,
            engine.render("standard.md.j2", values),
        ),
    ]
