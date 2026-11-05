"""S16.2.2 — files with a derived region: the digest, the adapter and the one classifier."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.hashing import ContentHash
from rn_forge.commons.generation import Action, Artifact, Change

from rn_forge.kiln.modules.base import ModuleRegistry
from rn_forge.kiln.modules.cicd import CICD
from rn_forge.kiln.modules.core import CORE
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.core.derived import DERIVED, NAV_BLOCK, managed_digest
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs import DocsModule, generate
from rn_forge.kiln.modules.docs.nav import build_nav
from rn_forge.kiln.modules.instructions import INSTRUCTIONS
from rn_forge.kiln.modules.node import NODE
from rn_forge.kiln.modules.python import PYTHON
from rn_forge.kiln.modules.registry import builtin
from rn_forge.kiln.modules.tasks import TASKS

CONFIG = (
    'schema_version = 1\n\n[repository]\nname = "demo"\narchetype = "python-tool"\n'
    '\n[docs]\nprofile = "mkdocs"\n'
)
BARE = 'schema_version = 1\n\n[repository]\nname = "demo"\narchetype = "python-tool"\n'


class _NoDocs(DocsModule):
    """The docs module, no longer rendering anything."""

    def artifacts(self, config: KilnConfig, root: Path) -> list[Artifact]:
        return []


BUILTIN = builtin()
WITHOUT_DOCS = ModuleRegistry(
    [CORE, PYTHON, NODE, _NoDocs(), TASKS, CICD, INSTRUCTIONS]
)
SRC = Path(__file__).resolve().parents[3] / "src"


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path / "home"


@pytest.fixture
def root(tmp_path: Path, home: Path) -> Path:
    """A repository after its first apply, with the docs module's registry."""
    repo = tmp_path / "repo"
    config = repo / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    cycle.apply(repo, home=home, registry=BUILTIN)
    generate.generate(repo)
    cycle.apply(repo, home=home, registry=BUILTIN)
    return repo


def _change(root: Path, home: Path, registry: ModuleRegistry) -> Change:
    planned = cycle.plan(root, home=home, registry=registry)
    return next(c for c in planned.changes if c.key == "mkdocs.yml")


def _docs(root: Path, home: Path) -> Change:
    return _change(root, home, BUILTIN)


def _read(root: Path) -> str:
    return (root / "mkdocs.yml").read_text(encoding="utf-8")


def _write(root: Path, text: str) -> None:
    (root / "mkdocs.yml").write_text(text, encoding="utf-8")


def test_s16_2_2_8_managed_digest() -> None:
    plain = "a: 1\n"
    assert managed_digest("pyproject.toml", plain) == ContentHash.of(plain)

    text = f"a: 1\nnav:\n{NAV_BLOCK.begin}\n    - X: x.md\n{NAV_BLOCK.end}\nb: 2\n"
    other_body = text.replace("X: x.md", "Y: y.md")
    assert "mkdocs.yml" in DERIVED
    assert managed_digest("mkdocs.yml", text) == managed_digest(
        "mkdocs.yml", other_body
    )
    assert managed_digest("mkdocs.yml", text) != ContentHash.of(text)
    assert managed_digest("mkdocs.yml", text) != managed_digest(
        "mkdocs.yml", text.replace("b: 2", "b: 3")
    )
    assert managed_digest("mkdocs.yml", plain) == ContentHash.of(plain)

    with pytest.raises(AppException):
        managed_digest("mkdocs.yml", f"nav:\n{NAV_BLOCK.begin}\n")


def test_s16_2_2_9_apply_classifies_derived(root: Path, home: Path) -> None:
    rendered = _read(root)
    assert _docs(root, home).action is Action.UNCHANGED

    nav = NAV_BLOCK.extract(rendered) or ""
    assert nav.strip()
    dropped = "".join(nav.splitlines(keepends=True)[:-2])
    _write(root, NAV_BLOCK.render(rendered, dropped))
    assert _docs(root, home).action is Action.UPDATE
    cycle.apply(root, home=home, registry=BUILTIN)
    assert _read(root) == rendered

    _write(root, rendered.replace("strict: true", "strict: false"))
    change = _docs(root, home)
    assert change.action is Action.DRIFT
    assert change.is_blocking

    _write(root, rendered.replace(NAV_BLOCK.begin + "\n", ""))
    assert _docs(root, home).action is Action.DRIFT


def test_s16_2_2_10_stale_derived_entry(root: Path, home: Path) -> None:
    rendered = _read(root)
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(BARE, encoding="utf-8")
    bare = WITHOUT_DOCS

    nav = NAV_BLOCK.extract(rendered) or ""
    _write(root, NAV_BLOCK.render(rendered, nav + "    - Z: z.md\n"))
    change = _change(root, home, bare)
    assert change.action is Action.DELETE
    cycle.apply(root, home=home, registry=bare)
    assert not (root / "mkdocs.yml").exists()

    config.write_text(CONFIG, encoding="utf-8")
    cycle.apply(root, home=home, registry=BUILTIN)
    config.write_text(BARE, encoding="utf-8")
    _write(root, rendered.replace("strict: true", "strict: false"))
    change = _change(root, home, bare)
    assert (change.action, change.intent) == (Action.DRIFT, Action.DELETE)


def test_s16_2_2_11_first_managed_apply(tmp_path: Path, home: Path) -> None:
    repo = tmp_path / "repo"
    config = repo / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    registry = BUILTIN
    (repo / "mkdocs.yml").write_text("site_name: mine\n", encoding="utf-8")

    assert _change(repo, home, registry).action is Action.CONFLICT
    cycle.apply(repo, home=home, registry=registry, force=["mkdocs.yml"])
    generate.generate(repo)
    assert "Generated by kiln" in _read(repo)

    state = (repo / ".rn-forge" / "kiln" / "state.json").read_bytes()
    before = _read(repo)
    cycle.apply(repo, home=home, registry=registry)
    assert (repo / ".rn-forge" / "kiln" / "state.json").read_bytes() == state
    assert _read(repo) == before


def _calls(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "plan"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "generation"
        ):
            found.append((path.name, node.lineno))
    return found


def test_s16_2_2_12_one_classifier() -> None:
    cycle_py = SRC / "rn_forge" / "kiln" / "modules" / "core" / "cycle.py"
    callers = {
        path: calls
        for path in sorted((SRC / "rn_forge" / "kiln").rglob("*.py"))
        if (calls := _calls(path))
    }
    assert list(callers) == [cycle_py]

    tree = ast.parse(cycle_py.read_text(encoding="utf-8"))
    (classify,) = (
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "classify"
    )
    inside = {getattr(n, "lineno", 0) for n in ast.walk(classify)}
    assert {line for _, line in callers[cycle_py]} <= inside

    commands = (SRC / "rn_forge" / "kiln" / "commands.py").read_text(encoding="utf-8")
    rows = re.search(r"def _config_change_rows.*?\n\n\ndef ", commands, re.DOTALL)
    assert rows is not None
    assert "cycle.classify(" in rows.group(0)
    assert build_nav  # the nav the settle compares against comes from the tree
