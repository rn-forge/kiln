"""S4.5.3 — `kiln diff` and `kiln version`: inspection.

Built over the same rendered-repo fixture as `test_apply.py` (the nearest `done`
story in this feature) — already scaffolded and passing, so no `uv init` is
needed.
"""

from __future__ import annotations

import inspect
import json
import subprocess
from collections.abc import Callable
import shutil
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import commands
from rn_forge.kiln.modules.core import cycle

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


@pytest.fixture
def repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rendered: Callable[[str], Path],
) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(rendered("python-tool"), root, ignore=_IGNORE)
    cycle.apply(root)
    monkeypatch.chdir(root)
    yield root
    console.set_mode(OutputMode.PLAIN)


def _last_json(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    out = capsys.readouterr().out.strip().splitlines()
    return json.loads(out[-1])


def _edit_taskfile(repo: Path) -> None:
    target = repo / "Taskfile.yml"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# edit\n", encoding="utf-8"
    )


def test_s4_5_3_1_clean_repo_diff_prints_nothing_and_exits_0(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commands.diff()
    assert capsys.readouterr().out == ""


def test_s4_5_3_1_edited_artifact_diff_names_the_path_and_raises(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _edit_taskfile(repo)
    with pytest.raises(AppException):
        commands.diff()
    out = capsys.readouterr().out
    assert "Taskfile.yml" in out
    assert "# edit" in out


def test_s4_5_3_1_diff_limits_to_the_named_artifact(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _edit_taskfile(repo)
    editorconfig = repo / ".editorconfig"
    editorconfig.write_text(
        editorconfig.read_text(encoding="utf-8") + "\n# edit\n", encoding="utf-8"
    )

    with pytest.raises(AppException):
        commands.diff("Taskfile.yml")
    out = capsys.readouterr().out
    assert "Taskfile.yml" in out
    assert ".editorconfig" not in out


def test_s4_5_3_1_unknown_artifact_is_refused_by_name(repo: Path) -> None:
    with pytest.raises(AppException, match="nope"):
        commands.diff("nope")


def test_s4_5_3_2_version_json_matches_the_installed_distribution(
    capsys: pytest.CaptureFixture[str],
) -> None:
    commands.version(json=True)
    payload = _last_json(capsys)
    assert payload["version"] == metadata.version("rn-forge-kiln")


@pytest.fixture
def reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rendered: Callable[[str], Path],
) -> Path:
    root = tmp_path / "reference"
    shutil.copytree(rendered("python-lib"), root, ignore=_IGNORE)
    monkeypatch.chdir(root)
    yield root
    console.set_mode(OutputMode.PLAIN)


@pytest.fixture
def old(tmp_path: Path, reference: Path) -> Path:
    root = tmp_path / "old"
    (root / "docs").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / "Taskfile.yml").write_text("version: '3'\n", encoding="utf-8")
    (root / ".gitignore").write_text("own\n", encoding="utf-8")
    (root / "docs" / "index.md").write_text("own\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("own\n", encoding="utf-8")
    shutil.copyfile(reference / "README.md", root / "README.md")
    (root / "legacy.yml").write_text("x: 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def _snapshot(*roots: Path) -> dict[str, bytes]:
    return {
        str(path): path.read_bytes()
        for root in roots
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_s16_9_11_1_every_class_is_reported_once(
    reference: Path, old: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commands.diff(old=str(old), json=True)
    rows = _last_json(capsys)["inventory"]
    got = {(r["path"], r["kind"], r["status"]) for r in rows}
    assert len(rows) == len({r["path"] for r in rows})
    assert {
        ("Taskfile.yml", "managed", "differs"),
        (".gitignore", "block", "differs"),
        ("docs/index.md", "seeded", "differs"),
        ("pyproject.toml", "scaffolded", "differs"),
        ("README.md", "scaffolded", "same"),
        ("legacy.yml", "old-only", "old-only"),
        (".editorconfig", "managed", "reference-only"),
    } <= got


def test_s16_9_11_2_old_only_rows_come_last_in_plain_output(
    reference: Path, old: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commands.diff(old=str(old))
    lines = capsys.readouterr().out.strip().splitlines()
    body, summary = lines[:-1], lines[-1]
    assert body[-1].split()[-1] == "legacy.yml"
    order = ("managed", "block", "seeded", "scaffolded", "old-only")
    kinds = [order.index(line.split()[0]) for line in body]
    assert kinds == sorted(kinds)
    for kind in order:
        assert kind in summary
    assert summary.endswith("1 old-only")


def test_s16_9_11_3_writes_nothing(reference: Path, old: Path) -> None:
    before = _snapshot(reference, old)
    commands.diff(old=str(old))
    assert _snapshot(reference, old) == before


def test_s16_9_11_4_exits_zero_with_differences(reference: Path, old: Path) -> None:
    commands.diff(old=str(old))


def test_s16_9_11_5_config_and_state_are_not_rows(
    reference: Path, old: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commands.diff(old=str(old), json=True)
    rows = _last_json(capsys)["inventory"]
    assert rows
    assert not [r for r in rows if r["path"].startswith(".rn-forge/kiln/")]


def test_s16_9_11_6_a_directory_that_is_not_a_git_repository_is_refused(
    reference: Path, tmp_path: Path
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(AppException, match="inventory.not-a-git-repo"):
        commands.diff(old=str(plain))


def test_s16_9_11_7_old_with_artifact_is_refused(reference: Path, old: Path) -> None:
    with pytest.raises(AppException, match="inventory.artifact-with-old"):
        commands.diff("Taskfile.yml", old=str(old))


def test_s16_9_11_8_old_is_an_option() -> None:
    assert list(inspect.signature(commands.diff).parameters) == [
        "artifact",
        "old",
        "json",
    ]
    assert "--old" in (commands.diff.__doc__ or "")
