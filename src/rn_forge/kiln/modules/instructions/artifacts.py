"""The artifacts `instructions` renders: the kiln block in `AGENTS.md`, and `standard.md`."""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.commons.generation.templated import TemplateArtifact, render_artifacts
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln import __version__
from rn_forge.kiln.config import KilnConfig

__all__ = ["KILN_BLOCK", "context", "md_cell", "render"]

KILN_BLOCK = ManagedBlock("rn-forge kiln", comment="<!--")
"""kiln's fenced block in the repo's `AGENTS.md`."""

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
_DOCS_VERBS = "`docs:build docs:serve docs:generate`"
_WEB_VERBS = "`web:dev`"


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


def _refill(markdown: str) -> str:
    """*markdown* with its paragraphs and top-level bullets wrapped as mdformat wraps them.

    `standard.md` interpolates values and switches whole sentences on and off, so
    no hand-wrapping in the template is right for every cell. Headings, tables,
    comments and code fences pass through; runs of blank lines collapse to one.
    """
    lines = markdown.split("\n")
    out: list[str] = []
    fenced = False
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if fenced or line.startswith("```"):
            fenced = fenced != line.startswith("```")
            out.append(line)
        elif not line.strip():
            if out and out[-1]:
                out.append("")
        elif line.startswith(("#", "|", "<!--")):
            out.append(line)
        else:
            bullet = line.startswith("- ")
            words = [line[2:] if bullet else line]
            while (
                i < len(lines)
                and lines[i].strip()
                and not lines[i].startswith(("- ", "#", "|", "<!--", "```"))
            ):
                words.append(lines[i])
                i += 1
            text = " ".join(words)
            out.append(_bullet(text) if bullet else _paragraph(text))
    return "\n".join(out).rstrip("\n") + "\n"


_CELL_ESCAPE = re.compile(r"(`[^`]*`)|([<*])")


def md_cell(text: str) -> str:
    """*text* as the content of one Markdown table cell.

    A pipe is escaped everywhere; `<` and `*` are escaped outside a code span,
    as mdformat writes them.
    """
    escaped = _CELL_ESCAPE.sub(lambda m: m.group(1) or f"\\{m.group(2)}", text)
    return escaped.replace("|", "\\|")


_API_SERVES = "`task api:dev` serves `{api_dir}/src/{api_module}/app.py`, "
_API_REPO_OWNED = (
    "which must define the ASGI application as `app`. The application "
    "and its tests are repo-owned: kiln renders nothing under `src/` or "
    "`tests/`, so create that module yourself."
)
_API_SEEDED = (
    "which defines the ASGI application as `app`. `kiln new` seeded it "
    "with a small router and a test; the application and its tests are "
    "repo-owned from then on."
)


def _display_archetype(config: KilnConfig) -> str:
    if config.archetype == "python-app" and config.lifecycle:
        return "python-tool"
    return config.archetype


def _selectors(config: KilnConfig) -> str:
    if not config.is_web:
        return ""
    frontend = f", frontend: `{config.frontend}`" if config.is_web_app else ""
    return f" (backend: `{config.backend}`{frontend})"


def _tools(config: KilnConfig) -> str:
    if config.is_node_lib:
        # node-lib's `forbidden_tools` less `kiln`, which the bullet adds itself.
        # `mkdocs` stays whatever the docs profile, as the ci-entrypoint check
        # reads the same list.
        return "`uv`, `mkdocs`, `pnpm`, `npx`, `nx`, `ng`"
    tools = "`uv`, `pytest`, `ruff`, `pyright`"
    if config.docs_profile == "mkdocs":
        tools += ", `mkdocs`"
    if config.is_web_app:
        tools += ", `pnpm`, `npx`, `nx`, `ng`"
    return tools


def _verbs(config: KilnConfig) -> str:
    mkdocs = config.docs_profile == "mkdocs"
    verbs = f", plus {_DOCS_VERBS}" if mkdocs else ""
    if config.is_web:
        verbs += " and `api:dev`" if mkdocs else ", plus `api:dev`"
        verbs += " `api:migrate`" if config.backend == "django" else ""
    if config.is_web_app:
        verbs += f", plus {_WEB_VERBS}"
    return verbs


def _archetype_bullet(config: KilnConfig) -> str:
    sonar = "on" if config.ci.sonar else "off"
    return _bullet(
        f"**Archetype:** `{_display_archetype(config)}`{_selectors(config)} · "
        f"**Docs profile:** `{config.docs_profile}` · "
        f"**CI:** GitHub Actions, Sonar {sonar}"
    )


def _entrypoint_bullet(config: KilnConfig) -> str:
    if config.is_node_lib:
        return _bullet(
            f"**Entrypoint:** `task`. Workflows and the gate never invoke "
            f"{_tools(config)} or `kiln` directly; a document may name a "
            f"project-scoped native command no verb covers — the ten root "
            f"verbs are {_ROOT_VERBS}{_verbs(config)}."
        )
    return _bullet(
        f"**Entrypoint:** `task`. Never invoke {_tools(config)} "
        f"or `kiln` directly, in a workflow or in a document — the ten root "
        f"verbs are {_ROOT_VERBS}{_verbs(config)}."
    )


def _frontend_bullet(config: KilnConfig) -> str:
    web_dir = config.web_dir
    return _bullet(
        f"**Frontend:** `{config.frontend}`, managed by pnpm + Nx at "
        f"`{web_dir}` (project `{config.web_project}`). "
        "Every file the frontend scaffold wrote is repo-owned; kiln renders "
        f"nothing under `{web_dir}`, and seeded a starter page that calls the "
        "API (`src/app/app.ts`, `app.html`, their specs, `app.config.ts` and "
        "`proxy.conf.json`) once at `kiln new`."
    )


def _api_paragraph(config: KilnConfig) -> str:
    serves = _API_SERVES.format(api_dir=config.api_dir, api_module=config.api_module)
    seeded = config.backend == "fastapi"
    return _paragraph(serves + (_API_SEEDED if seeded else _API_REPO_OWNED))


def context(config: KilnConfig) -> dict[str, object]:
    """The template context every `instructions` template renders with."""
    docs = config.docs
    web_dir = config.web_dir
    public = config.public_tasks()
    return {
        "archetype_bullet": _archetype_bullet(config),
        "entrypoint_bullet": _entrypoint_bullet(config),
        "frontend_bullet": _frontend_bullet(config),
        "api_paragraph": _api_paragraph(config),
        "docs_bullet": _bullet(f"**Docs:** external, at [docs]({docs.external_url})."),
        "developer_tasks": [t for t in public if not t.name.startswith("ci:")],
        "ci_tasks": [t for t in public if t.name.startswith("ci:")],
        "ci_matrix": config.ci_matrix(),
        "kiln_version": __version__,
        "name": config.name,
        "display_archetype": _display_archetype(config),
        "lifecycle": config.lifecycle,
        "workspace": config.is_workspace,
        "packages": [Path(package).name for package in config.packages],
        "docs_profile": config.docs_profile,
        "docs": config.docs_profile == "mkdocs",
        "external_url": docs.external_url,
        "sonar": config.ci.sonar,
        "release": config.release,
        "npm_publish": config.release == "npm",
        "web": config.is_web,
        "web_app": config.is_web_app,
        "node_lib": config.is_node_lib,
        "release_group": config.release_group,
        "backend": config.backend,
        "frontend": config.frontend,
        "api_dir": config.api_dir,
        "web_dir": web_dir,
        "web_project": config.web_project,
    }


def render(config: KilnConfig) -> list[Artifact]:
    """Render the kiln block in `AGENTS.md` and `.rn-forge/kiln/standard.md`."""
    engine = TemplateEngine.cached(package=_PACKAGE)
    engine.environment.filters["md_cell"] = md_cell
    values = context(config)
    artifacts = render_artifacts(
        engine,
        values,
        [
            TemplateArtifact(
                "AGENTS.md",
                ArtifactKind.BLOCK,
                template="block.md.j2",
                block=KILN_BLOCK,
            ),
            TemplateArtifact(".rn-forge/kiln/standard.md", template="standard.md.j2"),
        ],
    )
    return [
        dataclasses.replace(artifact, content=_refill(artifact.content))
        if artifact.path == ".rn-forge/kiln/standard.md"
        else artifact
        for artifact in artifacts
    ]
