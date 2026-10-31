"""S4.5.8 — `kiln init`: bring an existing standard repository under kiln.

Built over a copy of the session-rendered `python-app` repo (`rendered` in
`tests/conftest.py`), with `.rn-forge/` and every kiln block removed and a
`.git` entry added: a standard repository kiln has never seen, whose managed
files already equal their renders. No test runs a scaffold; every scaffold
function `commands` imports is replaced by one that records and fails.
"""

from __future__ import annotations

import json
import os
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

from rn_forge.kiln import commands
from rn_forge.kiln.config import KilnConfig
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
    "docs_scaffold",
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


def test_s4_5_8_1_force_over_differences_reproduces_a_fresh_new(
    repo: Path, fresh: Path
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    _tamper_block(repo, fresh, "CLAUDE.md")
    _commit(repo)

    commands.init(**SELECTORS, force=True, yes=True)

    assert _entries(repo) == _entries(fresh)
    for entry in _entries(fresh).values():
        if entry["kind"] == "managed":
            assert (repo / entry["path"]).read_bytes() == (
                fresh / entry["path"]
            ).read_bytes()
    claude = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert "tampered" not in claude
    assert tomllib.loads((repo / CONFIG).read_text(encoding="utf-8")) == tomllib.loads(
        (fresh / CONFIG).read_text(encoding="utf-8")
    )


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


def test_s4_5_8_3_unforced_conflicts_are_all_named_and_nothing_changes(
    repo: Path, fresh: Path
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    _tamper_block(repo, fresh, "CLAUDE.md")
    _commit(repo)
    before = _snapshot(repo)

    with pytest.raises(AppException) as raised:
        commands.init(**SELECTORS, yes=True)

    assert "Taskfile.yml" in str(raised.value)
    assert "CLAUDE.md" in str(raised.value)
    assert _snapshot(repo) == before
    assert not (repo / ".rn-forge").exists()


def test_s4_5_8_3_a_block_without_a_state_entry_is_a_conflict_even_if_equal(
    repo: Path, fresh: Path
) -> None:
    (repo / "CLAUDE.md").write_bytes((fresh / "CLAUDE.md").read_bytes())
    _commit(repo)
    before = _snapshot(repo)

    with pytest.raises(AppException, match="CLAUDE.md"):
        commands.init(**SELECTORS, yes=True)
    assert _snapshot(repo) == before


def test_s4_5_8_3_an_existing_config_without_state_is_a_conflict(
    repo: Path, fresh: Path
) -> None:
    (repo / CONFIG).parent.mkdir(parents=True)
    (repo / CONFIG).write_text("# mine\n", encoding="utf-8")
    _commit(repo)
    with pytest.raises(AppException, match="config.toml"):
        commands.init(**SELECTORS, yes=True)
    assert (repo / CONFIG).read_text(encoding="utf-8") == "# mine\n"
    assert not (repo / STATE).exists()


def test_s4_5_8_4_force_archives_every_overwritten_target(
    repo: Path, fresh: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    _tamper_block(repo, fresh, "CLAUDE.md")
    claude_before = (repo / "CLAUDE.md").read_bytes()
    gitignore = repo / ".gitignore"
    gitignore.write_text("custom-entry\n", encoding="utf-8")
    _commit(repo)

    commands.init(**SELECTORS, force=True, yes=True)

    assert "--force" in capsys.readouterr().err
    stamps = list((repo / ".rn-forge/kiln/backups").iterdir())
    archive = next(stamp for stamp in stamps if (stamp / "Taskfile.yml").exists())
    assert (archive / "Taskfile.yml").read_text(encoding="utf-8") == "# hand made\n"
    assert (archive / "CLAUDE.md").read_bytes() == claude_before
    assert gitignore.read_text(encoding="utf-8").startswith("custom-entry\n")
    assert "tampered" not in (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert (repo / "Taskfile.yml").read_text(encoding="utf-8") != "# hand made\n"


def test_s4_5_8_5_a_second_unforced_init_fails_naming_the_state(repo: Path) -> None:
    commands.init(**SELECTORS, yes=True)
    _commit(repo)
    before = _snapshot(repo)

    with pytest.raises(AppException, match="state.json"):
        commands.init(**SELECTORS, yes=True)
    assert _snapshot(repo) == before


def test_s4_5_8_5_a_forced_reinit_archives_state_and_applies_the_new_selectors(
    repo: Path,
) -> None:
    commands.init(**SELECTORS, yes=True)
    _commit(repo)
    old_state = (repo / STATE).read_bytes()
    old_config = (repo / CONFIG).read_bytes()

    commands.init(archetype="python-app", docs="none", force=True, yes=True)

    archived = {
        relative: [
            (stamp / relative).read_bytes()
            for stamp in (repo / ".rn-forge/kiln/backups").iterdir()
            if (stamp / relative).exists()
        ]
        for relative in (STATE, CONFIG)
    }
    assert old_state in archived[STATE]
    assert old_config in archived[CONFIG]
    config = tomllib.loads((repo / CONFIG).read_text(encoding="utf-8"))
    assert config["docs"]["profile"] == "none"
    assert _entries(repo) != json.loads(old_state)["entries"]


def test_s4_5_8_6_neither_path_runs_a_scaffold(
    repo: Path, scaffold_calls: list[str]
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    _commit(repo)
    commands.init(**SELECTORS, force=True, yes=True)
    _commit(repo)
    commands.init(**SELECTORS, force=True, yes=True)
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


def test_s4_5_8_force_does_not_imply_yes_and_dry_run_beats_yes(repo: Path) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    before = _snapshot(repo)
    commands.init(**SELECTORS, force=True)
    commands.init(**SELECTORS, force=True, yes=True, dry_run=True)
    assert _snapshot(repo) == before


def test_s4_5_8_a_failing_check_keeps_the_writes_and_the_archive(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "Taskfile.yml").write_text("# hand made\n", encoding="utf-8")
    monkeypatch.setattr(
        commands.checks,
        "run",
        lambda *_a, **_k: [Finding("x.y", Severity.ERROR, "broken")],
    )
    _commit(repo)
    with pytest.raises(AppException, match="check"):
        commands.init(**SELECTORS, force=True, yes=True)
    assert (repo / STATE).is_file()
    assert (repo / CONFIG).is_file()
    assert any((repo / ".rn-forge/kiln/backups").glob("*/Taskfile.yml"))


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
    document["dependency-groups"]["dev"].remove("taplo")  # type: ignore[index]
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
    removed = ["README.md", "CLAUDE.md", "AGENTS.md", ".gitignore", "docs", ".github"]
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


def test_s6_1_7_1_force_fences_and_keeps_the_contracts(repo: Path, fresh: Path) -> None:
    (repo / ".importlinter").write_text(_MINE, encoding="utf-8")
    _commit(repo)

    commands.init(**SELECTORS, force=True, yes=True)

    block = IMPORTLINTER_BLOCK
    text = (repo / ".importlinter").read_text(encoding="utf-8")
    assert block.extract(text) == block.extract(
        (fresh / ".importlinter").read_text(encoding="utf-8")
    )
    after = text.split(block.end, 1)[1]
    assert "; mine" in after
    assert _MINE.split("\n\n", 1)[1] in after
    assert "[importlinter]" not in after.splitlines()
    assert "other" not in after
    archives = (repo / ".rn-forge/kiln/backups").glob("*/.importlinter")
    assert [a.read_bytes() for a in archives if a.read_bytes() == _MINE.encode()]


def test_s6_1_7_2_without_force_it_is_still_refused(repo: Path) -> None:
    (repo / ".importlinter").write_text(_MINE, encoding="utf-8")
    _commit(repo)
    before = _snapshot(repo)

    with pytest.raises(AppException, match="core.block-unfenced"):
        commands.init(**SELECTORS, yes=True)
    assert _snapshot(repo) == before


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
) -> None:
    root = _renamed_repo(fresh, tmp_path, monkeypatch)
    layer = tmp_path / "layer.toml"
    layer.write_text("# no repository name\n", encoding="utf-8")

    commands.init(**SELECTORS, config=str(layer), force=True, yes=True)

    written = tomllib.loads((root / CONFIG).read_text(encoding="utf-8"))
    assert written["repository"]["name"] == "other-dir"


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


def test_s6_1_9_1_unmarked_nav_is_refused_before_anything_is_written(
    repo: Path,
) -> None:
    _unmark_nav(repo)
    before = _snapshot(repo)

    with pytest.raises(AppException, match="init.nav-unmarked") as error:
        commands.init(**SELECTORS, yes=True)
    assert "mkdocs.yml" in str(error.value)
    assert "--force" in str(error.value)
    assert _snapshot(repo) == before
    assert not (repo / ".rn-forge").exists()


def test_s6_1_9_2_force_marks_the_nav_and_derives_it(repo: Path, fresh: Path) -> None:
    unmarked = _unmark_nav(repo)

    commands.init(**SELECTORS, force=True, yes=True)

    assert (repo / "mkdocs.yml").read_bytes() == (fresh / "mkdocs.yml").read_bytes()
    archives = (repo / ".rn-forge/kiln/backups").glob("*/mkdocs.yml")
    assert [a for a in archives if a.read_bytes() == unmarked]


def test_s6_1_9_3_force_adds_a_nav_when_there_is_none(repo: Path, fresh: Path) -> None:
    text = (repo / "mkdocs.yml").read_text(encoding="utf-8")
    head = text.split("\nnav:\n", 1)[0]
    tail = text.split(NAV_BLOCK.end, 1)[1]
    (repo / "mkdocs.yml").write_text(head + "\n" + tail.lstrip("\n"), encoding="utf-8")
    assert "nav:" not in (repo / "mkdocs.yml").read_text(encoding="utf-8")
    _commit(repo)

    commands.init(**SELECTORS, force=True, yes=True)

    def nav(root: Path) -> str | None:
        return NAV_BLOCK.extract((root / "mkdocs.yml").read_text(encoding="utf-8"))

    assert nav(repo) is not None
    assert nav(repo) == nav(fresh)
