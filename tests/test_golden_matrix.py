"""S4.4.1 — render and validate every cell.

The one render test runs `kiln new` for real (`uv init` included), as the
nearest `done` stories' tests do, and carries no marker of its own.
"""

from __future__ import annotations

import difflib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from rn_forge.commons.fs.documents import YamlUtils

from rn_forge.kiln import archetypes

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "golden_matrix.py"

NAMES = [
    "python-app",
    "python-tool",
    "python-lib",
    "python-web-api-backend=fastapi",
    "python-web-app-backend=fastapi-frontend=angular",
    "node-lib",
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
    tasks = YamlUtils.load((ROOT / "tasks" / "self.yml").read_text(encoding="utf-8"))
    for name in ("golden:render", "golden:validate"):
        assert str(tasks["tasks"][name]["desc"]).strip()
        assert not tasks["tasks"][name].get("internal")
    root = YamlUtils.load((ROOT / "Taskfile.yml").read_text(encoding="utf-8"))
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


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def test_s9_1_12_1_ngkit_files_skip_check_template(matrix: ModuleType) -> None:
    assert len(matrix.NGKIT_FILES) == 10
    assert not any("check-template" in name for name in matrix.NGKIT_FILES)
    assert matrix.NGKIT_REF == "0c2cd2a"


def test_s9_1_12_2_ngkit_diff_compares_the_ref_with_the_cell(
    matrix: ModuleType, tmp_path: Path
) -> None:
    checkout, cell = tmp_path / "ngkit", tmp_path / "cell"
    files = {name: f"{name}\n" for name in matrix.NGKIT_FILES}
    _write(checkout, files)
    _git(checkout, "init", "-q")
    _git(checkout, "add", ".")
    _git(checkout, "commit", "-qm", "x")
    _write(cell, {**files, "sonar-project.properties": "changed\n"})
    lines = matrix.ngkit_diff(checkout, cell, "HEAD")
    assert [line for line in lines if line.startswith("@@")] == ["@@ -1 +1 @@"]
    assert "+changed" in lines
    with pytest.raises(RuntimeError):
        matrix.ngkit_diff(checkout, cell, "no-such-ref")


def _ngkit_repo(matrix: ModuleType, tmp_path: Path) -> tuple[Path, Path]:
    checkout, cell = tmp_path / "ngkit", tmp_path / "cell"
    files = {name: f"{name}\nsame\n" for name in matrix.NGKIT_FILES}
    _write(checkout, files)
    _git(checkout, "init", "-q")
    _git(checkout, "add", ".")
    _git(checkout, "commit", "-qm", "x")
    _write(cell, {**files, "sonar-project.properties": "changed\n"})
    (cell / matrix.NGKIT_FILES[0]).unlink()
    return checkout, cell


def test_s9_3_8_1_review_writes_both_folders(
    matrix: ModuleType, tmp_path: Path
) -> None:
    checkout, cell = _ngkit_repo(matrix, tmp_path)
    review = tmp_path / "review"
    matrix.ngkit_review(checkout, cell, review, "HEAD")
    for name in matrix.NGKIT_FILES:
        assert (review / "before-ngkit" / name).read_text() == f"{name}\nsame\n"
    assert (review / "after-kiln" / "sonar-project.properties").read_text() == (
        "changed\n"
    )
    assert (review / "after-kiln" / matrix.NGKIT_FILES[0]).read_text() == ""


def test_s9_3_8_2_review_folders_rebuild_the_diff(
    matrix: ModuleType, tmp_path: Path
) -> None:
    checkout, cell = _ngkit_repo(matrix, tmp_path)
    review = tmp_path / "review"
    matrix.ngkit_review(checkout, cell, review, "HEAD")
    rebuilt: list[str] = []
    for name in matrix.NGKIT_FILES:
        before = (review / "before-ngkit" / name).read_text().splitlines()
        after = (review / "after-kiln" / name).read_text().splitlines()
        rebuilt += difflib.unified_diff(
            before, after, fromfile=f"ngkit/{name}", tofile=f"kiln/{name}", lineterm=""
        )
    assert rebuilt
    assert rebuilt == matrix.ngkit_diff(checkout, cell, "HEAD")


def test_s9_3_8_3_review_replaces_the_folder(
    matrix: ModuleType, tmp_path: Path
) -> None:
    checkout, cell = _ngkit_repo(matrix, tmp_path)
    review = tmp_path / "review"
    matrix.ngkit_review(checkout, cell, review, "HEAD")
    stale = review / "before-ngkit" / "stale.txt"
    stale.write_text("x", encoding="utf-8")
    matrix.ngkit_review(checkout, cell, review, "HEAD")
    assert not stale.exists()
    assert (review / "before-ngkit" / matrix.NGKIT_FILES[1]).is_file()


def test_s9_3_8_4_ngkit_leaves_the_review_folders(
    matrix: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout, cell = _ngkit_repo(matrix, tmp_path)
    _git(checkout, "tag", matrix.NGKIT_REF)

    def render(_cell: object, dest: Path, _cmd: list[str]) -> None:
        _write(dest, {p.name: p.read_text() for p in cell.iterdir() if p.is_file()})
        for name in matrix.NGKIT_FILES:
            if (cell / name).is_file():
                _write(dest, {name: (cell / name).read_text()})

    monkeypatch.setattr(matrix, "render_cell", render)
    out_root = tmp_path / "out"
    assert matrix.ngkit(checkout, out_root) == 0
    review = out_root / "scratch" / "ngkit-review"
    assert (review / "before-ngkit").is_dir()
    assert (review / "after-kiln").is_dir()
    assert (out_root / "ngkit.diff").is_file()


def test_s9_1_12_3_main_requires_a_checkout(matrix: ModuleType) -> None:
    assert matrix.main(["ngkit"]) == 2


def test_s9_1_12_4_task_requires_ngkit() -> None:
    tasks = YamlUtils.load((ROOT / "tasks" / "self.yml").read_text(encoding="utf-8"))
    task = tasks["tasks"]["golden:ngkit"]
    assert str(task["desc"]).strip()
    assert task["requires"]["vars"] == ["NGKIT"]


PARITY = (
    "nx.json",
    "package.json",
    "pnpm-workspace.yaml",
    "eslint.config.mjs",
    "tsconfig.base.json",
    ".nvmrc",
    ".gitignore",
    ".vscode/extensions.json",
    "tasks/node.yml",
)


def _parity_files(**changes: str | None) -> dict[str, str]:
    """Nine parity files with nested JSON and YAML; *changes* replaces or (None) drops by name."""
    files = {
        "nx.json": json.dumps({"a": {"b": [1, {"c": 2}]}}),
        "package.json": json.dumps(
            {"dependencies": {"rxjs": "1"}, "devDependencies": {"nx": "1"}}
        ),
        "pnpm-workspace.yaml": "packages:\n  - libs/*\nsettings:\n  deep:\n    key: 1\n",
        "eslint.config.mjs": "export default [];\n",
        "tsconfig.base.json": json.dumps({"compilerOptions": {"paths": {"x": ["y"]}}}),
        ".nvmrc": "24\n",
        ".gitignore": ".nx\n",
        ".vscode/extensions.json": json.dumps({"recommendations": ["a"]}),
        "tasks/node.yml": "version: '3'\ntasks:\n  a:\n    cmds: [b]\n",
    }
    files.update({k: v for k, v in changes.items() if v is not None})
    return {k: v for k, v in files.items() if changes.get(k, "") is not None}


def _package(deps: dict[str, str], dev: dict[str, str] | None = None) -> str:
    return json.dumps(
        {"dependencies": deps, "devDependencies": dev or {"nx": "1"}}, indent=4
    )


def _cells(
    tmp_path: Path, lib: dict[str, str], web: dict[str, str]
) -> tuple[Path, Path]:
    _write(tmp_path / "lib", lib)
    _write(tmp_path / "web", web)
    return tmp_path / "lib", tmp_path / "web"


def test_s9_2_10_1_parity_files_are_the_nine(matrix: ModuleType) -> None:
    assert matrix.PARITY_FILES == PARITY


def test_s9_2_10_1_identical_cells_report_nothing(
    matrix: ModuleType, tmp_path: Path
) -> None:
    lib, web = _cells(tmp_path, _parity_files(), _parity_files())
    assert matrix.parity_cells(lib, web) == []


def test_s9_2_10_1_json_and_yaml_may_differ_in_layout_only(
    matrix: ModuleType, tmp_path: Path
) -> None:
    web_files = _parity_files(
        **{
            "nx.json": json.dumps({"a": {"b": [1, {"c": 2}]}}, indent=8),
            "pnpm-workspace.yaml": (
                "settings: {deep: {key: 1}}\npackages: ['libs/*']\n"
            ),
            "tsconfig.base.json": json.dumps(
                {"compilerOptions": {"paths": {"x": ["y"]}}}, indent=1
            ),
        }
    )
    lib, web = _cells(tmp_path, _parity_files(), web_files)
    assert matrix.parity_cells(lib, web) == []


@pytest.mark.parametrize("name", ["eslint.config.mjs", ".nvmrc", ".gitignore"])
def test_s9_2_10_1_other_files_compare_as_bytes(
    matrix: ModuleType, tmp_path: Path, name: str
) -> None:
    lib, web = _cells(tmp_path, _parity_files(), _parity_files(**{name: "x\n"}))
    assert [line for line in matrix.parity_cells(lib, web) if name in line]


def test_s16_7_6_6_tasks_node_yml_compares_parsed(
    matrix: ModuleType, tmp_path: Path
) -> None:
    layout = "version: '3'\ntasks:\n  a:\n    cmds:\n      - b\n"
    lib, web = _cells(
        tmp_path, _parity_files(), _parity_files(**{"tasks/node.yml": layout})
    )
    assert matrix.parity_cells(lib, web) == []
    changed = "version: '3'\ntasks:\n  a:\n    cmds:\n      - c\n"
    lib, web = _cells(
        tmp_path / "b", _parity_files(), _parity_files(**{"tasks/node.yml": changed})
    )
    lines = matrix.parity_cells(lib, web)
    assert len(lines) == 1 and "tasks/node.yml" in lines[0]


def _node_yml(*extra: str) -> str:
    return "version: '3'\ntasks:\n  a:\n    cmds: [b]\n" + "".join(
        f"  {name}:\n    cmds: [x]\n" for name in extra
    )


def test_s16_7_6_4_parity_allows_the_lib_version_task(
    matrix: ModuleType, tmp_path: Path
) -> None:
    assert matrix.LIB_ONLY_TASKS == ("version",)
    lib, web = _cells(
        tmp_path,
        _parity_files(**{"tasks/node.yml": _node_yml("version")}),
        _parity_files(),
    )
    assert matrix.parity_cells(lib, web) == []
    lib, web = _cells(
        tmp_path / "web",
        _parity_files(),
        _parity_files(**{"tasks/node.yml": _node_yml("version")}),
    )
    assert [line for line in matrix.parity_cells(lib, web) if "tasks/node.yml" in line]
    lib, web = _cells(
        tmp_path / "other",
        _parity_files(**{"tasks/node.yml": _node_yml("publish")}),
        _parity_files(),
    )
    assert [line for line in matrix.parity_cells(lib, web) if "tasks/node.yml" in line]


GITIGNORE_GROUPS = (
    "# Python tool caches\n.pytest_cache/\n.ruff_cache/\n\n"
    "# Coverage output\n.coverage\nhtmlcov/\n\n"
)


def test_s16_7_6_5_parity_allows_the_web_python_groups(
    matrix: ModuleType, tmp_path: Path
) -> None:
    assert matrix.WEB_ONLY_GITIGNORE_GROUPS == (
        "# Python tool caches",
        "# Coverage output",
    )
    base = "# Nx\n.nx\n\n"
    web_text = "# Nx\n.nx\n\n" + GITIGNORE_GROUPS + "# End\ndist\n"
    lib_text = base + "# End\ndist\n"
    lib, web = _cells(
        tmp_path,
        _parity_files(**{".gitignore": lib_text}),
        _parity_files(**{".gitignore": web_text}),
    )
    assert matrix.parity_cells(lib, web) == []
    lib, web = _cells(
        tmp_path / "swap",
        _parity_files(**{".gitignore": web_text}),
        _parity_files(**{".gitignore": lib_text}),
    )
    assert [line for line in matrix.parity_cells(lib, web) if ".gitignore" in line]
    lib, web = _cells(
        tmp_path / "extra",
        _parity_files(**{".gitignore": lib_text}),
        _parity_files(**{".gitignore": web_text + "extra\n"}),
    )
    assert [line for line in matrix.parity_cells(lib, web) if ".gitignore" in line]


@pytest.mark.parametrize(
    ("name", "changed"),
    [
        ("nx.json", json.dumps({"a": {"b": [1, {"c": 3}]}})),
        (
            "tsconfig.base.json",
            json.dumps({"compilerOptions": {"paths": {"x": ["z"]}}}),
        ),
        (".vscode/extensions.json", json.dumps({"recommendations": ["b"]})),
        (
            "pnpm-workspace.yaml",
            "packages:\n  - libs/*\nsettings:\n  deep:\n    key: 2\n",
        ),
        (".nvmrc", "22\n"),
        (".gitignore", ".nx\n.venv\n"),
    ],
)
def test_s9_2_10_2_a_value_difference_names_the_path(
    matrix: ModuleType, tmp_path: Path, name: str, changed: str
) -> None:
    lib, web = _cells(tmp_path, _parity_files(), _parity_files(**{name: changed}))
    lines = matrix.parity_cells(lib, web)
    assert len(lines) == 1 and name in lines[0]


@pytest.mark.parametrize("name", PARITY)
def test_s9_2_10_2_a_file_missing_from_the_web_side_is_reported(
    matrix: ModuleType, tmp_path: Path, name: str
) -> None:
    lib, web = _cells(tmp_path, _parity_files(), _parity_files(**{name: None}))
    lines = matrix.parity_cells(lib, web)
    assert len(lines) == 1 and name in lines[0] and "web" in lines[0]


@pytest.mark.parametrize("name", PARITY)
def test_s9_2_10_2_a_file_missing_from_the_lib_side_is_reported(
    matrix: ModuleType, tmp_path: Path, name: str
) -> None:
    lib, web = _cells(tmp_path, _parity_files(**{name: None}), _parity_files())
    lines = matrix.parity_cells(lib, web)
    assert len(lines) == 1 and name in lines[0] and "lib" in lines[0]


def test_s9_2_10_2_a_file_missing_from_both_sides_is_reported(
    matrix: ModuleType, tmp_path: Path
) -> None:
    lib, web = _cells(
        tmp_path, _parity_files(**{".nvmrc": None}), _parity_files(**{".nvmrc": None})
    )
    assert [line for line in matrix.parity_cells(lib, web) if ".nvmrc" in line]


def test_s9_2_10_3_the_web_side_may_add_rn_forge_ng_to_dependencies(
    matrix: ModuleType, tmp_path: Path
) -> None:
    lib = _parity_files(**{"package.json": _package({"rxjs": "1"})})
    web = _parity_files(
        **{"package.json": _package({"rxjs": "1", "@rn-forge/ng": "file:x.tgz"})}
    )
    lib_dir, web_dir = _cells(tmp_path, lib, web)
    assert matrix.parity_cells(lib_dir, web_dir) == []


@pytest.mark.parametrize("section", ["dependencies", "devDependencies"])
def test_s9_2_10_3_any_other_web_dependency_is_a_difference(
    matrix: ModuleType, tmp_path: Path, section: str
) -> None:
    deps, dev = {"rxjs": "1", "@rn-forge/ng": "x"}, {"nx": "1"}
    (deps if section == "dependencies" else dev)["left-pad"] = "1"
    lib = _parity_files(**{"package.json": _package({"rxjs": "1"})})
    web = _parity_files(**{"package.json": _package(deps, dev)})
    lib_dir, web_dir = _cells(tmp_path, lib, web)
    lines = matrix.parity_cells(lib_dir, web_dir)
    assert len(lines) == 1 and "package.json" in lines[0]


def test_s9_2_10_3_rn_forge_ng_in_web_dev_dependencies_is_a_difference(
    matrix: ModuleType, tmp_path: Path
) -> None:
    lib = _parity_files(**{"package.json": _package({"rxjs": "1"})})
    web = _parity_files(
        **{"package.json": _package({"rxjs": "1"}, {"nx": "1", "@rn-forge/ng": "x"})}
    )
    lib_dir, web_dir = _cells(tmp_path, lib, web)
    assert matrix.parity_cells(lib_dir, web_dir) != []


def test_s9_2_10_3_rn_forge_ng_on_the_lib_side_is_a_difference(
    matrix: ModuleType, tmp_path: Path
) -> None:
    ng = _package({"rxjs": "1", "@rn-forge/ng": "x"})
    lib_dir, web_dir = _cells(
        tmp_path,
        _parity_files(**{"package.json": ng}),
        _parity_files(**{"package.json": ng}),
    )
    assert matrix.parity_cells(lib_dir, web_dir) != []
    # Lib-only, with the web side lacking it too, differs as well.
    lib_only = _parity_files(**{"package.json": ng})
    web_none = _parity_files(**{"package.json": _package({"rxjs": "1"})})
    lib_dir, web_dir = _cells(tmp_path / "b", lib_only, web_none)
    assert matrix.parity_cells(lib_dir, web_dir) != []


def test_s9_2_10_3_other_package_json_keys_still_compare(
    matrix: ModuleType, tmp_path: Path
) -> None:
    lib = _parity_files(**{"package.json": _package({"rxjs": "1"})})
    web = json.loads(_package({"rxjs": "1", "@rn-forge/ng": "x"}))
    web["packageManager"] = "pnpm@1"
    lib_dir, web_dir = _cells(
        tmp_path, lib, _parity_files(**{"package.json": json.dumps(web)})
    )
    assert len(matrix.parity_cells(lib_dir, web_dir)) == 1


def _matrix_goldens(
    matrix: ModuleType,
    root: Path,
    web_files: dict[str, str],
    python: dict[str, str] | None = None,
) -> None:
    python = _py_cell() if python is None else python
    for cell in matrix.CELLS:
        if cell.archetype == "node-lib":
            _write(root / "working" / cell.name, _parity_files())
        elif cell.archetype == "python-web-app":
            _write(root / "working" / cell.name, {**python, **web_files})
        else:
            _write(root / "working" / cell.name, python)


def test_s9_2_10_4_main_parity_passes_when_the_cells_match(
    matrix: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _matrix_goldens(matrix, tmp_path, _parity_files())
    monkeypatch.setattr(matrix, "GOLDENS", tmp_path)
    assert matrix.main(["parity"]) == 0
    assert capsys.readouterr().err == ""


def test_s9_2_10_4_main_parity_prints_each_line_and_exits_1(
    matrix: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _matrix_goldens(matrix, tmp_path, _parity_files(**{".nvmrc": "22\n"}))
    monkeypatch.setattr(matrix, "GOLDENS", tmp_path)
    assert matrix.main(["parity"]) == 1
    assert ".nvmrc" in capsys.readouterr().out


def test_s9_2_10_4_main_parity_errors_when_a_cell_is_not_rendered(
    matrix: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(matrix, "GOLDENS", tmp_path)
    assert matrix.main(["parity"]) == 1
    assert "golden:render" in capsys.readouterr().err
    # One cell present, the other absent: still an error, never success.
    lib_name = next(c.name for c in matrix.CELLS if c.archetype == "node-lib")
    _write(tmp_path / "working" / lib_name, _parity_files())
    assert matrix.main(["parity"]) == 1


def test_s9_2_10_4_main_parity_takes_no_argument(matrix: ModuleType) -> None:
    assert matrix.main(["parity", "extra"]) == 2


def test_s9_2_10_5_task_golden_parity_calls_the_command() -> None:
    tasks = YamlUtils.load((ROOT / "tasks" / "self.yml").read_text(encoding="utf-8"))
    task = tasks["tasks"]["golden:parity"]
    assert str(task["desc"]).strip()
    assert task["cmds"] == ["uv run python scripts/golden_matrix.py parity"]


def test_s9_2_10_6_the_policy_names_the_parity_check() -> None:
    page = (ROOT / "docs/specs/epics/E4-generator/F4.4-render-matrix.md").read_text(
        encoding="utf-8"
    )
    policy = page.split("## Template review policy")[1].split("\n## ")[0]
    assert "self:golden:parity" in policy


PY_CELLS = NAMES[:5]
PY_TASKS = (
    "install lint lint:imports lint:audit lint:licenses format typecheck test"
    " test:coverage build version"
).split()
PY_DEV = '"actionlint-py>=1.7", "pyright>=1.1", "pytest>=9.1", "ruff>=0.16"'


def _py_cell(
    *,
    tasks: list[str] | None = None,
    glob: str = "tests/*",
    pyright: str = "",
    pytest_extra: str = "",
    dev: str = PY_DEV,
) -> dict[str, str]:
    names = PY_TASKS if tasks is None else tasks
    task_yml = "version: '3'\ntasks:\n" + "".join(
        f"  {n}:\n    cmds: [echo]\n" for n in names
    )
    pyproject = (
        '[project]\nname = "x"\n\n'
        "[tool.pyright]\n"
        f'typeCheckingMode = "strict"\n{pyright}\n'
        "[tool.pytest.ini_options]\n"
        f'addopts = "-ra"\n{pytest_extra}\n'
        f'[tool.ruff.lint.per-file-ignores]\n"{glob}" = ["ANN", "S101"]\n\n'
        f"[dependency-groups]\ndev = [{dev}]\n"
    )
    return {"tasks/python.yml": task_yml, "pyproject.toml": pyproject}


def _py_cells(tmp_path: Path, **per_cell: dict[str, str]) -> dict[str, Path]:
    cells: dict[str, Path] = {}
    for name in PY_CELLS:
        _write(tmp_path / name, per_cell.get(name, _py_cell()))
        cells[name] = tmp_path / name
    return cells


LIB_EXTRAS = {
    "pyright": 'include = ["packages"]\n',
    "pytest_extra": 'testpaths = ["packages"]\n',
    "glob": "**/tests/*",
    "dev": '{ include-group = "workspace" }, "coverage[toml]>=7.9", ' + PY_DEV,
}


def test_s16_7_7_1_identical_cells_report_nothing(
    matrix: ModuleType, tmp_path: Path
) -> None:
    assert matrix.python_parity_cells(_py_cells(tmp_path)) == []


def test_s16_7_7_2_a_pyright_value_difference_names_cell_and_key(
    matrix: ModuleType, tmp_path: Path
) -> None:
    cells = _py_cells(
        tmp_path, **{"python-app": _py_cell(pyright="reportFoo = true\n")}
    )
    assert matrix.python_parity_cells(cells) == ["python-app: tool.pyright differs"]


def test_s16_7_7_3_a_missing_or_extra_task_names_cell_and_task(
    matrix: ModuleType, tmp_path: Path
) -> None:
    short = [t for t in PY_TASKS if t != "lint:audit"]
    cells = _py_cells(
        tmp_path,
        **{
            "python-app": _py_cell(tasks=short),
            "python-lib": _py_cell(tasks=[*PY_TASKS, "deploy"]),
        },
    )
    assert matrix.python_parity_cells(cells) == [
        "python-app: task lint:audit missing",
        "python-lib: task deploy extra",
    ]


def test_s16_7_7_4_python_lib_extras_are_allowed_only_there(
    matrix: ModuleType, tmp_path: Path
) -> None:
    extras = {**LIB_EXTRAS, "glob": "tests/*"}
    assert (
        matrix.python_parity_cells(
            _py_cells(tmp_path / "a", **{"python-lib": _py_cell(**LIB_EXTRAS)})
        )
        == []
    )
    other = _py_cells(tmp_path / "b", **{"python-app": _py_cell(**extras)})
    assert matrix.python_parity_cells(other) == [
        "python-app: tool.pyright differs",
        "python-app: tool.pytest differs",
        "python-app: dependency-groups.dev differs",
    ]
    # A lib with another extra dev entry is still reported.
    odd = {**LIB_EXTRAS, "dev": LIB_EXTRAS["dev"] + ', "mypy"'}
    cells = _py_cells(tmp_path / "c", **{"python-lib": _py_cell(**odd)})
    assert matrix.python_parity_cells(cells) == [
        "python-lib: dependency-groups.dev differs"
    ]


def test_s16_7_7_5_only_the_tests_glob_spelling_may_differ_in_ruff(
    matrix: ModuleType, tmp_path: Path
) -> None:
    cells = _py_cells(tmp_path / "a", **{"python-app": _py_cell(glob="**/tests/*")})
    assert matrix.python_parity_cells(cells) == []
    cells = _py_cells(tmp_path / "b", **{"python-app": _py_cell(glob="src/*")})
    assert matrix.python_parity_cells(cells) == ["python-app: tool.ruff differs"]


def test_s16_7_7_6_a_missing_file_or_table_is_a_line(
    matrix: ModuleType, tmp_path: Path
) -> None:
    cells = _py_cells(tmp_path)
    (cells["python-app"] / "tasks" / "python.yml").unlink()
    (cells["python-lib"] / "pyproject.toml").write_text("[project]\nname='x'\n")
    lines = matrix.python_parity_cells(cells)
    assert "python-app: tasks/python.yml missing" in lines
    assert "python-lib: tool.ruff differs" in lines
    assert "python-lib: dependency-groups.dev differs" in lines


def test_s16_7_7_6_main_parity_runs_both_checks(
    matrix: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(matrix, "GOLDENS", tmp_path)
    _matrix_goldens(matrix, tmp_path, _parity_files())
    assert matrix.main(["parity"]) == 0
    # A Python difference alone fails.
    app = next(c.name for c in matrix.CELLS if c.archetype == "python-app")
    _write(tmp_path / "working" / app, _py_cell(pyright="reportFoo = true\n"))
    assert matrix.main(["parity"]) == 1
    assert f"{app}: tool.pyright differs" in capsys.readouterr().out
    # A Node difference alone fails.
    _matrix_goldens(matrix, tmp_path, {**_parity_files(), ".nvmrc": "22\n"})
    assert matrix.main(["parity"]) == 1
    assert ".nvmrc" in capsys.readouterr().out


def test_s16_7_7_6_main_parity_errors_when_a_python_cell_is_missing(
    matrix: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(matrix, "GOLDENS", tmp_path)
    _matrix_goldens(matrix, tmp_path, _parity_files())
    tool = next(c.name for c in matrix.CELLS if c.archetype == "python-tool")
    shutil.rmtree(tmp_path / "working" / tool)
    capsys.readouterr()
    assert matrix.main(["parity"]) == 1
    assert (
        f"missing cell: {tmp_path / 'working' / tool} (run task self:golden:render)"
        in capsys.readouterr().err
    )


def test_s16_7_7_7_the_policy_names_the_python_check() -> None:
    page = (ROOT / "docs/specs/epics/E4-generator/F4.4-render-matrix.md").read_text(
        encoding="utf-8"
    )
    policy = page.split("## Template review policy")[1].split("\n## ")[0]
    assert "python-tool" in policy
    assert "tasks/python.yml" in policy


def _named(name: str) -> str:
    return json.dumps(
        {"name": name, "dependencies": {"rxjs": "1"}, "devDependencies": {"nx": "1"}}
    )


def test_s16_7_8_5_parity_ignores_the_root_name_but_checks_it(
    matrix: ModuleType, tmp_path: Path
) -> None:
    lib = _parity_files(**{"package.json": _named("@lib/source")})
    web = _parity_files(**{"package.json": _named("@web/source")})
    lib_dir, web_dir = _cells(tmp_path / "ok", lib, web)
    assert matrix.parity_cells(lib_dir, web_dir) == []

    bad_lib = _parity_files(**{"package.json": _named("@workspace/source")})
    lib_dir, web_dir = _cells(tmp_path / "bad_lib", bad_lib, web)
    assert matrix.parity_cells(lib_dir, web_dir) == ["differs: package.json name (lib)"]

    bad_web = _parity_files(**{"package.json": _named("@workspace/source")})
    lib_dir, web_dir = _cells(tmp_path / "bad_web", lib, bad_web)
    assert matrix.parity_cells(lib_dir, web_dir) == ["differs: package.json name (web)"]

    # `=` in a cell directory name is read as `-`.
    root = tmp_path / "eq"
    _write(root / "a=b", _parity_files(**{"package.json": _named("@a-b/source")}))
    _write(root / "web", web)
    assert matrix.parity_cells(root / "a=b", root / "web") == []

    # No name at all is not reported for it.
    lib_dir, web_dir = _cells(tmp_path / "none", _parity_files(), _parity_files())
    assert matrix.parity_cells(lib_dir, web_dir) == []
