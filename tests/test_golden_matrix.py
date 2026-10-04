"""S4.4.1 — render and validate every cell.

The one render test runs `kiln new` for real (`uv init` included), as the
nearest `done` stories' tests do, and carries no marker of its own.
"""

from __future__ import annotations

import importlib.util
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


def test_s4_4_3_2_name_and_version_only_differences(
    matrix: ModuleType, tmp_path: Path
) -> None:
    _write(
        tmp_path / "golden",
        {
            "golden-app.code-workspace": "{}\n",
            "pyproject.toml": 'name = "golden-app"\nimport golden_app\n',
            "config.toml": 'name = "golden-app"\narchetype = "python-app"\n',
            "Taskfile.yml": "# Generated by kiln 1.0.0 from x\n",
        },
    )
    _write(
        tmp_path / "cell",
        {
            "python-app.code-workspace": "{}\n",
            "pyproject.toml": 'name = "python-app"\nimport python_app\n',
            "config.toml": 'name = "python-app"\narchetype = "python-app"\n',
            "Taskfile.yml": "# Generated by kiln 2.0.0 from x\n",
        },
    )
    lines = matrix.compare_cell(
        tmp_path / "cell", tmp_path / "golden", "python-app", "golden-app"
    )
    assert lines == []


def test_s4_4_3_3_differing_and_unpaired(matrix: ModuleType, tmp_path: Path) -> None:
    _write(tmp_path / "golden", {"a.txt": "one\ntwo\n", "g.txt": "x\n"})
    _write(tmp_path / "cell", {"a.txt": "one\n2\n", "c.txt": "y\n"})
    lines = matrix.compare_cell(
        tmp_path / "cell", tmp_path / "golden", "python-app", "golden-app"
    )
    assert "differs: a.txt" in lines
    assert "only in golden: g.txt" in lines
    assert "only in cell: c.txt" in lines
    after = lines[lines.index("differs: a.txt") + 1 :]
    assert "--- golden/a.txt" in after and "+++ cell/a.txt" in after
    assert "-two" in after and "+2" in after


def test_s4_4_3_4_skipped_paths(matrix: ModuleType, tmp_path: Path) -> None:
    _write(tmp_path / "golden", {"a.txt": "same\n"})
    _write(
        tmp_path / "cell",
        {
            "a.txt": "same\n",
            ".venv/lib/x.py": "x\n",
            ".docs-site/index.html": "x\n",
            "pkg/__pycache__/m.pyc": "x\n",
            "uv.lock": "x\n",
            ".coverage": "x\n",
            ".rn-forge/kiln/state.json": "{}\n",
            ".rn-forge/kiln/state.lock": "x\n",
            ".rn-forge/kiln/rendered/README.md": "x\n",
            ".rn-forge/kiln/backups/1/README.md": "x\n",
        },
    )
    lines = matrix.compare_cell(
        tmp_path / "cell", tmp_path / "golden", "python-app", "golden-app"
    )
    assert lines == []


def test_s4_4_3_5_missing_cell_and_compare(
    matrix: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    golden = tmp_path / "goldens"
    for cell, golden_name in matrix.COMPARED:
        _write(golden / cell, {f"{golden_name}.txt": f"{golden_name}\n"})
    lines = matrix.compare_cell(
        tmp_path / "nope", golden / "python-app", "python-app", "golden-app"
    )
    assert lines == [f"missing cell: {tmp_path / 'nope'}"]
    assert matrix.compare("", tmp_path / "out", golden) == 1
    assert "FAIL" in capsys.readouterr().out
    for cell, _ in matrix.COMPARED:
        _write(tmp_path / "out" / "working" / cell, {f"{cell}.txt": f"{cell}\n"})
    assert matrix.compare("", tmp_path / "out", golden) == 0
    assert "FAIL" not in capsys.readouterr().out
