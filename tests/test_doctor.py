"""S4.6.1 — `kiln doctor`: one report across modules. S4.6.5 — ownership."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import checks, commands, doctor
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.core.checks.generated import digest

TESTS = Path(__file__).parent
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


def _load(relative: str) -> ModuleType:
    """Import a sibling test file by path (the suite has no test packages)."""
    path = TESTS / relative
    name = "_doctor_helper_" + path.stem
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _run_one(root: Path, name: str) -> list[Finding]:
    return next(c for c in checks.CHECKS if c.name == name).run(
        KilnConfig.load(root), root
    )


@pytest.fixture
def copy(
    tmp_path: Path, rendered: Callable[[str], Path], monkeypatch: pytest.MonkeyPatch
) -> Path:
    """A writable copy of the rendered `python-app` repo."""
    root = tmp_path / "copy"
    shutil.copytree(rendered("python-app"), root, ignore=_IGNORE)
    monkeypatch.chdir(root)
    yield root
    console.set_mode(OutputMode.PLAIN)


def _edit(root: Path, relative: str, change: Callable[[str], str]) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    edited = change(text)
    assert edited != text, relative
    path.write_text(edited, encoding="utf-8")


def _reseed(root: Path, relative: str) -> None:
    """Record *relative*'s current content as its committed hash, so only the
    check under test sees the edit."""
    state_path = root / ".rn-forge" / "kiln" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    text = (root / relative).read_text(encoding="utf-8", newline="")
    for entry in state["entries"].values():
        if entry["path"] == relative and entry["kind"] == "managed":
            entry["content_hash"] = digest(text)
    state_path.write_text(json.dumps(state), encoding="utf-8")


def _break_generated(root: Path) -> None:
    _edit(root, "Taskfile.yml", lambda text: text + "\n# edit\n")


def _break_deps(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        _load("modules/python/checks/test_rn_forge_deps.py").MISSING_REQUIRED,
        encoding="utf-8",
    )


def _break_layout(root: Path) -> None:
    _edit(
        root,
        "Taskfile.yml",
        lambda text: text + "  stray:\n    desc: Stray\n    cmds: [uv build]\n",
    )
    _reseed(root, "Taskfile.yml")


def _break_entrypoint(root: Path) -> None:
    _edit(
        root,
        ".github/workflows/ci.yml",
        lambda text: text.replace("run: task validate", "run: uv sync", 1),
    )
    _reseed(root, ".github/workflows/ci.yml")


def _break_pins(root: Path) -> None:
    _edit(
        root,
        ".github/workflows/ci.yml",
        lambda text: re.sub(r"(uses: [^@\s]+)@[0-9a-f]{40}", r"\1@v4", text, count=1),
    )
    _reseed(root, ".github/workflows/ci.yml")


def _break_hooks(root: Path) -> None:
    _edit(
        root,
        ".rn-forge/kiln/config.toml",
        lambda text: text.replace(
            "setup = []", 'setup = ["./.github/actions/ghost"]', 1
        ),
    )


def _break_structure(root: Path) -> None:
    _edit(root, "docs/_areas.yml", lambda text: text + "  - key: ghost\n")


def _break_derived(root: Path) -> None:
    (root / "docs" / "guides" / "brand-new.md").write_text("# New\n", encoding="utf-8")


def _break_site(root: Path) -> None:
    _edit(root, "docs/index.md", lambda text: text + "\n[x](missing.md)\n")


def _break_quality(root: Path) -> None:
    _break_site(root)
    _edit(
        root,
        "pyproject.toml",
        lambda text: re.sub(r'\s*"rn-forge-commons[^"]*",?', "", text),
    )


BREAKS: dict[str, tuple[Callable[[Path], None], str]] = {
    "generated": (_break_generated, "artifact."),
    "rn-forge-deps": (_break_deps, "deps."),
    "task-layout": (_break_layout, "taskgraph."),
    "ci-entrypoint": (_break_entrypoint, "ci.entrypoint"),
    "ci-pins": (_break_pins, "ci.unpinned"),
    "ci-hooks": (_break_hooks, "ci.hook-missing"),
    "docs-structure": (_break_structure, "docs."),
    "docs-generate": (_break_derived, "docs.nav-stale"),
    "docs-site": (_break_site, "docs.broken-link"),
}


# The three docs checks read one tree and overlap: a broken link or a page
# outside the nav is reported by more than one of them.
DOCS = frozenset({"docs-structure", "docs-generate", "docs-site"})
QUALITY = frozenset({"rn-forge-deps", "docs-structure", "docs-site"})


def test_s4_6_1_1_every_registered_check_has_a_break() -> None:
    assert set(BREAKS) == set(checks.names())


@pytest.mark.parametrize("name", checks.names())
def test_s4_6_1_1_each_check_reports_only_its_own_code(copy: Path, name: str) -> None:
    breaker, prefix = BREAKS[name]
    assert checks.run(copy) == []
    breaker(copy)

    own = _run_one(copy, name)
    assert any(f.is_error and f.code.startswith(prefix) for f in own), [
        str(f) for f in own
    ]
    if name in QUALITY:
        # an ownership run skips a quality check
        assert checks.run(copy, scope="ownership") == []
        assert any(f.is_error and f.code.startswith(prefix) for f in checks.run(copy))

    for other in checks.names():
        if other != name and not (name in DOCS and other in DOCS):
            errors = [f for f in _run_one(copy, other) if f.is_error]
            assert errors == [], (other, [str(f) for f in errors])


def test_s4_6_1_2_full_on_a_fresh_repo_exits_0(copy: Path) -> None:
    assert doctor.full(copy) == []
    commands.doctor([copy], full=True)


def test_s4_6_1_2_full_reports_a_stale_artifact(copy: Path) -> None:
    _edit(
        copy,
        ".rn-forge/kiln/config.toml",
        lambda text: text.replace("sonar = true", "sonar = false"),
    )
    stale = [f for f in doctor.full(copy) if f.code == "artifact.stale"]
    changed = {c.path for c in cycle.plan(copy).changes if c.action.value == "update"}
    assert changed
    assert changed <= {f.path for f in stale}
    with pytest.raises(AppException):
        commands.doctor([copy], full=True)


def test_s4_6_1_2_warnings_alone_exit_0(
    copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def warn(config: object, root: Path) -> list[Finding]:
        return [Finding("stub.warn", Severity.WARNING, "only a warning")]

    monkeypatch.setattr(checks, "CHECKS", (checks.Check("stub", "core", warn),))
    commands.doctor([copy])


def test_s4_6_1_3_json_lists_every_finding_in_module_order(
    copy: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _break_generated(copy)  # core
    _break_pins(copy)  # cicd, listed after docs by the archetype
    _break_derived(copy)  # docs
    with pytest.raises(AppException):
        commands.doctor([copy], json=True)

    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    items = payload["findings"]
    assert items
    assert all(set(item) == {"code", "severity", "message", "path"} for item in items)
    assert all(isinstance(item["severity"], str) for item in items)

    codes = [item["code"] for item in items]
    assert codes.index("artifact.drift") < codes.index("docs.nav-stale")
    assert codes.index("docs.nav-stale") < codes.index("ci.unpinned")


def test_s4_6_1_4_apply_fails_on_an_error_finding(
    copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(config: object, root: Path) -> list[Finding]:
        return [Finding("stub.error", Severity.ERROR, "an error")]

    monkeypatch.setattr(checks, "CHECKS", (checks.Check("stub", "core", fail),))
    with pytest.raises(AppException, match=r"check\(s\) failed"):
        commands.apply()


def test_s4_6_5_1_seeded_edits_and_deletions_are_silent(copy: Path) -> None:
    _edit(copy, "README.md", lambda text: text + "\nmy own words\n")
    (copy / "src" / "python_app" / "commands.py").unlink()
    for findings in (checks.run(copy), doctor.full(copy)):
        assert [
            str(f)
            for f in findings
            if f.path in {"README.md", "src/python_app/commands.py"}
        ] == []
        assert findings == []


def test_s4_6_5_2_repository_owned_pyproject_and_layout_are_silent(
    copy: Path,
) -> None:
    _edit(
        copy,
        "pyproject.toml",
        lambda text: text.replace(
            'typeCheckingMode = "strict"', 'typeCheckingMode = "basic"'
        ),
    )
    (copy / "NOTES.txt").write_text("notes\n", encoding="utf-8")
    (copy / "tests").rename(copy / "test")
    assert checks.run(copy) == []


def test_s4_6_5_3_quality_checks_run_by_default(copy: Path) -> None:
    _break_quality(copy)
    assert checks.run(copy, scope="ownership") == []
    assert {"docs.broken-link", "deps.required-missing"} <= {
        f.code for f in checks.run(copy)
    }
    assert _run_one(copy, "docs-site")
    assert _run_one(copy, "rn-forge-deps")


def test_s4_6_5_4_a_sibling_under_rn_forge_is_ignored(copy: Path) -> None:
    before = ([str(f) for f in checks.run(copy)], [str(f) for f in doctor.full(copy)])
    sibling = copy / ".rn-forge" / "other"
    sibling.mkdir()
    (sibling / "state.json").write_text("{not json", encoding="utf-8")
    after = ([str(f) for f in checks.run(copy)], [str(f) for f in doctor.full(copy)])
    assert after == before


def test_s4_6_5_5_managed_drift_still_reported(copy: Path) -> None:
    _break_generated(copy)
    assert "artifact.drift" in {f.code for f in checks.run(copy)}
    _edit(copy, "Taskfile.yml", lambda text: text.replace("\n# edit\n", ""))
    (copy / "tasks" / "quality.yml").unlink()
    missing = [f for f in checks.run(copy) if f.code == "artifact.missing"]
    assert [f.path for f in missing] == ["tasks/quality.yml"]


def test_s4_6_5_6_malformed_config_still_errors(copy: Path) -> None:
    (copy / ".rn-forge" / "kiln" / "config.toml").write_text(
        "not = [valid", encoding="utf-8"
    )
    with pytest.raises(AppException, match="config"):
        checks.run(copy)


@pytest.fixture
def fleet(copy: Path, tmp_path: Path) -> Path:
    """Three repos (`clean`, `warned`, `broken`) and a non-kiln `plain` dir under
    one working directory, so the paths given are short and relative."""
    base = tmp_path / "fleet"
    base.mkdir()
    for name in ("clean", "warned", "broken"):
        shutil.copytree(copy, base / name, ignore=_IGNORE)
    _break_generated(base / "broken")
    (base / "plain").mkdir()
    return base


def _warn_only(monkeypatch: pytest.MonkeyPatch, repo_name: str) -> None:
    real = checks.run

    def run(root: Path, only: str | None = None) -> list[Finding]:
        findings = real(root, only)
        if root.name == repo_name:
            findings.append(Finding("stub.warn", Severity.WARNING, "only a warning"))
        return findings

    monkeypatch.setattr(checks, "run", run)


def test_s4_6_3_1_table_has_one_row_per_repo(
    fleet: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(fleet)
    commands.doctor([Path("clean"), Path("warned")], all=True)
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if "│" in line or "┃" in line]
    assert any(
        "repo" in line and "errors" in line and "warnings" in line for line in lines
    )
    rows = [line for line in lines if "clean" in line or "warned" in line]
    assert len(rows) == 2
    assert [("clean" in row) for row in rows] == [True, False]


def test_s4_6_3_1_more_than_one_path_needs_all(fleet: Path) -> None:
    with pytest.raises(AppException, match="--all"):
        commands.doctor([fleet / "clean", fleet / "warned"])


def test_s4_6_3_1_single_path_json_is_unchanged(
    fleet: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commands.doctor([fleet / "clean"], json=True)
    assert json.loads(capsys.readouterr().out) == {"findings": []}


def test_s4_6_3_2_json_attributes_findings(
    fleet: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(fleet)
    with pytest.raises(AppException):
        commands.doctor([Path("broken"), Path("clean")], all=True, json=True)
    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert [repo["path"] for repo in payload["repos"]] == ["broken", "clean"]
    broken, clean = payload["repos"]
    assert clean["findings"] == []
    assert "artifact.drift" in {item["code"] for item in broken["findings"]}
    assert all(
        set(item) == {"code", "severity", "message", "path"}
        for item in broken["findings"]
    )
    errors = sum(i["severity"] == "error" for i in broken["findings"])
    assert payload["summary"] == {"repos": 2, "errors": errors, "warnings": 0}


def test_s4_6_3_3_a_non_kiln_path_is_its_own_error(
    fleet: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(fleet)
    with pytest.raises(AppException):
        commands.doctor([Path("plain"), Path("broken")], all=True, json=True)
    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    plain, broken = payload["repos"]
    assert [i["code"] for i in plain["findings"]] == ["config.load"]
    assert plain["findings"][0]["severity"] == "error"
    assert plain["findings"][0]["message"]
    assert "artifact.drift" in {i["code"] for i in broken["findings"]}


def test_s4_6_3_3_full_runs_per_repo(fleet: Path) -> None:
    commands.doctor([fleet / "clean", fleet / "warned"], all=True, full=True)


@pytest.mark.parametrize("order", [("clean", "broken"), ("broken", "clean")])
def test_s4_6_3_4_exit_is_order_independent(
    fleet: Path, order: tuple[str, str]
) -> None:
    with pytest.raises(AppException):
        commands.doctor([fleet / name for name in order], all=True)


def test_s4_6_3_5_three_repos_clean_warnings_errors(
    fleet: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(fleet)
    _warn_only(monkeypatch, "warned")
    with pytest.raises(AppException):
        commands.doctor(
            [Path("clean"), Path("warned"), Path("broken")], all=True, json=True
        )
    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    counts = {
        repo["path"]: (
            sum(i["severity"] == "error" for i in repo["findings"]),
            sum(i["severity"] == "warning" for i in repo["findings"]),
        )
        for repo in payload["repos"]
    }
    assert counts["clean"] == (0, 0)
    assert counts["warned"] == (0, 1)
    assert counts["broken"][0] >= 1
    assert payload["summary"]["repos"] == 3
    assert payload["summary"]["warnings"] == 1
    assert payload["summary"]["errors"] == counts["broken"][0]


def test_s4_6_3_5_warnings_alone_exit_0(
    fleet: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _warn_only(monkeypatch, "warned")
    commands.doctor([fleet / "clean", fleet / "warned"], all=True)


def test_s4_12_5_1_bare_doctor_reports_the_quality_checks(
    copy: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _break_quality(copy)
    assert {"docs.broken-link", "deps.required-missing"} <= {
        f.code for f in checks.run(copy)
    }
    with pytest.raises(AppException):
        commands.doctor([copy], json=True)
    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    codes = {item["code"] for item in payload["findings"]}
    assert {"docs.broken-link", "deps.required-missing"} <= codes


def test_s4_12_5_2_the_ownership_scope_skips_them(copy: Path) -> None:
    _break_quality(copy)
    assert checks.run(copy, scope="ownership") == []
    _break_generated(copy)
    assert "artifact.drift" in {f.code for f in checks.run(copy, scope="ownership")}


def test_s4_12_5_3_apply_does_not_fail_on_them(copy: Path) -> None:
    _break_quality(copy)
    commands._fail_on_errors(copy)
    commands.apply()
    _break_generated(copy)
    with pytest.raises(AppException, match=r"check\(s\) failed"):
        commands._fail_on_errors(copy)


def test_s4_12_5_4_full_includes_them_and_the_render_findings(
    copy: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _edit(
        copy,
        ".rn-forge/kiln/config.toml",
        lambda text: text.replace("sonar = true", "sonar = false"),
    )
    _break_quality(copy)
    with pytest.raises(AppException):
        commands.doctor([copy], full=True, json=True)
    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    codes = {item["code"] for item in payload["findings"]}
    assert {"artifact.stale", "docs.broken-link", "deps.required-missing"} <= codes


def test_s4_12_5_5_all_includes_them(
    fleet: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _break_site(fleet / "clean")
    with pytest.raises(AppException):
        commands.doctor([fleet / "clean", fleet / "warned"], all=True, json=True)
    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    first, second = payload["repos"]
    assert "docs.broken-link" in {item["code"] for item in first["findings"]}
    assert second["findings"] == []


def test_s7_3_2_1_invalid_state_is_an_app_exception(copy: Path) -> None:
    (copy / ".rn-forge" / "kiln" / "state.json").write_text("{", encoding="utf-8")
    with pytest.raises(AppException, match=r"state\.json") as raised:
        checks.run(copy)
    assert not isinstance(raised.value, json.JSONDecodeError)


def test_s7_3_3_1_doctor_needs_no_pyyaml(copy: Path) -> None:
    def run(prelude: str) -> subprocess.CompletedProcess[str]:
        code = f"import sys; {prelude}from rn_forge.kiln.main import app; app()"
        return subprocess.run(
            [sys.executable, "-c", code, "doctor"],
            cwd=copy,
            capture_output=True,
            text=True,
            check=False,
        )

    assert any((copy / ".github" / "workflows").glob("*.yml"))
    plain = run("")
    blocked = run("sys.modules['yaml'] = None; ")
    assert blocked.returncode == plain.returncode
    assert "yaml" not in blocked.stderr
