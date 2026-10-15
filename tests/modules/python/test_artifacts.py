"""S4.3.1 — the `python` module's artifacts: `.importlinter`.

Also proves the five properties every F4.3 story owes its module
(`docs/specs/epics/E4-generator/F4.3-concern-modules.md`).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest
from rn_forge.commons.exceptions import AppException
from rn_forge.tooling.generation import Action, Artifact, ArtifactKind

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.python import PYTHON

ARCHETYPES = ("python-app", "python-tool", "python-lib")

CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "{archetype}"
"""

LIB_CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "python-lib"

[archetype."python-lib"]
packages = ["packages/alpha", "packages/beta"]
"""


def _importlinter(config: KilnConfig, root: Path) -> list[Artifact]:
    """The module's `.importlinter` alone; the seeded starter files are S4.9.1's."""
    return [a for a in PYTHON.artifacts(config, root) if a.path == ".importlinter"]


def _root(tmp_path: Path, archetype: str) -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    text = (
        LIB_CONFIG if archetype == "python-lib" else CONFIG.format(archetype=archetype)
    )
    config.write_text(text, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_1_property1_renders_exactly_the_module_s_template_inventory_row(
    tmp_path: Path, archetype: str
) -> None:
    """The template inventory lists only `.importlinter` for `python`."""
    config = KilnConfig.load(_root(tmp_path, archetype))
    artifacts = PYTHON.artifacts(config, tmp_path)
    assert [a.path for a in artifacts] == [".importlinter"]
    assert artifacts[0].kind is ArtifactKind.BLOCK


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_1_property2_into_an_empty_directory_only_creates(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    home = tmp_path / "home"
    actions = {
        change.key: change.action for change in cycle.plan(root, home=home).changes
    }
    assert set(actions.values()) <= {Action.CREATE, Action.INSERT, Action.SKIP}
    assert actions[".importlinter#rn-forge kiln"] is Action.INSERT


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_1_property3_a_second_apply_is_unchanged(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    home = tmp_path / "home"
    cycle.apply(root, home=home)
    actions = {
        change.key: change.action for change in cycle.plan(root, home=home).changes
    }
    assert set(actions.values()) <= {Action.UNCHANGED, Action.SKIP}


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_1_3_lint_imports_passes_on_the_rendered_importlinter(
    tmp_path: Path,
    archetype: str,
    monkeypatch: pytest.MonkeyPatch,
    rendered: Callable[[str], Path],
) -> None:
    """`lint-imports` passes on the rendered `.importlinter` in each archetype."""
    from importlinter import cli as importlinter_cli

    source = rendered(archetype)
    config = KilnConfig.load(source)
    [artifact] = _importlinter(config, source)
    assert artifact.block is not None
    (tmp_path / ".importlinter").write_text(
        artifact.block.render("", artifact.content), encoding="utf-8"
    )

    src_dirs = (
        [str(source / "src")]
        if archetype != "python-lib"
        else [
            str(source / "packages" / "lib-alpha" / "src"),
            str(source / "packages" / "lib-beta" / "src"),
        ]
    )
    monkeypatch.chdir(tmp_path)
    for src_dir in src_dirs:
        monkeypatch.syspath_prepend(src_dir)
    assert (
        importlinter_cli.lint_imports(config_filename=str(tmp_path / ".importlinter"))
        == importlinter_cli.EXIT_STATUS_SUCCESS
    )


WEB_CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "{archetype}"

[archetype."{archetype}"]
backend = "{backend}"
{extra}
"""


def _web_root(tmp_path: Path, archetype: str, backend: str, extra: str = "") -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        WEB_CONFIG.format(archetype=archetype, backend=backend, extra=extra),
        encoding="utf-8",
    )
    return tmp_path


def test_s5_1_2_python_web_api_root_package_is_the_api_member(tmp_path: Path) -> None:
    root = _web_root(tmp_path, "python-web-api", "fastapi")
    config = KilnConfig.load(root)
    [artifact] = PYTHON.artifacts(config, root)
    assert "root_package = demo_api" in artifact.content


def test_s5_1_2_python_web_api_fastapi_forbids_django_not_fastapi(
    tmp_path: Path,
) -> None:
    root = _web_root(tmp_path, "python-web-api", "fastapi")
    config = KilnConfig.load(root)
    [artifact] = PYTHON.artifacts(config, root)
    forbidden = artifact.content.split("forbidden_modules =")[1].split(
        "allow_indirect"
    )[0]
    assert "django" in forbidden
    assert "fastapi" not in forbidden
    assert "typer" in forbidden
    assert "jinja2" in forbidden
    assert "click" in forbidden


def test_s5_1_2_python_web_app_django_forbids_fastapi_not_django(
    tmp_path: Path,
) -> None:
    root = _web_root(tmp_path, "python-web-app", "django", extra='frontend = "angular"')
    config = KilnConfig.load(root)
    [artifact] = PYTHON.artifacts(config, root)
    forbidden = artifact.content.split("forbidden_modules =")[1].split(
        "allow_indirect"
    )[0]
    assert "fastapi" in forbidden
    assert "django" not in forbidden


def test_s5_1_3_backend_flag_only_changes_the_importlinter_forbidden_list(
    tmp_path: Path,
) -> None:
    """`backend` never changes topology — only .importlinter's forbidden list."""
    django_root = _web_root(
        tmp_path / "django", "python-web-app", "django", extra='frontend = "angular"'
    )
    fastapi_root = _web_root(
        tmp_path / "fastapi", "python-web-app", "fastapi", extra='frontend = "angular"'
    )
    [django_artifact] = PYTHON.artifacts(KilnConfig.load(django_root), django_root)
    [fastapi_artifact] = PYTHON.artifacts(KilnConfig.load(fastapi_root), fastapi_root)
    django_lines = django_artifact.content.splitlines()
    fastapi_lines = fastapi_artifact.content.splitlines()
    assert len(django_lines) == len(fastapi_lines)
    diffs = [(a, b) for a, b in zip(django_lines, fastapi_lines, strict=True) if a != b]
    assert diffs == [("    fastapi", "    django")]


MODULE_CONFIG = (
    LIB_CONFIG
    + """modules = { "packages/alpha" = "rn_forge.alpha" }
"""
)


def test_s6_1_3_1_module_defaults_from_the_path(tmp_path: Path) -> None:
    config = KilnConfig.load(_root(tmp_path, "python-lib"))
    assert config.module_for("packages/alpha") == "alpha"
    assert config.module_for("packages/rn-forge-cli") == "rn_forge_cli"


def test_s6_1_3_1_module_is_read_from_config(tmp_path: Path) -> None:
    (tmp_path / ".rn-forge" / "kiln").mkdir(parents=True)
    (tmp_path / ".rn-forge" / "kiln" / "config.toml").write_text(
        MODULE_CONFIG.replace("packages/alpha", "packages/rn-forge-cli", 2).replace(
            "rn_forge.alpha", "rn_forge.cli"
        ),
        encoding="utf-8",
    )
    config = KilnConfig.load(tmp_path)
    assert config.module_for("packages/rn-forge-cli") == "rn_forge.cli"
    assert config.module_for("packages/beta") == "beta"


def test_s6_1_3_1_a_modules_key_outside_packages_is_a_config_error(
    tmp_path: Path,
) -> None:
    (tmp_path / ".rn-forge" / "kiln").mkdir(parents=True)
    (tmp_path / ".rn-forge" / "kiln" / "config.toml").write_text(
        LIB_CONFIG + 'modules = { "packages/gamma" = "gamma" }\n', encoding="utf-8"
    )
    with pytest.raises(AppException, match="packages/gamma"):
        KilnConfig.load(tmp_path)


def test_s6_1_3_1_an_invalid_module_value_is_a_config_error(tmp_path: Path) -> None:
    (tmp_path / ".rn-forge" / "kiln").mkdir(parents=True)
    (tmp_path / ".rn-forge" / "kiln" / "config.toml").write_text(
        LIB_CONFIG + 'modules = { "packages/alpha" = "Rn-Forge" }\n', encoding="utf-8"
    )
    with pytest.raises(AppException):
        KilnConfig.load(tmp_path)


def test_s6_1_3_2_importlinter_names_the_declared_module(tmp_path: Path) -> None:
    (tmp_path / ".rn-forge" / "kiln").mkdir(parents=True)
    (tmp_path / ".rn-forge" / "kiln" / "config.toml").write_text(
        MODULE_CONFIG, encoding="utf-8"
    )
    [artifact] = _importlinter(KilnConfig.load(tmp_path), tmp_path)
    roots = [line.strip() for line in artifact.content.splitlines()]
    assert "rn_forge.alpha" in roots
    assert "beta" in roots
    assert "alpha" not in roots


OWN_CONFIG = LIB_CONFIG + 'import_contracts = "own"\n'


def _load(tmp_path: Path, text: str) -> KilnConfig:
    (tmp_path / ".rn-forge" / "kiln").mkdir(parents=True)
    (tmp_path / ".rn-forge" / "kiln" / "config.toml").write_text(text, encoding="utf-8")
    return KilnConfig.load(tmp_path)


def test_s6_1_4_1_default_keeps_kiln_contracts(tmp_path: Path) -> None:
    config = _load(tmp_path, LIB_CONFIG)
    assert config.import_contracts == "kiln"
    [artifact] = _importlinter(config, tmp_path)
    assert "[importlinter:contract:frameworks-come-from-rn-forge]" in artifact.content
    assert "[importlinter:contract:packages-are-independent]" in artifact.content
    assert "owns its import contracts" not in artifact.content


def test_s6_1_4_2_own_renders_only_the_root(tmp_path: Path) -> None:
    config = _load(tmp_path, OWN_CONFIG)
    assert config.import_contracts == "own"
    [artifact] = _importlinter(config, tmp_path)
    content = artifact.content
    assert "[importlinter]" in content
    assert "root_packages =" in content
    assert "include_external_packages = True" in content
    assert not [
        line
        for line in content.splitlines()
        if line.startswith("[importlinter:contract:")
    ]
    assert (
        "; This repository owns its import contracts: they are below the END marker."
        in content
    )


@pytest.mark.parametrize("archetype", ["python-app", "python-tool"])
def test_s6_1_4_3_own_is_python_lib_only(tmp_path: Path, archetype: str) -> None:
    with pytest.raises(AppException):
        _load(
            tmp_path,
            CONFIG.format(archetype=archetype)
            + f'\n[archetype."{archetype}"]\nimport_contracts = "own"\n',
        )


def test_s6_1_4_4_an_unknown_value_is_refused(tmp_path: Path) -> None:
    with pytest.raises(AppException):
        _load(tmp_path, LIB_CONFIG + 'import_contracts = "none"\n')
