"""S4.5.8 — `kiln init`: bring an existing standard repository under kiln.

Built over a copy of the session-rendered `python-app` repo (`rendered` in
`tests/conftest.py`), with `.rn-forge/` and every kiln block removed and a
`.git` entry added: a standard repository kiln has never seen, whose managed
files already equal their renders. No test runs a scaffold; every scaffold
function `commands` imports is replaced by one that records and fails.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import tomlkit

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.commons.generation import ArtifactKind, StateEntry
from rn_forge.commons.generation.artifacts import block_from_entry

from rn_forge.kiln import commands, main
from rn_forge.commons.generation import Action

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.core.config.manager import ConfigManager
from rn_forge.kiln.modules.core.artifacts import GITIGNORE_BLOCK
from rn_forge.kiln.modules.docs.nav import NAV_BLOCK
from rn_forge.kiln.modules.python.artifacts import IMPORTLINTER_BLOCK

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(".rn-forge/kiln/state.json")
CONFIG = Path(".rn-forge/kiln/config.toml")
TAPLO = Path(sys.executable).parent / "taplo"
SELECTORS: dict[str, Any] = {"archetype": "python-app", "docs": "mkdocs"}

_IGNORE = shutil.ignore_patterns(
    ".venv",
    ".uv-cache",
    ".ruff_cache",
    ".import_linter_cache",
    ".pytest_cache",
    ".docs-site",
    ".git",
    "__pycache__",
)
_SCAFFOLDS = (
    "scaffold_backend",
    "scaffold_node",
    "reconcile_backend",
    "reconcile_node",
    "instructions_scaffold",
    "python_add_package",
    "docs_add_package",
)


def _entries(root: Path) -> dict[str, dict[str, Any]]:
    return json.loads((root / STATE).read_text(encoding="utf-8"))["entries"]


def _blocks(root: Path) -> list[StateEntry]:
    return [
        StateEntry.from_dict(entry)
        for entry in _entries(root).values()
        if entry["kind"] == "block"
    ]


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        file.relative_to(root).as_posix(): file.read_bytes()
        for file in sorted(root.rglob("*"))
        if file.is_file() and ".git" not in file.parts
    }


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


_REAL_RUN_TASK = commands._run_task


@pytest.fixture(autouse=True)
def task_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, str]]:
    """Replace `commands._run_task` with a recorder, so no test runs `task` unless it restores `_REAL_RUN_TASK`."""
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        commands, "_run_task", lambda root, name: calls.append((root, name))
    )
    return calls


@pytest.fixture
def scaffold_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every scaffold function `commands` holds fails if called, and is recorded."""
    calls: list[str] = []

    def forbidden(name: str) -> Callable[..., None]:
        def fail(*_: object, **__: object) -> None:
            calls.append(name)
            raise AssertionError(f"init called {name}")

        return fail

    for name in _SCAFFOLDS:
        monkeypatch.setattr(commands, name, forbidden(name))
    return calls


@pytest.fixture
def fresh(rendered: Callable[[str], Path]) -> Path:
    """The `new` repo the standard says init must reproduce."""
    return rendered("python-app")


@pytest.fixture
def repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fresh: Path,
    scaffold_calls: list[str],
) -> Path:
    """A standard repository with no kiln state, no kiln blocks, files already equal."""
    root = _unadopted(fresh, tmp_path)
    monkeypatch.chdir(root)
    return root


def _unadopted(fresh: Path, tmp_path: Path) -> Path:
    """A copy of *fresh* with its kiln state and kiln blocks removed."""
    root = tmp_path / fresh.name
    shutil.copytree(fresh, root, ignore=_IGNORE)
    for block in _blocks(root):
        path = root / block.path
        path.write_text(
            block_from_entry(block).remove(path.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
    shutil.rmtree(root / ".rn-forge")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    return root


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _commit(root: Path) -> None:
    """Commit every change in *root*, leaving the tree clean."""
    _git(root, "add", "-A")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "edit")


def _tamper_block(root: Path, fresh: Path, path: str) -> None:
    """Put a kiln block with the wrong body into *path*."""
    entry = next(block for block in _blocks(fresh) if block.path == path)
    file = root / path
    file.write_text(
        block_from_entry(entry).render(file.read_text(encoding="utf-8"), "tampered"),
        encoding="utf-8",
    )


def test_s4_5_8_1_equal_files_are_baselined_without_rewriting(
    repo: Path, fresh: Path
) -> None:
    whole = [
        repo / entry["path"]
        for entry in _entries(fresh).values()
        if entry["kind"] == "managed" and (repo / entry["path"]).is_file()
    ]
    assert whole
    for file in whole:
        os.utime(file, ns=(1_000_000_000, 1_000_000_000))

    commands.init(**SELECTORS, yes=True)

    assert (repo / CONFIG).is_file()
    assert (repo / STATE).is_file()
    assert {file: file.stat().st_mtime_ns for file in whole} == {
        file: 1_000_000_000 for file in whole
    }
    assert _entries(repo) == _entries(fresh)


def test_s4_5_8_2_outside_a_git_worktree_fails_and_leaves_no_umbrella(
    repo: Path,
) -> None:
    shutil.rmtree(repo / ".git")
    with pytest.raises(AppException, match="Git worktree"):
        commands.init(**SELECTORS, yes=True)
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_2_kilns_own_checkout_fails_and_leaves_no_umbrella(repo: Path) -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    name = pyproject["project"]["name"]
    (repo / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "0"\n', encoding="utf-8"
    )
    with pytest.raises(AppException, match="own source checkout"):
        commands.init(**SELECTORS, yes=True)
    assert not (repo / ".rn-forge").exists()


@pytest.mark.parametrize(
    "missing",
    ["pyproject.toml"],
)
def test_s4_5_8_2_a_missing_preflight_path_fails_and_leaves_no_umbrella(
    repo: Path, missing: str
) -> None:
    target = repo / missing
    shutil.rmtree(target) if target.is_dir() else target.unlink()
    with pytest.raises(AppException, match=f"missing {missing}"):
        commands.init(**SELECTORS, yes=True)
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_2_every_failed_condition_is_named_in_one_error(repo: Path) -> None:
    shutil.rmtree(repo / ".git")
    (repo / "pyproject.toml").unlink()
    with pytest.raises(AppException) as raised:
        commands.init(**SELECTORS)
    message = str(raised.value)
    assert "Git worktree" in message
    assert "pyproject.toml" in message
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_2_archetype_is_required(repo: Path) -> None:
    with pytest.raises(AppException, match="--archetype"):
        commands.init(yes=True)
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_3_conflicts_are_overwritten_and_archived(
    repo: Path, fresh: Path
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    _tamper_block(repo, fresh, "CLAUDE.md")
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    assert (repo / "Taskfile.yml").read_bytes() == (fresh / "Taskfile.yml").read_bytes()
    assert "tampered" not in (repo / "CLAUDE.md").read_text(encoding="utf-8")
    backups = repo / ".rn-forge/kiln/backups"
    assert list(backups.glob("*/Taskfile.yml"))
    assert list(backups.glob("*/CLAUDE.md"))


def test_s4_5_8_3_a_block_without_a_state_entry_is_archived_even_if_equal(
    repo: Path, fresh: Path
) -> None:
    (repo / "CLAUDE.md").write_bytes((fresh / "CLAUDE.md").read_bytes())
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    assert list((repo / ".rn-forge/kiln/backups").glob("*/CLAUDE.md"))
    assert (repo / "CLAUDE.md").read_bytes() == (fresh / "CLAUDE.md").read_bytes()


def test_s4_5_8_3_an_existing_config_without_state_is_archived_and_replaced(
    repo: Path, fresh: Path
) -> None:
    (repo / CONFIG).parent.mkdir(parents=True)
    (repo / CONFIG).write_text("# mine\n", encoding="utf-8")
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    archives = list(
        (repo / ".rn-forge/kiln/backups").glob("*/.rn-forge/kiln/config.toml")
    )
    assert [a.read_text(encoding="utf-8") for a in archives] == ["# mine\n"]
    assert (repo / CONFIG).read_text(encoding="utf-8") != "# mine\n"
    assert (repo / STATE).is_file()


def test_s4_5_8_5_a_second_init_is_refused_naming_apply(repo: Path) -> None:
    commands.init(**SELECTORS, yes=True)
    _commit(repo)
    before = _snapshot(repo)

    with pytest.raises(AppException, match="state.json.*kiln apply"):
        commands.init(**SELECTORS, yes=True)
    assert _snapshot(repo) == before


def test_s4_5_8_6_init_runs_no_scaffold(repo: Path, scaffold_calls: list[str]) -> None:
    commands.init(**SELECTORS, yes=True)
    assert scaffold_calls == []


def test_s4_5_8_preview_prints_the_plan_and_writes_nothing(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _snapshot(repo)
    commands.init(**SELECTORS, json=True)
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["root"] == str(repo.resolve())
    assert payload["config"]["repository"]["name"] == repo.name
    assert payload["artifacts"]
    assert _snapshot(repo) == before
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_without_yes_and_with_dry_run_nothing_is_written(repo: Path) -> None:
    before = _snapshot(repo)
    commands.init(**SELECTORS)
    commands.init(**SELECTORS, yes=True, dry_run=True)
    assert _snapshot(repo) == before


def test_s4_5_8_a_failing_check_keeps_the_writes(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        commands.checks,
        "run",
        lambda *_a, **_k: [Finding("x.y", Severity.ERROR, "broken")],
    )
    with pytest.raises(AppException, match="check"):
        commands.init(**SELECTORS, yes=True)
    assert (repo / STATE).is_file()
    assert (repo / CONFIG).is_file()


@pytest.fixture
def lib_fresh(rendered: Callable[[str], Path]) -> Path:
    """The `new` python-lib repository with two packages; rendered before the scaffolds are fenced."""
    return rendered("python-lib")


@pytest.fixture
def lib_repo(
    lib_fresh: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scaffold_calls: list[str],
) -> Path:
    """`lib_fresh`, not yet under kiln."""
    root = _unadopted(lib_fresh, tmp_path)
    monkeypatch.chdir(root)
    return root


def _packages_config(tmp_path: Path, *packages: str) -> str:
    listed = ", ".join(f'"{package}"' for package in packages)
    path = tmp_path / "adopt.toml"
    path.write_text(
        f'[archetype."python-lib"]\npackages = [{listed}]\n', encoding="utf-8"
    )
    return str(path)


def test_s6_1_5_1_init_adopts_a_library_workspace_with_its_packages(
    lib_repo: Path, lib_fresh: Path, tmp_path: Path
) -> None:
    packages = ["packages/lib-alpha", "packages/lib-beta"]
    config = _packages_config(tmp_path, *packages)

    commands.init(archetype="python-lib", config=config, yes=True)

    written = tomllib.loads((lib_repo / CONFIG).read_text(encoding="utf-8"))
    assert written["archetype"]["python-lib"]["packages"] == packages
    assert _entries(lib_repo) == _entries(lib_fresh)


def test_s6_9_1_1_init_writes_no_starter_into_a_package_with_subpackages(
    lib_repo: Path, tmp_path: Path
) -> None:
    packages = ["packages/lib-alpha", "packages/lib-beta"]
    alpha = lib_repo / packages[0]
    beta_starters = [
        lib_repo / packages[1] / "src" / "lib_beta" / "settings.py",
        lib_repo / packages[1] / "tests" / "test_settings.py",
    ]
    assert all(file.is_file() for file in beta_starters)
    before = [file.read_bytes() for file in beta_starters]
    (alpha / "src" / "lib_alpha" / "settings.py").unlink()
    (alpha / "tests" / "test_settings.py").unlink()
    (alpha / "src" / "lib_alpha" / "sub").mkdir()
    (alpha / "src" / "lib_alpha" / "sub" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    _commit(lib_repo)

    commands.init(
        archetype="python-lib", config=_packages_config(tmp_path, *packages), yes=True
    )

    assert not (alpha / "src" / "lib_alpha" / "settings.py").exists()
    assert not (alpha / "tests" / "test_settings.py").exists()
    assert [file.read_bytes() for file in beta_starters] == before


def test_s6_6_1_1_written_config_is_taplo_clean(
    lib_fresh: Path, tmp_path: Path
) -> None:
    source = tmp_path / "src"
    (source / CONFIG).parent.mkdir(parents=True)
    document = tomlkit.parse((lib_fresh / CONFIG).read_text(encoding="utf-8"))
    document["archetype"]["python-lib"]["packages"] = [  # type: ignore[index]
        f"packages/rn-forge-package-{n}" for n in range(1, 10)
    ]
    (source / CONFIG).write_text(tomlkit.dumps(document), encoding="utf-8")
    config = KilnConfig.load(source)
    out = tmp_path / "out"
    out.mkdir()

    commands._write_config(out, config)  # noqa: SLF001
    shutil.copy(lib_fresh / ".taplo.toml", out / ".taplo.toml")
    result = subprocess.run(
        [str(TAPLO), "fmt", "--check", "--diff", str(CONFIG)],
        cwd=out,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_s6_6_1_2_init_writes_packages_one_per_line(
    lib_repo: Path, tmp_path: Path
) -> None:
    config = _packages_config(tmp_path, "packages/lib-alpha", "packages/lib-beta")

    commands.init(archetype="python-lib", config=config, yes=True)

    text = (lib_repo / CONFIG).read_text(encoding="utf-8")
    assert (
        'packages = [\n    "packages/lib-alpha",\n    "packages/lib-beta",\n]' in text
    )


def test_s6_6_2_5_init_adds_missing_tools(lib_repo: Path, tmp_path: Path) -> None:
    pyproject = lib_repo / "pyproject.toml"
    document = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
    dev = document["dependency-groups"]["dev"]  # type: ignore[index]
    dev.remove(next(e for e in dev if str(e).startswith("taplo")))
    pyproject.write_text(tomlkit.dumps(document), encoding="utf-8")
    _commit(lib_repo)
    config = _packages_config(tmp_path, "packages/lib-alpha", "packages/lib-beta")

    commands.init(archetype="python-lib", config=config, yes=True)

    groups = tomllib.loads(pyproject.read_text(encoding="utf-8"))["dependency-groups"]
    assert "taplo" in groups["dev"]
    assert not [e for g in groups.values() for e in g if "rn-forge-kiln" in str(e)]


def test_s6_6_2_6_nothing_added_when_every_tool_is_present(
    lib_repo: Path, tmp_path: Path
) -> None:
    before = (lib_repo / "pyproject.toml").read_bytes()
    config = _packages_config(tmp_path, "packages/lib-alpha", "packages/lib-beta")

    commands.init(archetype="python-lib", config=config, yes=True)

    assert (lib_repo / "pyproject.toml").read_bytes() == before


@pytest.mark.parametrize("without_pyproject", [False, True])
def test_s6_1_5_2_a_listed_package_must_exist(
    lib_repo: Path, tmp_path: Path, without_pyproject: bool
) -> None:
    if without_pyproject:
        (lib_repo / "packages/missing").mkdir()
    config = _packages_config(tmp_path, "packages/lib-alpha", "packages/missing")

    with pytest.raises(AppException, match="init.package-missing.*packages/missing"):
        commands.init(archetype="python-lib", config=config, yes=True)
    assert not (lib_repo / ".rn-forge").exists()


def test_s6_1_5_3_init_renders_a_missing_taskfile_and_tasks(
    repo: Path, fresh: Path
) -> None:
    (repo / "Taskfile.yml").unlink()
    shutil.rmtree(repo / "tasks")
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    assert (repo / "Taskfile.yml").read_bytes() == (fresh / "Taskfile.yml").read_bytes()
    assert sorted(path.name for path in (repo / "tasks").iterdir()) == sorted(
        path.name for path in (fresh / "tasks").iterdir()
    )


def test_s6_1_6_1_init_creates_every_missing_path(repo: Path, fresh: Path) -> None:
    removed = [
        "README.md",
        "CLAUDE.md",
        "AGENTS.md",
        ".gitignore",
        "docs",
        ".github",
        "mkdocs.yml",
    ]
    for name in removed:
        target = repo / name
        shutil.rmtree(target) if target.is_dir() else target.unlink()
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    assert _entries(repo) == _entries(fresh)
    # README.md and AGENTS.md are repo-owned bodies only a scaffold writes.
    for name in ("CLAUDE.md", ".gitignore", "docs", ".github"):
        assert (repo / name).exists()


@pytest.mark.parametrize("tracked", [False, True])
def test_s6_1_6_2_a_dirty_tree_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str], tracked: bool
) -> None:
    path = "README.md" if tracked else "scratch.txt"
    with (repo / path).open("a", encoding="utf-8") as handle:
        handle.write("edit\n")

    with pytest.raises(AppException, match=f"init.dirty-tree.*{path}"):
        commands.init(**SELECTORS, yes=True)
    assert not (repo / ".rn-forge").exists()

    commands.init(**SELECTORS)
    assert capsys.readouterr().out.strip()
    assert not (repo / ".rn-forge").exists()


_MINE = (
    "; mine\n[importlinter]\nroot_packages =\n    other\n\n"
    "[importlinter:contract:mine]\nname = mine\ntype = forbidden\n"
    "source_modules =\n    a\nforbidden_modules =\n    b\n"
)


def test_s6_1_7_1_an_unfenced_importlinter_is_fenced_and_keeps_the_contracts(
    repo: Path,
) -> None:
    (repo / ".importlinter").write_text(_MINE, encoding="utf-8")
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    block = IMPORTLINTER_BLOCK
    text = (repo / ".importlinter").read_text(encoding="utf-8")
    assert block.extract(text) is not None
    after = text.split(block.end, 1)[1]
    assert "; mine" in after
    assert _MINE.split("\n\n", 1)[1] in after
    assert "[importlinter]" not in after.splitlines()
    assert "other" not in after
    archives = (repo / ".rn-forge/kiln/backups").glob("*/.importlinter")
    assert [a.read_bytes() for a in archives if a.read_bytes() == _MINE.encode()]


_DUPLICATES = "# mine\n.DS_Store\n.ruff_cache\nnode_stuff/\n.pytest_cache\n"


def test_s6_1_8_1_duplicates_outside_the_block_are_removed(
    repo: Path, fresh: Path
) -> None:
    (repo / ".gitignore").write_text(_DUPLICATES, encoding="utf-8")
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    block = GITIGNORE_BLOCK
    text = (repo / ".gitignore").read_text(encoding="utf-8")
    assert text.split(block.begin, 1)[0] == "# mine\nnode_stuff/\n\n"
    assert block.extract(text) == block.extract(
        (fresh / ".gitignore").read_text(encoding="utf-8")
    )


def test_s6_1_8_2_a_negation_leaves_the_file_alone(repo: Path) -> None:
    original = _DUPLICATES + "!keep.log\n"
    (repo / ".gitignore").write_text(original, encoding="utf-8")
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    text = (repo / ".gitignore").read_text(encoding="utf-8")
    assert text.split(GITIGNORE_BLOCK.begin, 1)[0].rstrip("\n") == original.rstrip("\n")


def _renamed_repo(fresh: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An unadopted copy of *fresh* in a directory called `other-dir`, as the cwd."""
    root = _unadopted(fresh, tmp_path / "unadopted").rename(tmp_path / "other-dir")
    monkeypatch.chdir(root)
    return root


def _fresh_name(fresh: Path) -> str:
    written = tomllib.loads((fresh / CONFIG).read_text(encoding="utf-8"))
    return written["repository"]["name"]


def test_s6_1_16_1_init_takes_the_name_from_config(
    fresh: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scaffold_calls: list[str],
) -> None:
    root = _renamed_repo(fresh, tmp_path, monkeypatch)
    name = _fresh_name(fresh)
    layer = tmp_path / "layer.toml"
    layer.write_text(f'[repository]\nname = "{name}"\n', encoding="utf-8")

    commands.init(**SELECTORS, config=str(layer), yes=True)

    written = tomllib.loads((root / CONFIG).read_text(encoding="utf-8"))
    assert written["repository"]["name"] == name
    for file in root.rglob("*"):
        if file.is_file() and ".git" not in file.parts:
            assert b"other-dir" not in file.read_bytes(), file


def test_s6_1_16_2_without_a_config_name_the_directory_names_it(
    fresh: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scaffold_calls: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _renamed_repo(fresh, tmp_path, monkeypatch)
    layer = tmp_path / "layer.toml"
    layer.write_text("# no repository name\n", encoding="utf-8")

    commands.init(**SELECTORS, config=str(layer), json=True)

    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["config"]["repository"]["name"] == "other-dir"


def _before_block(repo: Path) -> str:
    text = (repo / ".gitignore").read_text(encoding="utf-8")
    return text.split(GITIGNORE_BLOCK.begin, 1)[0]


def test_s6_1_19_1_a_group_left_with_only_comments_goes(repo: Path) -> None:
    original = "# system files\n.DS_Store\n\n# mine\nnode_stuff/\n.pytest_cache\n"
    (repo / ".gitignore").write_text(original, encoding="utf-8")
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    assert _before_block(repo) == "# mine\nnode_stuff/\n\n"


def test_s6_1_19_2_a_comment_only_group_is_kept(repo: Path) -> None:
    original = "# header\n\n# mine\n.DS_Store\nnode_stuff/\n"
    (repo / ".gitignore").write_text(original, encoding="utf-8")
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    assert _before_block(repo) == "# header\n\n# mine\nnode_stuff/\n\n"


def _unmark_nav(repo: Path) -> bytes:
    path = repo / "mkdocs.yml"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    markers = (NAV_BLOCK.begin.strip(), NAV_BLOCK.end.strip())
    text = "".join(line for line in lines if line.strip() not in markers)
    path.write_text(text, encoding="utf-8")
    _commit(repo)
    return text.encode()


def test_s6_1_9_2_an_unmarked_nav_is_archived_marked_and_derived(
    repo: Path, fresh: Path
) -> None:
    unmarked = _unmark_nav(repo)

    commands.init(**SELECTORS, yes=True)

    assert (repo / "mkdocs.yml").read_bytes() == (fresh / "mkdocs.yml").read_bytes()
    archives = (repo / ".rn-forge/kiln/backups").glob("*/mkdocs.yml")
    assert [a for a in archives if a.read_bytes() == unmarked]


def test_s6_1_9_3_a_nav_is_added_when_there_is_none(repo: Path, fresh: Path) -> None:
    text = (repo / "mkdocs.yml").read_text(encoding="utf-8")
    head = text.split("\nnav:\n", 1)[0]
    tail = text.split(NAV_BLOCK.end, 1)[1]
    (repo / "mkdocs.yml").write_text(head + "\n" + tail.lstrip("\n"), encoding="utf-8")
    assert "nav:" not in (repo / "mkdocs.yml").read_text(encoding="utf-8")
    _commit(repo)

    commands.init(**SELECTORS, yes=True)

    def nav(root: Path) -> str | None:
        return NAV_BLOCK.extract((root / "mkdocs.yml").read_text(encoding="utf-8"))

    assert nav(repo) is not None
    assert list((repo / ".rn-forge/kiln/backups").glob("*/mkdocs.yml"))


# S9.1.15 — `kiln init` gives an existing `node-lib` what `kiln new` does.

NODE_SELECTORS: dict[str, Any] = {"archetype": "node-lib", "docs": "mkdocs"}
_DOCS_GROUP_SIZE = 6  # node-lib under mkdocs: four mdformat entries + two mkdocs


@pytest.fixture
def node_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A node repository named like the `new` one: `.git`, `package.json`, `nx.json`, no Python files."""
    root = tmp_path / "node-lib"
    root.mkdir()
    (root / "package.json").write_text('{"name": "node-lib"}\n', encoding="utf-8")
    (root / "nx.json").write_text("{}\n", encoding="utf-8")
    _git(root, "init", "-q")
    _commit(root)
    monkeypatch.chdir(root)
    return root


def _plan(capsys: pytest.CaptureFixture[str]) -> dict[str, dict[str, str]]:
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    return {row["path"]: row for row in payload["artifacts"]}


def test_s9_1_15_1_a_node_lib_gets_the_pyproject_new_writes(
    node_repo: Path, rendered: Callable[[str], Path]
) -> None:
    commands.init(**NODE_SELECTORS, yes=True)

    written = tomllib.loads((node_repo / "pyproject.toml").read_text(encoding="utf-8"))
    assert written["project"]["name"] == "node-lib"
    assert "build-system" not in written
    assert set(written["dependency-groups"]) == {"dev", "docs"}
    fresh = rendered("node-lib") / "pyproject.toml"
    assert (node_repo / "pyproject.toml").read_bytes() == fresh.read_bytes()


def test_s9_1_15_1_the_dry_run_lists_the_pyproject_as_a_seeded_create(
    node_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _snapshot(node_repo)

    commands.init(**NODE_SELECTORS, dry_run=True, json=True)

    row = _plan(capsys)["pyproject.toml"]
    assert (row["kind"], row["action"]) == ("seeded", "create")
    assert _snapshot(node_repo) == before


@pytest.mark.parametrize("archetype", ["python-app", "python-lib", "python-tool"])
def test_s9_1_15_1_other_archetypes_still_refuse_a_missing_pyproject(
    node_repo: Path, archetype: str
) -> None:
    before = _snapshot(node_repo)

    with pytest.raises(AppException) as error:
        commands.init(archetype=archetype, docs="mkdocs", yes=True)

    assert f"kiln init cannot run in {node_repo}: missing pyproject.toml" in str(
        error.value
    )
    assert _snapshot(node_repo) == before


def test_s9_1_15_2_docs_mkdocs_creates_the_missing_mkdocs_yml(
    node_repo: Path, rendered: Callable[[str], Path]
) -> None:
    commands.init(**NODE_SELECTORS, yes=True)

    text = (node_repo / "mkdocs.yml").read_text(encoding="utf-8")
    assert NAV_BLOCK.extract(text) is not None
    fresh = rendered("node-lib") / "mkdocs.yml"
    assert (node_repo / "mkdocs.yml").read_bytes() == fresh.read_bytes()


def test_s9_1_15_2_the_dry_run_lists_mkdocs_yml_as_a_managed_create(
    node_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commands.init(**NODE_SELECTORS, dry_run=True, json=True)

    row = _plan(capsys)["mkdocs.yml"]
    assert (row["kind"], row["action"]) == ("managed", "create")


def test_s9_1_15_2_docs_none_writes_no_mkdocs_yml(node_repo: Path) -> None:
    commands.init(archetype="node-lib", docs="none", yes=True)

    assert not (node_repo / "mkdocs.yml").exists()


def test_s9_1_15_2_an_existing_mkdocs_yml_is_archived_and_overwritten(
    node_repo: Path, rendered: Callable[[str], Path]
) -> None:
    own = "site_name: mine\n# BEGIN derived nav\nnav: []\n# END derived nav\n"
    (node_repo / "mkdocs.yml").write_text(own, encoding="utf-8")
    _commit(node_repo)

    commands.init(**NODE_SELECTORS, yes=True)

    fresh = rendered("node-lib") / "mkdocs.yml"
    assert (node_repo / "mkdocs.yml").read_bytes() == fresh.read_bytes()
    archives = (node_repo / ".rn-forge/kiln/backups").glob("*/mkdocs.yml")
    assert [a.read_text(encoding="utf-8") for a in archives] == [own]


def test_s9_1_15_2_a_python_archetype_also_gets_a_missing_mkdocs_yml(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "mkdocs.yml").unlink()
    _commit(repo)
    monkeypatch.undo()
    monkeypatch.chdir(repo)

    commands.init(**SELECTORS, yes=True)

    text = (repo / "mkdocs.yml").read_text(encoding="utf-8")
    assert NAV_BLOCK.extract(text) is not None


def test_s9_1_15_3_the_docs_group_init_completes_is_news_whole_group(
    node_repo: Path,
) -> None:
    (node_repo / "pyproject.toml").write_text(
        '[project]\nname = "node-lib"\nversion = "0"\n'
        'requires-python = ">=3.12"\n\n[dependency-groups]\n'
        'dev = ["ruff"]\ndocs = ["mdformat"]\n',
        encoding="utf-8",
    )
    _commit(node_repo)

    commands.init(**NODE_SELECTORS, yes=True)

    groups = tomllib.loads((node_repo / "pyproject.toml").read_text(encoding="utf-8"))[
        "dependency-groups"
    ]
    assert len(groups["docs"]) == _DOCS_GROUP_SIZE
    assert groups["docs"][0] == "mdformat"  # pinned already, at no version: kept
    names = {re.split(r"[\[<>=]", entry)[0] for entry in groups["docs"]}
    assert names == {
        "mdformat",
        "mdformat-front-matters",
        "mdformat-gfm",
        "mdformat-mkdocs",
        "mkdocs-material",
        "mkdocstrings",
    }


def test_s9_1_15_3_an_entry_pinned_at_any_version_is_kept(node_repo: Path) -> None:
    pinned = ["mdformat-gfm==0.3.5", "mkdocs-material>=9.0,<10"]
    body = "".join(f'    "{entry}",\n' for entry in pinned)
    (node_repo / "pyproject.toml").write_text(
        '[project]\nname = "node-lib"\nversion = "0"\n'
        'requires-python = ">=3.12"\n\n[dependency-groups]\n'
        f"docs = [\n{body}]\n",
        encoding="utf-8",
    )
    _commit(node_repo)

    commands.init(**NODE_SELECTORS, yes=True)

    docs = tomllib.loads((node_repo / "pyproject.toml").read_text(encoding="utf-8"))[
        "dependency-groups"
    ]["docs"]
    assert all(entry in docs for entry in pinned)
    assert len(docs) == _DOCS_GROUP_SIZE
    assert not [
        e for e in docs if e.startswith(("mdformat-gfm>", "mkdocs-material>=9.6"))
    ]


def test_s9_1_15_4_the_adopt_prompt_does_not_ask_for_these_files_by_hand() -> None:
    text = (ROOT / "src/rn_forge/kiln/prompts/adopt.md").read_text(encoding="utf-8")
    section = text.split("## 2. Prepare", 1)[1].split("## 3.", 1)[0]
    assert "mkdocs.yml" not in section
    assert "pyproject.toml" not in section.split("node-lib", 1)[-1].split("```", 1)[0]


# S16.1.1 — `init` refuses a dirty worktree, always.


def test_s16_1_1_1_dirty_tree_is_refused(lib_repo: Path) -> None:
    (lib_repo / "scratch.txt").write_text("x\n", encoding="utf-8")
    before = _snapshot(lib_repo)

    with pytest.raises(AppException, match="init.dirty-tree"):
        commands.init(archetype="python-lib", docs="mkdocs", yes=True)

    assert _snapshot(lib_repo) == before
    assert not (lib_repo / ".rn-forge").exists()


def test_s16_1_1_2_dry_run_does_not_need_a_clean_tree(lib_repo: Path) -> None:
    (lib_repo / "scratch.txt").write_text("x\n", encoding="utf-8")
    before = _snapshot(lib_repo)

    commands.init(archetype="python-lib", docs="mkdocs", yes=True, dry_run=True)

    assert _snapshot(lib_repo) == before
    assert not (lib_repo / ".rn-forge").exists()


def test_s16_1_1_3_force_is_gone() -> None:
    assert "force" not in inspect.signature(commands.init).parameters
    assert main.app(["init", "--archetype", "python-app", "--force"]) == 2


# S16.1.2 — `init` overwrites kiln-shaped files and archives them.

_LIB = {"archetype": "python-lib", "docs": "mkdocs"}
_OVERWRITTEN = (
    "Taskfile.yml",
    "docs/_areas.yml",
    "docs/specs/_structure.md",
    "docs/specs/epics/index.md",
    ".github/workflows/ci.yml",
)


def _hand_edit(root: Path) -> dict[str, bytes]:
    """Replace each of `_OVERWRITTEN` with content of the repository's own; return the bytes."""
    for relative in _OVERWRITTEN:
        path = root / relative
        mine = f"# mine: {relative}\n"
        # nav is built from _areas.yml, so it stays a mapping
        path.write_text(
            path.read_text(encoding="utf-8") + mine
            if relative == "docs/_areas.yml"
            else mine,
            encoding="utf-8",
        )
    _commit(root)
    return {relative: (root / relative).read_bytes() for relative in _OVERWRITTEN}


def _lib_init(root: Path, tmp_path: Path) -> None:
    config = _packages_config(tmp_path, "packages/lib-alpha", "packages/lib-beta")
    commands.init(**_LIB, config=config, yes=True)


def test_s16_1_2_1_overwrites(lib_repo: Path, lib_fresh: Path, tmp_path: Path) -> None:
    _hand_edit(lib_repo)

    _lib_init(lib_repo, tmp_path)

    for relative in _OVERWRITTEN:
        assert (lib_repo / relative).read_bytes() == (lib_fresh / relative).read_bytes()
    config = ConfigManager().load(lib_repo)
    planned = cycle.adoption_plan(lib_repo, config)
    stale = [
        change.path
        for change in planned.changes
        if change.path in _OVERWRITTEN
        and change.action not in (Action.UNCHANGED, Action.SKIP, Action.CONFLICT)
    ]
    assert stale == []


def test_s16_1_2_2_backups(
    lib_repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = _hand_edit(lib_repo)

    _lib_init(lib_repo, tmp_path)

    backups = lib_repo / ".rn-forge/kiln/backups"
    for relative, content in before.items():
        assert [file.read_bytes() for file in backups.glob(f"*/{relative}")][0] == (
            content
        )
    printed = "".join(capsys.readouterr().out.split())
    assert any(str(directory) in printed for directory in backups.iterdir())


def test_s16_1_2_3_content_is_never_touched(lib_repo: Path, tmp_path: Path) -> None:
    kept = {
        "README.md": "# mine\n",
        "docs/guides/x.md": "# x\n\nwords\n",
        "docs/adr/ADR-0001.md": "# ADR-0001\n\nwords\n",
        "docs/guides/index.md": "# Guides\n\nour own guide index\n",
        "docs/specs/epics/index.md": (
            "# Epics\n\nour own intro\n\n<!-- BEGIN derived epics -->\n\n"
            "| [E1 — Mine](E1/index.md) | Closed |\n\n<!-- END derived epics -->\n"
        ),
    }
    source = next((lib_repo / "packages/lib-alpha/src").rglob("*.py"))
    test = next((lib_repo / "packages/lib-alpha/tests").rglob("*.py"))
    for relative, text in kept.items():
        (lib_repo / relative).write_text(text, encoding="utf-8")
    source.write_text("# mine\n", encoding="utf-8")
    test.write_text("# mine\n", encoding="utf-8")
    _commit(lib_repo)
    paths = [
        *kept,
        source.relative_to(lib_repo).as_posix(),
        test.relative_to(lib_repo).as_posix(),
    ]
    before = {path: (lib_repo / path).read_bytes() for path in paths}

    _lib_init(lib_repo, tmp_path)

    after = {path: (lib_repo / path).read_bytes() for path in paths}
    epics = "docs/specs/epics/index.md"  # its fence is regenerated
    assert b"our own intro" in after.pop(epics)
    before.pop(epics)
    assert after == before


def test_s16_1_2_3_whitespace_only_differences_are_not_content(
    lib_repo: Path, lib_fresh: Path, tmp_path: Path
) -> None:
    seed = (lib_fresh / "docs/guides/index.md").read_text(encoding="utf-8")
    (lib_repo / "docs/guides/index.md").write_text(seed + "\n\n  \n", encoding="utf-8")
    _commit(lib_repo)

    _lib_init(lib_repo, tmp_path)

    assert (lib_repo / "docs/guides/index.md").read_text(encoding="utf-8") == seed


def test_s16_1_2_4_pyproject_and_gitignore_merge(
    lib_repo: Path, tmp_path: Path
) -> None:
    pyproject = lib_repo / "pyproject.toml"
    document = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
    document["project"]["description"] = "my own words"  # type: ignore[index]
    pyproject.write_text(tomlkit.dumps(document), encoding="utf-8")
    with (lib_repo / ".gitignore").open("a", encoding="utf-8") as handle:
        handle.write("\nmine_only/\n")
    _commit(lib_repo)

    _lib_init(lib_repo, tmp_path)

    written = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert written["project"]["description"] == "my own words"
    ignore = (lib_repo / ".gitignore").read_text(encoding="utf-8")
    assert "mine_only/" in ignore.split(GITIGNORE_BLOCK.begin, 1)[0]


def test_s16_1_2_5_no_conflict_stage(
    lib_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _hand_edit(lib_repo)
    config = _packages_config(tmp_path, "packages/lib-alpha", "packages/lib-beta")

    code = main.app(["init", "--archetype", "python-lib", "--config", config, "--yes"])

    assert code == 0
    captured = capsys.readouterr()
    assert "nothing written" not in captured.out + captured.err


def _local_kiln(root: Path) -> str:
    """The `KILN` variable that runs this checkout's kiln, not the repository's pinned ref."""
    return f"KILN=uv run --project {ROOT} kiln"


def _real_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    if shutil.which("task") is None or shutil.which("uv") is None:
        pytest.skip("task or uv is not on PATH")

    def run(root: Path, name: str) -> None:
        subprocess.run(["task", name, _local_kiln(root)], cwd=root, check=True)

    monkeypatch.setattr(commands, "_run_task", run)


def _lint(root: Path) -> None:
    done = subprocess.run(
        ["task", "lint", _local_kiln(root)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_s16_1_3_1_lint_passes_after_init(
    lib_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _real_tasks(monkeypatch)

    _lib_init(lib_repo, tmp_path)

    _lint(lib_repo)


def test_s16_1_3_2_order(
    lib_repo: Path, tmp_path: Path, task_calls: list[tuple[Path, str]]
) -> None:
    _lib_init(lib_repo, tmp_path)

    assert task_calls == [
        (lib_repo, "setup"),
        (lib_repo, "format"),
        (lib_repo, "docs:generate"),
    ]


def test_s16_1_3_2_a_failing_step_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_a: object, **_k: object) -> None:
        raise subprocess.CalledProcessError(1, ["task", "format"])

    monkeypatch.setattr(commands.subprocess, "run", fail)
    with pytest.raises(AppException, match=r"`task format` failed"):
        _REAL_RUN_TASK(tmp_path, "format")


def test_s16_1_3_3_dry_run_runs_nothing(
    lib_repo: Path, task_calls: list[tuple[Path, str]]
) -> None:
    commands.init(**_LIB, dry_run=True, yes=True)
    commands.init(**_LIB)

    assert task_calls == []


@pytest.mark.parametrize("docs", ["none", "external"])
def test_s16_1_3_4_no_docs_profile(
    repo: Path, docs: str, task_calls: list[tuple[Path, str]]
) -> None:
    commands.init(archetype="python-app", docs=docs, yes=True)

    assert [name for _, name in task_calls] == ["setup", "format"]


@pytest.mark.parametrize("docs", ["none", "external"])
def test_s16_1_3_4_no_docs_profile_lint_passes(
    repo: Path, docs: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _real_tasks(monkeypatch)
    config = tmp_path / "external.toml"
    config.write_text('[docs]\nexternal_url = "https://docs.example.com"\n')

    commands.init(
        archetype="python-app",
        docs=docs,
        config=str(config) if docs == "external" else None,
        yes=True,
    )

    _lint(repo)
