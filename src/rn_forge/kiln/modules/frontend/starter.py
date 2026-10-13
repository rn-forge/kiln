"""The seeded starter source `frontend` writes once, at `kiln new`."""

from __future__ import annotations

from pathlib import Path

from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.frontend.angular import SCAFFOLD_APP_DIR

__all__ = ["render"]

_APP_FILES = {
    "app.config.ts": "angular/app.config.ts.j2",
    "app.config.spec.ts": "angular/app.config.spec.ts.j2",
}


def render(config: KilnConfig, root: Path) -> list[Artifact]:
    """Render the Angular starter for *config* at *root*.

    Returns `SEEDED` artifacts for `python-web-app` with `frontend = "angular"`
    when `<web_dir>/src/app/app.config.ts` exists under *root*; otherwise `[]`.
    """
    if config.archetype != "python-web-app" or config.frontend != "angular":
        return []
    web_dir = config.web_dir or SCAFFOLD_APP_DIR
    if not (root / web_dir / "src" / "app" / "app.config.ts").is_file():
        return []
    engine = TemplateEngine(package="rn_forge.kiln.modules.frontend")
    return [
        Artifact(
            f"{web_dir}/src/app/{name}",
            ArtifactKind.SEEDED,
            engine.render(template, {"name": config.name}),
        )
        for name, template in _APP_FILES.items()
    ]
