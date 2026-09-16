"""S4.3.1 — `uv init` + reconcile.

`uv` is invoked once, into an empty directory, and the reconcile leaves a
`pyproject.toml` that check 8a passes without kiln ever writing the file
kiln apply owns nothing of (kiln ADR-0001, ADR-0005).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.python.checks import pyproject
from rn_forge.kiln.modules.python.scaffold import scaffold

CONFIG = """
schema_version = 1

[repository]
name = "demo-tool"
archetype = "{archetype}"
"""

LIB_CONFIG = """
schema_version = 1

[repository]
name = "demo-lib"
archetype = "python-lib"

[archetype."python-lib"]
packages = ["packages/demo-alpha", "packages/demo-beta"]
"""


def _root(tmp_path: Path, archetype: str) -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    text = (
        LIB_CONFIG if archetype == "python-lib" else CONFIG.format(archetype=archetype)
    )
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
