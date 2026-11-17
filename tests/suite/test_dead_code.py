"""S18.7.4 — dead code and unused exports are gone."""

from __future__ import annotations

from pathlib import Path

from rn_forge.kiln import devops
from rn_forge.kiln.modules import registry
from rn_forge.kiln.modules.docs import work
from rn_forge.kiln.modules.node import scaffold as node_scaffold
from rn_forge.kiln.modules.python import scaffold as python_scaffold


def test_s18_7_4_1_the_deleted_names_are_gone() -> None:
    assert not hasattr(python_scaffold, "scaffold")
    assert not hasattr(devops, "Package")
    assert not hasattr(work, "read_metadata")
    assert not hasattr(node_scaffold, "_SCAFFOLDERS")


def test_s18_7_4_2_builtin_is_cached() -> None:
    assert registry.builtin() is registry.builtin()


def test_s18_8_1_1_no_module_declares_checks() -> None:
    modules = Path(registry.__file__).parent
    offenders = [
        str(path)
        for path in modules.rglob("*.py")
        if "def checks(self" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
