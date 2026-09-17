"""S4.2.3 — `core` artifacts and the cycle adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.paths import PathUtils
from rn_forge.tooling.generation import Action

from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import CORE, cycle, umbrella
from rn_forge.kiln.modules.core.cycle import CycleRefused

CONFIG = 'schema_version = 1\n\n[repository]\nname = "demo"\narchetype = "python-app"\n'
STATE = Path(".rn-forge/kiln/state.json")


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
        ".gitignore#rn-forge kiln": Action.INSERT,
        ".importlinter": Action.CREATE,
        "Taskfile.yml": Action.CREATE,
        "tasks/workspace.yml": Action.CREATE,
        "tasks/quality.yml": Action.CREATE,
        ".github/actions/setup/action.yml": Action.CREATE,
        ".github/workflows/ci.yml": Action.CREATE,
        "sonar-project.properties": Action.CREATE,
        "CLAUDE.md#rn-forge kiln": Action.INSERT,
        ".rn-forge/kiln/standard.md": Action.CREATE,
    }
    cycle.apply(root, home=home)
    for path in (
        ".editorconfig",
        ".mdformat.toml",
        ".gitignore",
        ".importlinter",
        "Taskfile.yml",
        "tasks/workspace.yml",
        "tasks/quality.yml",
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
