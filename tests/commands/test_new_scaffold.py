"""`kiln new`: what a fresh scaffold contains."""

from __future__ import annotations
import json
import pytest
import subprocess
from collections.abc import Callable
from pathlib import Path
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.artifacts import GITIGNORE_BLOCK
from rn_forge.kiln.modules.docs.checks import derived
from tests.conftest import new_repo
from typing import Any


@pytest.fixture(autouse=True)
def _in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`kiln new` stages beneath the current directory; keep that out of the repo."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


UV_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "scaffold" / "uv" / ".gitignore"
)


def test_fresh_scaffolds_have_identical_composed_gitignores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    texts = []
    for run in ("first", "second"):
        cwd = tmp_path / run
        cwd.mkdir()
        monkeypatch.chdir(cwd)
        target = cwd / "demo"
        new_repo(target, archetype="python-web-api", docs="none", yes=True)
        assert (target / ".git").is_dir()
        texts.append((target / ".gitignore").read_bytes())

    assert texts[0] == texts[1]
    text = texts[0].decode("utf-8")
    kiln = GITIGNORE_BLOCK.extract(text)
    assert kiln is not None
    assert text == GITIGNORE_BLOCK.render(
        "## uv ##\n" + UV_FIXTURE.read_text(encoding="utf-8"), kiln
    )


def test_new_seeds_the_workspace_file(tmp_path: Path) -> None:
    target = tmp_path / "demo"
    new_repo(target, archetype="python-tool", docs="none", yes=True)
    workspace = json.loads((target / "demo.code-workspace").read_text("utf-8"))
    assert workspace == {"folders": [{"path": "."}]}


def test_docs_none_omits_the_mkdocs_tree_and_site_tasks(
    tmp_path: Path,
) -> None:
    target = tmp_path / "demo"
    new_repo(target, archetype="python-tool", docs="none", yes=True)

    assert not (target / "docs").exists()
    assert not (target / "mkdocs.yml").exists()
    assert not (target / "tasks" / "docs.yml").exists()
    listed = subprocess.run(
        ["task", "--list-all", "--json"],
        cwd=target,
        capture_output=True,
        text=True,
        check=True,
    )
    names = [task["name"] for task in json.loads(listed.stdout)["tasks"]]
    assert "format" in names
    assert [name for name in names if name.startswith("docs:")] == []
    assert "mdformat" in (target / "tasks" / "quality.yml").read_text("utf-8")
    assert (target / "README.md").is_file()
    assert (target / "CLAUDE.md").is_file()
    assert (target / ".mdformat.toml").is_file()


def test_new_writes_a_current_derived_nav(
    rendered: Callable[[str], Path],
) -> None:
    target = rendered("python-tool")

    assert derived.check(KilnConfig.load(target), target) == []
    nav = (target / "mkdocs.yml").read_text(encoding="utf-8")
    assert "# BEGIN derived nav" in nav
    assert "guides/index.md" in nav
    state = (target / ".rn-forge" / "kiln" / "state.json").read_text("utf-8")
    assert '"mkdocs.yml"' in state


def test_new_writes_tabbed_navigation_features(
    rendered: Callable[[str], Path],
) -> None:
    target = rendered("python-tool")

    mkdocs = (target / "mkdocs.yml").read_text(encoding="utf-8")
    assert "navigation.tabs" in mkdocs
    assert "navigation.indexes" in mkdocs
    assert "navigation.sections" not in mkdocs
    assert "Overview:" not in mkdocs


def test_new_writes_a_current_epic_list(
    rendered: Callable[[str], Path],
) -> None:
    target = rendered("python-tool")

    page = target / "docs" / "specs" / "epics" / "index.md"
    assert "No epics yet." in page.read_text(encoding="utf-8")
    assert derived.check(KilnConfig.load(target), target) == []


def test_new_inside_a_uv_project_leaves_it_untouched(tmp_path: Path) -> None:
    parent = tmp_path / "pyproject.toml"
    parent.write_text('[project]\nname = "host"\nversion = "0.1.0"\n', encoding="utf-8")

    new_repo(tmp_path / "out" / "demo", archetype="python-tool", docs="none", yes=True)

    assert parent.read_text(encoding="utf-8") == (
        '[project]\nname = "host"\nversion = "0.1.0"\n'
    )
