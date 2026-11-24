"""The seeded starter source `python` writes once, at `kiln new`."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path

from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.commons.generation.templated import TemplateArtifact, render_artifacts
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.kiln.config import KilnConfig

__all__ = ["render", "seedable", "starter_flags"]

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
    "http/__init__.py": "fastapi/http_init.py.j2",
    "http/items.py": "fastapi/items.py.j2",
    "domain/__init__.py": "fastapi/domain_init.py.j2",
    "domain/errors.py": "fastapi/errors.py.j2",
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
    engine = TemplateEngine.cached(package="rn_forge.kiln.modules.python")
    if config.archetype in {"python-tool", "python-app"}:
        tool = config.lifecycle
        package = config.module
        return _render(
            engine,
            root,
            base="",
            module=package,
            src=_TOOL_SRC if tool else _APP_SRC,
            tests=_TOOL_TESTS if tool else _APP_TESTS,
            context={"name": config.name, "package": package},
        )
    if config.is_workspace:
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
    if config.is_web:
        if config.backend != "fastapi":
            return []
        module = config.api_module
        assert module is not None  # `is_web` implies an API member
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
    return render_artifacts(
        engine,
        context,
        [
            TemplateArtifact(path, ArtifactKind.SEEDED, template=f"starter/{template}")
            for path, template in files.items()
        ],
    )


def starter_flags(archetype: str, name: str, package: str) -> dict[str, object]:
    """The `cli` and `lifecycle` config a new *archetype* repository starts with."""
    flags: dict[str, object] = {}
    if archetype in {"python-tool", "python-app"}:
        flags["cli"] = {
            "name": name,
            "help": f"The {name} command line.",
            "commands": [{"name": "hello", "target": f"{package}.commands:hello"}],
        }
    if archetype == "python-tool":
        flags["lifecycle"] = {"product": f"{package}.product:PRODUCT"}
    return flags
