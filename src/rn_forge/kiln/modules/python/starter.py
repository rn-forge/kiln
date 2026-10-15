"""The seeded starter source `python` writes once, at `kiln new`."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path

from rn_forge.tooling.generation import Artifact, ArtifactKind
from rn_forge.tooling.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.python.artifacts import root_package

__all__ = ["render", "seedable"]

_TOOL_SRC = {
    "main.py": "main_tool.py.j2",
    "commands.py": "commands.py.j2",
    "product.py": "product.py.j2",
}
_TOOL_TESTS = {
    "test_cli.py": "test_cli.py.j2",
    "test_product.py": "test_product.py.j2",
}
_APP_SRC = {"main.py": "main_app.py.j2", "commands.py": "commands.py.j2"}
_APP_TESTS = {"test_cli.py": "test_cli.py.j2"}
_LIB_SRC = {"settings.py": "settings.py.j2"}
_LIB_TESTS = {"test_settings.py": "test_settings.py.j2"}
_API_SRC = {
    "app.py": "fastapi/app.py.j2",
    "errors.py": "fastapi/errors.py.j2",
    "routes.py": "fastapi/routes.py.j2",
}
_API_TESTS = {"test_app.py": "fastapi/test_app.py.j2"}


def seedable(package_dir: Path, starter: Collection[str]) -> bool:
    """Whether *package_dir* is still a fresh package.

    True when *package_dir* is a directory and every `*.py` file directly in it
    is `__init__.py` or named in *starter*.
    """
    if not package_dir.is_dir():
        return False
    allowed = {"__init__.py", *starter}
    return all(path.name in allowed for path in package_dir.glob("*.py"))


def render(config: KilnConfig, root: Path) -> list[Artifact]:
    """Render the starter source for *config* at *root*.

    Returns `SEEDED` artifacts, or `[]` for an archetype with no starter or a
    package that already holds product code.
    """
    engine = TemplateEngine(package="rn_forge.kiln.modules.python")
    if config.archetype in {"python-tool", "python-app"}:
        tool = config.archetype == "python-tool"
        package = root_package(config.name)
        return _render(
            engine,
            root,
            base="",
            module=package,
            src=_TOOL_SRC if tool else _APP_SRC,
            tests=_TOOL_TESTS if tool else _APP_TESTS,
            context={"name": config.name, "package": package},
        )
    if config.archetype == "python-lib":
        artifacts: list[Artifact] = []
        for member in config.packages:
            module = config.module_for(member)
            artifacts += _render(
                engine,
                root,
                base=f"{member}/",
                module=module,
                src=_LIB_SRC,
                tests=_LIB_TESTS,
                context={"name": config.name, "module": module},
            )
        return artifacts
    if config.archetype in {"python-web-api", "python-web-app"}:
        if config.backend != "fastapi":
            return []
        module = root_package(f"{config.name}-api")
        return _render(
            engine,
            root,
            base=f"{config.api_dir}/",
            module=module,
            src=_API_SRC,
            tests=_API_TESTS,
            context={"name": config.name, "module": module},
        )
    return []


def _render(
    engine: TemplateEngine,
    root: Path,
    *,
    base: str,
    module: str,
    src: Mapping[str, str],
    tests: Mapping[str, str],
    context: Mapping[str, object],
) -> list[Artifact]:
    package_dir = module.replace(".", "/")
    if not seedable(root / f"{base}src" / package_dir, src):
        return []
    files = {f"{base}src/{package_dir}/{n}": t for n, t in src.items()}
    files |= {f"{base}tests/{n}": t for n, t in tests.items()}
    return [
        Artifact(
            path, ArtifactKind.SEEDED, engine.render(f"starter/{template}", context)
        )
        for path, template in files.items()
    ]
