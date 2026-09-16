"""S4.2.1 — the archetype manifests."""

from __future__ import annotations

import pytest

from rn_forge.commons.exceptions import AppException

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.registry import builtin

PYTHON_ARCHETYPES = ["python-app", "python-lib", "python-tool"]


def test_s4_2_1_every_python_archetype_is_shipped() -> None:
    assert list(archetypes.shipped()) == PYTHON_ARCHETYPES


@pytest.mark.parametrize("name", PYTHON_ARCHETYPES)
def test_s4_2_1_every_python_archetype_manifest_loads(name: str) -> None:
    archetype = archetypes.load(name)
    assert archetype.name == name
    assert archetype.modules == [
        "core",
        "python",
        "docs",
        "tasks",
        "cicd",
        "instructions",
    ]
    assert "rn-forge-commons" in archetype.dependencies.required
    assert set(archetype.dependencies.required) <= set(archetype.dependencies.allowed)
    assert "kiln" in archetype.forbidden_tools
    assert "quality:lint:generated" in archetype.required_validate
    assert len(builtin().for_archetype(archetype)) == len(archetype.modules)


def test_s4_2_1_a_manifest_naming_an_unregistered_module_is_refused_by_name() -> None:
    archetype = archetypes.load("python-app").model_copy(
        update={"modules": ["core", "conjured"]}
    )
    with pytest.raises(AppException, match="conjured"):
        builtin().for_archetype(archetype)


def test_an_unknown_archetype_is_refused_naming_what_ships() -> None:
    with pytest.raises(AppException, match="Unknown archetype 'python-hovercraft'"):
        archetypes.load("python-hovercraft")


def test_lifecycle_and_mkdocs_adjust_the_manifest(repo) -> None:
    archetype = archetypes.for_config(
        KilnConfig.load(repo(archetype="python-app", lifecycle=True, docs="mkdocs"))
    )
    assert "rn-forge-tooling" in archetype.dependencies.required
    assert "docs:build" in archetype.required_validate
