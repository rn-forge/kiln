"""S4.3.1 — `uv init` + reconcile. S4.3.7 — the scaffold completes `pyproject.toml`.

`uv` is invoked once, into an empty directory, and the reconcile leaves a
`pyproject.toml` that check 8a passes without kiln ever writing the file
kiln apply owns nothing of (kiln ADR-0003, ADR-0005). S4.3.7 adds the
rn-forge dependency lines and the `docs` group so `rn-forge-deps` and
`task setup` pass on a fresh `kiln new` repo too.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.python.checks import pyproject, rn_forge_deps
from rn_forge.kiln.modules.python.scaffold import scaffold

CONFIG = """
schema_version = 1

[repository]
name = "demo-tool"
archetype = "{archetype}"

[docs]
profile = "{docs_profile}"
"""

LIB_CONFIG = """
schema_version = 1

[repository]
name = "demo-lib"
archetype = "python-lib"

[archetype."python-lib"]
packages = ["packages/demo-alpha", "packages/demo-beta"]

[docs]
profile = "{docs_profile}"
"""


def _root(tmp_path: Path, archetype: str, *, docs_profile: str = "mkdocs") -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    template = LIB_CONFIG if archetype == "python-lib" else CONFIG
    text = template.format(archetype=archetype, docs_profile=docs_profile)
    config.write_text(text, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("archetype", ["python-app", "python-tool"])
def test_s4_3_1_1_scaffold_then_reconcile_passes_check_8a(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "demo_tool" / "__init__.py").is_file()
    assert pyproject.check(config, root) == []


def test_s4_3_1_1_scaffold_a_workspace_passes_check_8a_at_root_and_members(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "python-lib")
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert (root / "pyproject.toml").is_file()
    assert (root / "packages" / "demo-alpha" / "pyproject.toml").is_file()
    assert (root / "packages" / "demo-beta" / "pyproject.toml").is_file()
    assert pyproject.check(config, root) == []


def test_s4_3_1_1_scaffold_never_leaves_a_git_tree_or_a_readme(tmp_path: Path) -> None:
    """Scaffolding shells out to `uv init` alone; it never templates its output (D16)."""
    root = _root(tmp_path, "python-app")
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert not (root / ".git").exists()
    assert not (root / "README.md").exists()


@pytest.mark.parametrize("archetype", ["python-app", "python-tool", "python-lib"])
def test_s4_3_7_rn_forge_deps_passes_after_scaffold(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert rn_forge_deps.check(config, root) == []


@pytest.mark.parametrize("archetype", ["python-app", "python-tool"])
def test_s4_3_7_root_dependencies_match_archetype_order(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    config = KilnConfig.load(root)
    scaffold(root, config)
    document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    required = archetypes.for_config(config).dependencies.required
    assert document["project"]["dependencies"] == [
        archetypes.requirement(name) for name in required
    ]


def test_s4_3_7_workspace_members_carry_dependencies_root_does_not(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "python-lib")
    config = KilnConfig.load(root)
    scaffold(root, config)
    required = archetypes.for_config(config).dependencies.required
    expected = [archetypes.requirement(name) for name in required]
    for package in ("demo-alpha", "demo-beta"):
        member = tomllib.loads(
            (root / "packages" / package / "pyproject.toml").read_text(encoding="utf-8")
        )
        assert member["project"]["dependencies"] == expected
    root_document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert root_document["project"]["dependencies"] == []


@pytest.mark.parametrize("docs_profile", ["none", "mkdocs"])
def test_s4_3_7_root_docs_group_reflects_profile(
    tmp_path: Path, docs_profile: str
) -> None:
    root = _root(tmp_path, "python-tool", docs_profile=docs_profile)
    config = KilnConfig.load(root)
    scaffold(root, config)
    document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    docs_group = document["dependency-groups"]["docs"]
    assert "mdformat>=1.0.0" in docs_group
    has_mkdocs_entry = any(entry.startswith("mkdocs-") for entry in docs_group)
    assert has_mkdocs_entry == (docs_profile == "mkdocs")


def test_s4_3_7_check_8a_still_passes(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-tool")
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert pyproject.check(config, root) == []
