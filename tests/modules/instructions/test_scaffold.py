"""S4.3.5 — the scaffolded bodies of `README.md`, `CLAUDE.md` and `AGENTS.md`."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.instructions.scaffold import scaffold

GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "golden"
ARCHETYPES = ("python-app", "python-tool", "python-lib")

CONFIG = 'schema_version = 1\n\n[repository]\nname = "demo"\narchetype = "python-app"\n'

README = """# demo

What this repository is, in a paragraph.

## Working here

- Run everything through `task`. `task validate` is the gate.
- Do not edit a file whose first line says it was generated. The kiln block in
  [CLAUDE.md](CLAUDE.md) says what that means and what to do instead.

## Conventions

- Python 3.14, `src/` layout, pyright strict, ruff for lint and format.
"""

BULLETS = (
    "- Run everything through `task`. `task validate` is the gate.\n",
    "- Do not edit a file whose first line says it was generated. The kiln block in\n"
    "  [CLAUDE.md](CLAUDE.md) says what that means and what to do instead.\n",
)


def _root(tmp_path: Path) -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    return tmp_path


def test_s4_3_5_scaffold_writes_the_three_bodies(tmp_path: Path) -> None:
    root = _root(tmp_path)
    scaffold(root, KilnConfig.load(root))
    assert (root / "README.md").read_text(encoding="utf-8") == README
    assert (root / "CLAUDE.md").read_text(encoding="utf-8").startswith("# demo\n")
    assert (root / "AGENTS.md").is_file()


def test_s4_3_5_scaffold_never_overwrites_a_present_body(tmp_path: Path) -> None:
    root = _root(tmp_path)
    for name in ("README.md", "CLAUDE.md", "AGENTS.md"):
        (root / name).write_text("mine\n", encoding="utf-8")
    scaffold(root, KilnConfig.load(root))
    for name in ("README.md", "CLAUDE.md", "AGENTS.md"):
        assert (root / name).read_text(encoding="utf-8") == "mine\n"


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_5_readme_bullets_appear_verbatim_in_every_golden(archetype: str) -> None:
    golden = (GOLDEN / archetype / "README.md").read_text(encoding="utf-8")
    for bullet in BULLETS:
        assert bullet in README
        assert bullet in golden


def test_s4_3_5_readme_is_mdformat_clean(tmp_path: Path) -> None:
    """Formatted under a golden's `.mdformat.toml`, which a rendered repo carries too."""
    root = _root(tmp_path)
    scaffold(root, KilnConfig.load(root))
    (root / ".mdformat.toml").write_bytes(
        (GOLDEN / "python-app" / ".mdformat.toml").read_bytes()
    )
    result = subprocess.run(
        [sys.executable, "-m", "mdformat", "--check", "README.md"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
