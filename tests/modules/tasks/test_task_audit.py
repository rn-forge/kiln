"""The dependency vulnerability audit task."""

from __future__ import annotations

from tests.conftest import module_findings
import pytest
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.config import CiConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS
from rn_forge.kiln.modules.tasks.artifacts import render
from tests.modules.tasks.support import (
    ARCHETYPES,
    AUDIT_REF,
    WEB_CELLS,
    WORKFLOWS_REF,
    _audit_root,
    _codes,
    _rendered_yaml,
    _root,
    _unmarked,
    _web_root,
)


AUDIT_PREFIX = (
    "uv export --frozen --all-packages --all-groups --all-extras "
    "--no-emit-workspace --no-header"
)


AUDIT_SUFFIX = (
    "| uv run pip-audit --disable-pip --require-hashes --strict -r /dev/stdin"
)


AUDIT_ALL_CELLS = [(a, "") for a in ARCHETYPES] + list(WEB_CELLS)


def _audit_cmd(root: Path) -> str:
    _, python = _rendered_yaml(root)
    (cmd,) = python["lint:audit"]["cmds"]
    assert isinstance(cmd, str)
    return cmd


@pytest.mark.parametrize(("archetype", "extra"), AUDIT_ALL_CELLS)
def test_s4_11_5_1_lint_runs_audit_after_workflows(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _audit_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    root_tasks, python = _rendered_yaml(root)
    cmds = _unmarked(root_tasks["lint"]["cmds"])
    at = cmds.index(WORKFLOWS_REF)
    assert cmds[at : at + 2] == [WORKFLOWS_REF, AUDIT_REF]
    task = python["lint:audit"]
    assert task["internal"] is True
    assert task["desc"].strip()
    assert len(task["cmds"]) == 1
    assert isinstance(task["cmds"][0], str)
    assert "dependency vulnerabilities" in root_tasks["lint"]["desc"]


def test_s4_11_5_1_the_command(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    cmd = _audit_cmd(root)
    assert "\n" not in cmd
    assert "  " not in cmd
    assert "--ignore-vuln" not in cmd
    expected = f"set -o pipefail; {AUDIT_PREFIX} {AUDIT_SUFFIX}"
    assert cmd == expected


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s16_6_4_1_audit_exports_extras(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    cmd = _audit_cmd(root)
    assert "--all-extras" in cmd.split("|")[0]
    assert "set -o pipefail" in cmd


def test_s16_4_4_1_audit_command_has_no_exclude_flags(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    assert "--no-emit-package" not in _audit_cmd(root)


def test_s4_11_5_3_web_and_lib_cells_render_the_same_command(tmp_path: Path) -> None:
    commands = set()
    for archetype, extra in AUDIT_ALL_CELLS:
        root = _audit_root(tmp_path / archetype, archetype, extra)
        cycle.apply(root, home=tmp_path / archetype / "home")
        commands.add(_audit_cmd(root))
        _, python = _rendered_yaml(root)
        text = YamlUtils.serialize(python["lint:audit"])
        assert "for:" not in text
        assert "PACKAGE_DIRS" not in text
    assert len(commands) == 1


def test_s4_11_5_4_ignore_entries_become_flags(tmp_path: Path) -> None:
    one = _root(
        tmp_path / "one",
        extra=(
            '\n[[ci.checks.pip-audit.ignore]]\nid = "GHSA-xxxx-xxxx-xxxx"\n'
            'reason = "not reachable"\n'
        ),
    )
    cycle.apply(one, home=tmp_path / "one" / "home")
    assert _audit_cmd(one).endswith(f"{AUDIT_SUFFIX} --ignore-vuln GHSA-xxxx-xxxx-xxxx")
    two = _root(
        tmp_path / "two",
        extra=(
            '\n[[ci.checks.pip-audit.ignore]]\nid = "PYSEC-2026-1"\nreason = "a"\n'
            '\n[[ci.checks.pip-audit.ignore]]\nid = "CVE-2026-2"\nreason = "b"\n'
        ),
    )
    cycle.apply(two, home=tmp_path / "two" / "home")
    assert _audit_cmd(two).endswith(
        f"{AUDIT_SUFFIX} --ignore-vuln PYSEC-2026-1 --ignore-vuln CVE-2026-2"
    )


@pytest.mark.parametrize(
    "entry",
    [
        'id = "PYSEC-1"',
        'id = "PYSEC-1"\nreason = ""',
        'id = "PYSEC-1"\nreason = "   "',
        'reason = "why"',
        'id = ""\nreason = "why"',
        'id = "PYSEC-1"\nreason = "why"\nextra = "x"',
        'id = "PYSEC-1"\nreason = "why"\n\n[[ci.checks.pip-audit.ignore]]\n'
        'id = "PYSEC-1"\nreason = "again"',
    ],
)
def test_s4_11_5_5_ignore_entries_need_id_and_reason(
    tmp_path: Path, entry: str
) -> None:
    root = _root(tmp_path, extra=f"\n[[ci.checks.pip-audit.ignore]]\n{entry}\n")
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_s4_11_5_5_an_id_with_shell_characters_is_refused(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra='\n[[ci.checks.pip-audit.ignore]]\nid = "x; rm"\nreason = "why"\n',
    )
    with pytest.raises(AppException):
        KilnConfig.load(root)


def test_s4_11_5_5_the_default_config_has_an_empty_list() -> None:
    assert CiConfig().audit_policy().ignore == []


def test_s4_11_5_6_command_override_is_refused(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra=(
            '\n[tasks]\n[tasks.command_overrides]\n"python:lint:audit" = "echo hi"\n'
        ),
    )
    with pytest.raises(AppException, match="python:lint:audit: unknown task"):
        TASKS.artifacts(KilnConfig.load(root), root)


@pytest.mark.parametrize("name", [n for n in archetypes.shipped() if n != "node-lib"])
def test_s4_11_5_7_required_validate_gains_it(name: str) -> None:
    required = archetypes.load(name).required_validate
    assert "python:lint:audit" in required
    assert required.index("python:lint:audit") == (
        required.index("ci:lint:workflows") + 1
    )


@pytest.mark.parametrize(("archetype", "extra"), AUDIT_ALL_CELLS)
def test_s4_11_5_7_task_layout_accepts_the_rendered_files(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _audit_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    assert _codes(root) == []


def test_s4_11_5_7_gate_shrunk_fires_when_lint_drops_audit(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    taskfile = root / "Taskfile.yml"
    line = "      - task: python:lint:audit\n"
    text = taskfile.read_text(encoding="utf-8")
    assert line in text
    taskfile.write_text(text.replace(line, ""), encoding="utf-8")
    findings = [f for f in module_findings("tasks", KilnConfig.load(root), root)]
    assert any(
        f.code == "gate.shrunk" and "python:lint:audit" in str(f) for f in findings
    )


def test_s17_1_2_1_audit_override_is_refused(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra='\n[tasks]\n[tasks.command_overrides]\n"python:lint:audit" = "true"\n',
    )
    with pytest.raises(AppException) as raised:
        render(KilnConfig.load(root))
    assert "tasks.command_overrides.python:lint:audit: unknown task" in str(
        raised.value
    )


GUARDED = (
    "python:lint:audit",
    "python:lint:licenses",
    "node:lint:audit",
    "node:lint:licenses",
    "ci:secret-scan",
    "ci:internal-ranges",
)


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [(a, "") for a in (*ARCHETYPES, "node-lib")] + list(WEB_CELLS),
)
def test_s17_1_2_2_no_guarded_check_is_overridable(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    bad = '\n[tasks]\n[tasks.command_overrides]\n"x:y" = "true"\n'
    if archetype in WEB_CELLS[0] or archetype == "python-web-app":
        root = _web_root(tmp_path, archetype, "fastapi", extra=extra + bad)
    else:
        root = _root(tmp_path, archetype, extra=bad)
    with pytest.raises(AppException) as raised:
        render(KilnConfig.load(root))
    listed = str(raised.value).split("this archetype renders", 1)[1]
    names = {n.strip() for n in listed.split(",")}
    assert names.isdisjoint(GUARDED)


def test_s17_1_2_3_primitives_stay_overridable(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra=(
            '\n[tasks]\n[tasks.command_overrides]\n"python:lint:imports" = "echo hi"\n'
        ),
    )
    cycle.apply(root, home=tmp_path / "home")
    _, python = _rendered_yaml(root)
    assert python["lint:imports"]["cmds"] == ["echo hi"]


def test_s17_1_3_4_unreachable_licences_is_a_finding(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    taskfile = root / "Taskfile.yml"
    line = "      - task: python:lint:licenses\n"
    text = taskfile.read_text(encoding="utf-8")
    assert line in text
    taskfile.write_text(text.replace(line, ""), encoding="utf-8")
    findings = module_findings("tasks", KilnConfig.load(root), root)
    assert any(
        f.code == "gate.shrunk" and "python:lint:licenses" in str(f) for f in findings
    )
