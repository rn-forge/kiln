"""S4.4.1 — render and validate every cell.

The one render test runs `kiln new` for real (`uv init` included), as the
nearest `done` stories' tests do, and carries no marker of its own.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from rn_forge.kiln import archetypes

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "golden_matrix.py"

NAMES = [
    "python-app",
    "python-tool",
    "python-lib",
    "python-web-api-backend=fastapi",
    "python-web-app-backend=fastapi-frontend=angular",
]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("golden_matrix", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["golden_matrix"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def matrix() -> ModuleType:
    return _load()


def test_s4_4_1_1_cells(matrix: ModuleType) -> None:
    assert [cell.name for cell in matrix.CELLS] == NAMES
    shipped = archetypes.shipped()
    assert all(cell.archetype in shipped for cell in matrix.CELLS)


def test_s4_4_1_1_gitignored() -> None:
    done = subprocess.run(["git", "check-ignore", "-q", ".goldens"], cwd=ROOT)
    assert done.returncode == 0


def test_s4_4_1_1_render_one_cell(matrix: ModuleType, tmp_path: Path) -> None:
    cell = next(c for c in matrix.CELLS if c.name == "python-app")
    dest = tmp_path / cell.name
    matrix.render_cell(cell, dest, ["uv", "run", "--project", str(ROOT), "kiln"])
    for relative in (".rn-forge/kiln/config.toml", "Taskfile.yml", "pyproject.toml"):
        assert (dest / relative).is_file(), relative


def test_s4_4_1_1_remove_retries_a_directory_not_empty(
    matrix: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cell = tmp_path / "cell"
    (cell / ".uv-cache").mkdir(parents=True)
    real = matrix.shutil.rmtree
    calls: list[Path] = []

    def flaky(path: Path) -> None:
        calls.append(path)
        if len(calls) == 1:
            raise OSError(66, "Directory not empty")
        real(path)

    monkeypatch.setattr(matrix.shutil, "rmtree", flaky)
    monkeypatch.setattr(matrix.time, "sleep", lambda _: None)
    matrix._remove(cell)
    assert not cell.exists()
    assert len(calls) == 2

    def stuck(path: Path) -> None:
        calls.append(path)
        raise OSError(66, "Directory not empty")

    calls.clear()
    monkeypatch.setattr(matrix.shutil, "rmtree", stuck)
    with pytest.raises(OSError, match="Directory not empty"):
        matrix._remove(cell)
    assert len(calls) == 3


def test_s4_4_1_2_ref_dir(matrix: ModuleType, tmp_path: Path) -> None:
    assert matrix.ref_dir("") == "working"
    assert matrix.ref_dir("feature/v1") == "feature-v1"
    assert matrix.ref_dir("main") != matrix.ref_dir("feature/v1")
    assert tmp_path / matrix.ref_dir("main") != tmp_path / matrix.ref_dir("v1")


def test_s4_4_1_3_validate_reports_every_cell(
    matrix: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for name in NAMES:
        (tmp_path / "working" / name).mkdir(parents=True)
    failing = tmp_path / "working" / NAMES[1]
    calls: list[Path] = []

    def fake_run(cmd: list[str], cwd: Path) -> bool:
        calls.append(cwd)
        return cwd != failing

    monkeypatch.setattr(matrix, "run", fake_run)
    assert matrix.validate("", tmp_path) == 1
    out = capsys.readouterr().out
    for name in NAMES:
        assert name in out
    rows = [
        line
        for line in out.splitlines()
        if "|" in line and "FAIL" in line.split("|")[-1]
    ]
    assert len(rows) == 1 and NAMES[1] in rows[0]
    assert tmp_path / "working" / NAMES[-1] in calls


def test_s5_3_2_1_validate_runs_setup_then_validate(
    matrix: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for name in NAMES:
        (tmp_path / "working" / name).mkdir(parents=True)
    calls: list[tuple[list[str], Path]] = []

    def fake_run(cmd: list[str], cwd: Path) -> bool:
        calls.append((cmd, cwd))
        return True

    monkeypatch.setattr(matrix, "run", fake_run)
    assert matrix.validate("", tmp_path) == 0
    task = ["task", "-t", "Taskfile.yml"]
    for name in NAMES:
        cell = tmp_path / "working" / name
        cmds = [cmd for cmd, cwd in calls if cwd == cell]
        assert cmds[0] == [*task, "setup"]
        assert cmds[1] == [*task, "validate"]
    assert ["uv", "sync"] not in [cmd for cmd, _ in calls]
    assert "setup+validate" in capsys.readouterr().out


def test_s4_4_1_3_missing_cell_is_a_fail_row(
    matrix: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(matrix, "run", lambda cmd, cwd: True)
    assert matrix.validate("", tmp_path) == 1
    assert capsys.readouterr().out.count("FAIL") >= len(NAMES)


def test_s4_4_1_task_layout() -> None:
    tasks = yaml.safe_load((ROOT / "tasks" / "self.yml").read_text(encoding="utf-8"))
    for name in ("golden:render", "golden:validate"):
        assert str(tasks["tasks"][name]["desc"]).strip()
        assert not tasks["tasks"][name].get("internal")
    root = yaml.safe_load((ROOT / "Taskfile.yml").read_text(encoding="utf-8"))
    assert root["includes"]["self"] == "tasks/self.yml"


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def test_s4_4_3_1_normalize(matrix: ModuleType) -> None:
    assert matrix.normalize("golden-app", "golden-app", "python-app") == "python-app"
    assert matrix.normalize("golden_app", "golden-app", "python-app") == "python_app"
    # The cell side maps its own name to itself, so an archetype equal to it stays.
    text = 'archetype = "python-app"\n'
    assert matrix.normalize(text, "python-app", "python-app") == text
    for word in ("Generated", "Seeded"):
        assert (
            matrix.normalize(f"# {word} by kiln 1.2.3 from", "golden-app", "python-app")
            == f"# {word} by kiln <version> from"
        )


def _tree(
    root: Path, files: dict[str, str], entries: dict[str, dict[str, str]]
) -> None:
    """Write *files* and a `state.json` whose entries are *entries* (key -> fields)."""
    _write(root, files)
    state = {
        key: {"kind": "managed", "path": key, "begin_marker": None, "end_marker": None}
        | fields
        for key, fields in entries.items()
    }
    _write(root, {".rn-forge/kiln/state.json": json.dumps({"entries": state})})


def _compare(matrix: ModuleType, tmp_path: Path) -> list[str]:
    result: list[str] = matrix.compare_cell(
        tmp_path / "ref", tmp_path / "base", "python-app"
    )
    return result


def test_s4_4_3_2_provenance_version_only_differences(
    matrix: ModuleType, tmp_path: Path
) -> None:
    files = {
        "python-app.code-workspace": {},
        "pyproject.toml": {},
        "config.toml": {},
        "Taskfile.yml": {},
    }
    _tree(
        tmp_path / "base",
        {
            "python-app.code-workspace": "{}\n",
            "pyproject.toml": 'name = "python-app"\nimport python_app\n',
            "config.toml": 'name = "python-app"\narchetype = "python-app"\n',
            "Taskfile.yml": "# Generated by kiln 1.0.0 from x\n",
        },
        files,
    )
    _tree(
        tmp_path / "ref",
        {
            "python-app.code-workspace": "{}\n",
            "pyproject.toml": 'name = "python-app"\nimport python_app\n',
            "config.toml": 'name = "python-app"\narchetype = "python-app"\n',
            "Taskfile.yml": "# Generated by kiln 2.0.0 from x\n",
        },
        files,
    )
    assert _compare(matrix, tmp_path) == []


def test_s4_4_3_3_block_compares_only_its_region(
    matrix: ModuleType, tmp_path: Path
) -> None:
    block = {
        "kind": "block",
        "path": "CLAUDE.md",
        "begin_marker": "<!-- BEGIN -->",
        "end_marker": "<!-- END -->",
    }
    entries = {"CLAUDE.md#kiln": block}

    def claude(before: str, inside: str) -> dict[str, str]:
        return {"CLAUDE.md": f"{before}\n<!-- BEGIN -->\n{inside}\n<!-- END -->\n"}

    _tree(tmp_path / "base", claude("base prose", "same"), entries)
    _tree(tmp_path / "ref", claude("other prose", "same"), entries)
    assert _compare(matrix, tmp_path) == []
    _tree(tmp_path / "ref", claude("other prose", "changed"), entries)
    lines = _compare(matrix, tmp_path)
    assert "differs: CLAUDE.md#kiln" in lines
    assert "--- base/CLAUDE.md#kiln" in lines
    assert "+++ ref/CLAUDE.md#kiln" in lines
    assert "-same" in lines and "+changed" in lines


def test_s4_4_3_4_seeded_and_unlisted_are_ignored(
    matrix: ModuleType, tmp_path: Path
) -> None:
    seeded = {"kind": "seeded"}
    _tree(
        tmp_path / "base",
        {"a.txt": "same\n", "s.md": "one\n", "u.txt": "one\n", "b.txt": "x\n"},
        {"a.txt": {}, "s.md": seeded, "b.txt": {}},
    )
    _tree(
        tmp_path / "ref",
        {"a.txt": "same\n", "s.md": "two\n", "u.txt": "two\n", "r.txt": "y\n"},
        {"a.txt": {}, "s.md": seeded, "r.txt": {}},
    )
    assert _compare(matrix, tmp_path) == [
        "only in base: b.txt",
        "only in ref: r.txt",
    ]


def test_s4_4_3_5_missing_cell_and_compare(
    matrix: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _tree(tmp_path / "there", {"a.txt": "a\n"}, {"a.txt": {}})
    for ref_dir, base_dir, missing in (
        (tmp_path / "nope", tmp_path / "there", tmp_path / "nope"),
        (tmp_path / "there", tmp_path / "nope", tmp_path / "nope"),
    ):
        lines = matrix.compare_cell(ref_dir, base_dir, "python-app")
        assert lines == [f"missing cell: {missing}"]
    assert matrix.compare("base", "ref", tmp_path / "out") == 1
    assert "FAIL" in capsys.readouterr().out
    for ref in ("base", "ref"):
        for cell in matrix.CELLS:
            _tree(
                tmp_path / "out" / ref / cell.name,
                {f"{cell.name}.txt": f"{cell.name}\n"},
                {f"{cell.name}.txt": {}},
            )
    assert matrix.compare("base", "ref", tmp_path / "out") == 0
    assert "FAIL" not in capsys.readouterr().out


def test_s4_4_9_1_compare_pairs_every_cell_of_two_refs(
    matrix: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for ref in ("base", "ref"):
        for cell in matrix.CELLS:
            _tree(
                tmp_path / ref / cell.name,
                {"Taskfile.yml": f"{cell.name}\n"},
                {"Taskfile.yml": {}},
            )
    assert matrix.compare("base", "ref", tmp_path) == 0
    out = capsys.readouterr().out
    rows = [line for line in out.splitlines() if "|" in line and "PASS" in line]
    assert [row.split("|")[0].strip() for row in rows] == NAMES
    assert "FAIL" not in out

    _write(tmp_path / "ref" / "python-tool", {"Taskfile.yml": "changed\n"})
    assert matrix.compare("base", "ref", tmp_path) == 1
    out = capsys.readouterr().out
    assert "differs: Taskfile.yml" in out
    assert out.count("FAIL") == 1


def test_s4_4_9_2_main_requires_a_base(matrix: ModuleType) -> None:
    assert matrix.main(["compare"]) == 2
