"""S4.2.3 — `core` artifacts and the cycle adapter."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.paths import PathUtils
from rn_forge.tooling.generation import Action, ArtifactKind, StateEntry
from rn_forge.tooling.state import StateStore

from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import CORE, cycle, umbrella
from rn_forge.kiln.modules.core.cycle import CycleRefused
from rn_forge.kiln.modules.python import PYTHON

CONFIG = 'schema_version = 1\n\n[repository]\nname = "demo"\narchetype = "python-app"\n'
STATE = Path(".rn-forge/kiln/state.json")
TAPLO = Path(sys.executable).parent / "taplo"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    config = repo / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    return repo


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path / "home"


def actions(root: Path, home: Path, **kwargs) -> dict[str, Action]:
    return {
        change.key: change.action
        for change in cycle.plan(root, home=home, **kwargs).changes
    }


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and umbrella.BACKUPS not in path.relative_to(root).parents
        and umbrella.RENDERED not in path.relative_to(root).parents
    }


def test_s4_2_3_applying_core_into_an_empty_directory_only_creates_and_inserts(
    root: Path, home: Path
) -> None:
    assert actions(root, home) == {
        ".editorconfig": Action.CREATE,
        ".mdformat.toml": Action.CREATE,
        ".taplo.toml": Action.CREATE,
        "demo.code-workspace": Action.CREATE,
        ".gitignore#rn-forge kiln": Action.INSERT,
        ".importlinter#rn-forge kiln": Action.INSERT,
        "Taskfile.yml": Action.CREATE,
        "tasks/workspace.yml": Action.CREATE,
        "tasks/quality.yml": Action.CREATE,
        "tasks/python.yml": Action.CREATE,
        "tasks/kiln.yml": Action.CREATE,
        "tasks/ci.yml": Action.CREATE,
        ".github/actions/setup/action.yml": Action.CREATE,
        ".github/workflows/ci.yml": Action.CREATE,
        ".github/dependabot.yml": Action.CREATE,
        "sonar-project.properties": Action.CREATE,
        "CLAUDE.md#rn-forge kiln": Action.INSERT,
        ".rn-forge/kiln/standard.md": Action.CREATE,
    }
    cycle.apply(root, home=home)
    for path in (
        ".editorconfig",
        ".mdformat.toml",
        ".taplo.toml",
        "demo.code-workspace",
        ".gitignore",
        ".importlinter",
        "Taskfile.yml",
        "tasks/workspace.yml",
        "tasks/quality.yml",
        "tasks/python.yml",
        "tasks/kiln.yml",
        "tasks/ci.yml",
        ".github/actions/setup/action.yml",
        ".github/workflows/ci.yml",
        "sonar-project.properties",
        "CLAUDE.md",
        ".rn-forge/kiln/standard.md",
        ".rn-forge/kiln/state.json",
    ):
        assert (root / path).is_file(), path
    assert ".rn-forge/kiln/backups/" in (root / ".gitignore").read_text(
        encoding="utf-8"
    )


def test_s5_3_1_mdformat_config_is_seeded_once(tmp_path: Path, home: Path) -> None:
    root = tmp_path / "absent"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    cycle.apply(root, home=home)
    seeded = root / ".mdformat.toml"
    assert seeded.is_file()
    assert ".rn-forge/kiln/rendered/**" in seeded.read_text(encoding="utf-8")

    existing = tmp_path / "present"
    config = existing / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    expected = "wrap = 100\n"
    existing_file = existing / ".mdformat.toml"
    existing_file.write_text(expected, encoding="utf-8")
    cycle.apply(existing, home=home)
    assert existing_file.read_text(encoding="utf-8") == expected


def test_s4_10_1_1_taplo_config_is_seeded_once(tmp_path: Path, home: Path) -> None:
    root = tmp_path / "absent"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    cycle.apply(root, home=home)
    seeded = root / ".taplo.toml"
    assert seeded.is_file()
    assert ".rn-forge/kiln/rendered/**" in seeded.read_text(encoding="utf-8")

    existing = tmp_path / "present"
    config = existing / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    expected = "include = []\n"
    existing_file = existing / ".taplo.toml"
    existing_file.write_text(expected, encoding="utf-8")
    cycle.apply(existing, home=home)
    assert existing_file.read_text(encoding="utf-8") == expected


def test_s4_10_1_6_seeded_toml_is_taplo_clean(root: Path, home: Path) -> None:
    cycle.apply(root, home=home)
    for relative in (".mdformat.toml", ".taplo.toml"):
        result = subprocess.run(
            [str(TAPLO), "fmt", "--check", "--diff", relative],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_s5_3_6_5_workspace_file_is_one_relative_folder(
    root: Path, home: Path, tmp_path: Path
) -> None:
    cycle.apply(root, home=home)
    text = (root / "demo.code-workspace").read_text(encoding="utf-8")
    assert json.loads(text) == {"folders": [{"path": "."}]}
    assert str(root) not in text
    assert str(Path.home()) not in text

    moved = tmp_path / "elsewhere" / "checkout"
    shutil.copytree(root, moved)
    workspace = moved / "demo.code-workspace"
    (folder,) = json.loads(workspace.read_text(encoding="utf-8"))["folders"]
    assert (workspace.parent / folder["path"]).resolve() == moved.resolve()


def test_s5_3_6_5_apply_preserves_user_edits_to_the_workspace_file(
    root: Path, home: Path
) -> None:
    cycle.apply(root, home=home)
    workspace = root / "demo.code-workspace"
    edited = '{"folders": [{"path": "."}], "settings": {"editor.tabSize": 2}}\n'
    workspace.write_text(edited, encoding="utf-8")

    cycle.apply(root, home=home)
    assert workspace.read_text(encoding="utf-8") == edited


def test_s4_2_3_a_freshly_applied_repo_passes_the_generated_check(
    root: Path, home: Path
) -> None:
    cycle.apply(root, home=home)
    assert checks.run(root, only="generated") == []


def test_s4_2_3_a_second_apply_is_unchanged_and_leaves_state_byte_identical(
    root: Path, home: Path
) -> None:
    cycle.apply(root, home=home)
    before = (root / STATE).read_bytes()

    assert set(actions(root, home).values()) <= {Action.UNCHANGED, Action.SKIP}
    cycle.apply(root, home=home)
    assert (root / STATE).read_bytes() == before


def test_s4_2_3_a_hand_edited_artifact_is_drift_and_nothing_is_written(
    root: Path, home: Path
) -> None:
    cycle.apply(root, home=home)
    editorconfig = root / ".editorconfig"
    editorconfig.write_text("root = false\n", encoding="utf-8")
    before = snapshot(root)

    assert actions(root, home)[".editorconfig"] is Action.DRIFT
    with pytest.raises(AppException, match="unapproved"):
        cycle.apply(root, home=home)
    assert snapshot(root) == before


def test_s4_2_3_forcing_a_drifted_path_rewrites_only_it(root: Path, home: Path) -> None:
    cycle.apply(root, home=home)
    rendered = (root / ".editorconfig").read_bytes()
    (root / ".editorconfig").write_text("root = false\n", encoding="utf-8")
    before = snapshot(root)

    planned = cycle.plan(root, force=[".editorconfig"], home=home)
    assert [change.path for change in planned.writes] == [".editorconfig"]
    cycle.apply(root, force=[".editorconfig"], home=home)

    after = snapshot(root)
    assert after.pop(".editorconfig") == rendered
    before.pop(".editorconfig")
    assert after == before


def test_s4_2_3_a_legacy_kiln_tree_is_refused_and_nothing_is_written(
    tmp_path: Path, home: Path
) -> None:
    repo = tmp_path / "legacy"
    tree = repo / ".rn-forge" / "kiln"
    tree.mkdir(parents=True)
    (tree / "state.json").write_text(json.dumps({"entries": {}}), encoding="utf-8")
    before = snapshot(repo)

    with pytest.raises(CycleRefused) as caught:
        cycle.apply(repo, home=home)
    assert [finding.code for finding in caught.value.findings] == ["legacy.kiln-state"]
    assert snapshot(repo) == before


def test_s4_2_3_a_legacy_tree_under_rnf_home_is_refused(root: Path, home: Path) -> None:
    (home / "kiln").mkdir(parents=True)
    (home / "kiln" / "config.toml").write_text("[kiln]\n", encoding="utf-8")
    with pytest.raises(CycleRefused, match="legacy.kiln-state"):
        cycle.apply(root, home=home)
    assert not (root / ".editorconfig").exists()


def test_s4_2_3_find_root_from_a_nested_directory_returns_the_repo_root(
    root: Path,
) -> None:
    nested = root / "src" / "demo" / "deep"
    nested.mkdir(parents=True)
    assert umbrella.find_root(nested) == root.resolve()


def test_s4_2_3_a_write_failure_mid_transaction_rolls_everything_back(
    root: Path, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    state = root / STATE
    state.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "entries": {"README.md": {"path": "README.md", "kind": "seeded"}},
            }
        ),
        encoding="utf-8",
    )
    before = snapshot(root)
    original = PathUtils.atomic_write
    written: list[Path] = []

    def failing(content, path, *args, **kwargs):
        if Path(path) == root / ".gitignore":
            raise OSError("disk full")
        written.append(Path(path))
        return original(content, path, *args, **kwargs)

    monkeypatch.setattr(PathUtils, "atomic_write", staticmethod(failing))
    with pytest.raises(AppException, match="rolled back"):
        cycle.apply(root, home=home)

    assert root / ".editorconfig" in written  # the failure really was mid-transaction
    assert snapshot(root) == before


def test_s4_2_3_core_checks_report_what_doctor_only_generated_reports(
    root: Path, home: Path
) -> None:
    cycle.apply(root, home=home)
    (root / ".editorconfig").write_text("root = false\n", encoding="utf-8")
    (root / ".gitignore").write_text("", encoding="utf-8")

    from_doctor = [str(finding) for finding in checks.run(root, only="generated")]
    from_core = [str(finding) for finding in CORE.checks(KilnConfig.load(root), root)]
    assert len(from_doctor) == 2
    assert from_core == from_doctor


IMPORTLINTER_KEY = ".importlinter#rn-forge kiln"
END_MARKER = "# END rn-forge kiln"


def test_s4_7_3_1_new_repo_gets_a_fenced_importlinter(root: Path, home: Path) -> None:
    cycle.apply(root, home=home)
    first = (root / ".importlinter").read_text(encoding="utf-8").splitlines()[0]
    assert first == "# BEGIN rn-forge kiln"
    assert actions(root, home)[IMPORTLINTER_KEY] is Action.UNCHANGED


def test_s4_7_3_2_own_contract_below_the_block_survives(root: Path, home: Path) -> None:
    cycle.apply(root, home=home)
    path = root / ".importlinter"
    own = "\n[importlinter:contract:mine]\nname = mine\ntype = forbidden\n"
    path.write_text(path.read_text(encoding="utf-8") + own, encoding="utf-8")
    before = path.read_bytes()

    assert actions(root, home)[IMPORTLINTER_KEY] is Action.UNCHANGED
    cycle.apply(root, home=home)
    assert path.read_bytes() == before
    assert actions(root, home)[IMPORTLINTER_KEY] is Action.UNCHANGED


@pytest.mark.parametrize("adopt", [False, True])
def test_s4_7_3_3_unfenced_importlinter_is_refused(
    root: Path, home: Path, adopt: bool
) -> None:
    path = root / ".importlinter"
    path.write_text("[importlinter]\nroot_package = demo\n", encoding="utf-8")
    before = snapshot(root)

    with pytest.raises(CycleRefused) as refused:
        cycle.plan(root, home=home, adopt=adopt)
    (finding,) = refused.value.findings
    assert finding.code == "core.block-unfenced"
    assert finding.path == ".importlinter"
    assert snapshot(root) == before


def test_s4_7_3_4_converted_entry_is_forgotten(root: Path) -> None:
    config = KilnConfig.load(root)
    artifacts = PYTHON.artifacts(config, root) + CORE.artifacts(config, root)
    managed = StateEntry(
        path=".importlinter", kind=ArtifactKind.MANAGED, content_hash="x"
    )
    block = next(a for a in artifacts if a.path == ".gitignore")
    block_entry = StateEntry(
        path=".gitignore", kind=ArtifactKind.BLOCK, content_hash="y"
    )
    taskfile = StateEntry(
        path="Taskfile.yml", kind=ArtifactKind.MANAGED, content_hash="z"
    )
    assert block.block is not None
    entries = {
        ".importlinter": managed,
        ".gitignore#rn-forge kiln": block_entry,
        "Taskfile.yml": taskfile,
    }
    assert cycle._without_converted(entries, artifacts) == {
        ".gitignore#rn-forge kiln": block_entry,
        "Taskfile.yml": taskfile,
    }


def test_s4_7_3_5_fenced_file_with_old_state_converts_under_force(
    root: Path, home: Path
) -> None:
    cycle.apply(root, home=home)
    store = StateStore(
        root / STATE, entry_type=StateEntry, schema_version=cycle.STATE_SCHEMA_VERSION
    )
    entries = store.load()
    del entries[IMPORTLINTER_KEY]
    entries[".importlinter"] = StateEntry(
        path=".importlinter", kind=ArtifactKind.MANAGED, content_hash="x"
    )
    store.replace_all(entries)

    planned = cycle.plan(root, home=home)
    by_key = {change.key: change.action for change in planned.changes}
    assert by_key[IMPORTLINTER_KEY] is Action.CONFLICT
    assert ".importlinter" not in by_key

    cycle.apply(root, home=home, force=[".importlinter"])
    text = (root / ".importlinter").read_text(encoding="utf-8")
    assert text.startswith("# BEGIN rn-forge kiln")
