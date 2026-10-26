"""The seeded starter source `frontend` writes once, at `kiln new`."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.fs.documents import DocumentError, DocumentUtils
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.commons.generation.templated import TemplateArtifact, render_artifacts
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.frontend.angular import SCAFFOLD_APP_DIR

__all__ = ["render"]

_APP_FILES = {
    "src/app/app.config.ts": "angular/app.config.ts.j2",
    "src/app/app.config.spec.ts": "angular/app.config.spec.ts.j2",
    "src/app/app.ts": "angular/app.ts.j2",
    "src/app/app.html": "angular/app.html.j2",
    "src/app/app.spec.ts": "angular/app.spec.ts.j2",
    "proxy.conf.json": "angular/proxy.conf.json.j2",
}


_NGKIT_PACKAGE = "@rn-forge/ng"


def _has_ngkit(root: Path) -> bool:
    try:
        package = DocumentUtils.read(root / "package.json")
    except DocumentError:
        return False
    dependencies = package.get("dependencies")
    return isinstance(dependencies, dict) and _NGKIT_PACKAGE in dependencies


def render(config: KilnConfig, root: Path) -> list[Artifact]:
    """Render the Angular starter for *config* at *root*.

    Returns `SEEDED` artifacts for `python-web-app` with `frontend = "angular"`
    when `<web_dir>/src/app/app.config.ts` exists under *root* and *root*'s
    `package.json` lists `@rn-forge/ng` in `dependencies`; otherwise `[]`.
    """
    if config.archetype != "python-web-app" or config.frontend != "angular":
        return []
    web_dir = config.web_dir or SCAFFOLD_APP_DIR
    if not (root / web_dir / "src" / "app" / "app.config.ts").is_file():
        return []
    if not _has_ngkit(root):
        return []
    engine = TemplateEngine.cached(package="rn_forge.kiln.modules.frontend")
    return render_artifacts(
        engine,
        {"name": config.name},
        [
            TemplateArtifact(
                f"{web_dir}/{relative}", ArtifactKind.SEEDED, template=template
            )
            for relative, template in _APP_FILES.items()
        ],
    )
