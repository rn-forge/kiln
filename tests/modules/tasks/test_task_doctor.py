"""One `kiln:doctor` replaces the per-check tasks."""

from __future__ import annotations
import pytest
import re
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS
from tests.conftest import module_findings, requires
from tests.modules.tasks.support import (
    ALL_CELLS,
    _ci_tasks,
    _codes,
    _load,
    _root,
    _run_task,
    _ci_root,
    _unmarked,
)


LINT_ORDER = [
    "python:lint",
    "python:lint:imports",
    "quality:lint:markdown",
    "quality:lint:toml",
    "quality:lint:yaml",
    "kiln:doctor",
    "ci:lint:workflows",
    "python:lint:audit",
    "python:lint:licenses",
]


REMOVED_KEYS = [
    "quality:lint:generated",
    "quality:lint:rn-forge-deps",
    "quality:lint:task-layout",
    "ci:lint:entrypoint",
    "ci:lint:pins",
    "ci:lint:hooks",
    "docs:lint:site",
    "docs:lint:structure",
    "docs:lint:generate",
    "docs:lint",
    "kiln:doctor",
]


KILN_DOCTOR_CMDS = [
    {"cmd": "{{.KILN}} doctor .", "if": '[ -z "{{.KILN_DOCTOR_FULL}}" ]'},
    {"cmd": "{{.KILN}} doctor . --full", "if": '[ -n "{{.KILN_DOCTOR_FULL}}" ]'},
]


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_kiln_yml_holds_one_internal_doctor_task(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _ci_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    document = _load(root, "tasks/kiln.yml")
    assert set(document["tasks"]) == {"doctor", "diff", "apply", "pin"}
    assert not [n for n in ("diff", "apply") if "internal" in document["tasks"][n]]
    doctor = document["tasks"]["doctor"]
    assert doctor["internal"] is True
    assert doctor["desc"].strip()
    assert doctor["cmds"] == KILN_DOCTOR_CMDS
    assert _load(root, "Taskfile.yml")["includes"]["kiln"] == "tasks/kiln.yml"


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_root_lint_runs_in_the_exact_order(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _ci_root(tmp_path, archetype, extra)
    expected = list(LINT_ORDER)
    if archetype == "python-web-app":
        expected[2:2] = ["node:lint", "node:lint:format"]
        expected.insert(expected.index("python:lint:audit") + 1, "node:lint:audit")
        expected.append("node:lint:licenses")
    for profile in ("mkdocs", "none"):
        config = root / ".rn-forge/kiln/config.toml"
        text = config.read_text(encoding="utf-8")
        config.write_text(
            re.sub(r'profile = "\w+"', f'profile = "{profile}"', text),
            encoding="utf-8",
        )
        cycle.apply(root, home=tmp_path / "home")
        cmds = _unmarked(_load(root, "Taskfile.yml")["tasks"]["lint"]["cmds"])
        assert cmds == [{"task": name} for name in expected]


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
@requires("task")
def test_doctor_runs_once(tmp_path: Path, archetype: str, extra: str) -> None:
    root = _ci_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    without = _run_task(root, "--dry", "lint")
    assert without.returncode == 0, without.stderr
    out = without.stdout + without.stderr
    assert out.count("kiln doctor .") == 1
    assert "--full" not in out
    asked = _run_task(root, "--dry", "lint", "KILN_DOCTOR_FULL=1")
    assert asked.returncode == 0, asked.stderr
    out = asked.stdout + asked.stderr
    assert out.count("kiln doctor . --full") == 1
    assert out.count("kiln doctor .") == 1


def test_kiln_yml_runs_the_pinned_kiln(tmp_path: Path) -> None:
    root = _root(tmp_path, extra='\n[kiln]\nref = "v9.9.9"\n')
    cycle.apply(root, home=tmp_path / "home")
    assert _load(root, "tasks/kiln.yml")["vars"]["KILN"] == (
        'uvx --from "rn-forge-kiln @ git+https://github.com/rn-forge/kiln@v9.9.9" kiln'
    )


def test_kiln_itself_runs_its_working_tree(tmp_path: Path) -> None:
    root = _root(
        tmp_path, extra='\n[archetype."python-tool"]\nmodule = "rn_forge.kiln"\n'
    )
    cycle.apply(root, home=tmp_path / "home")
    assert _load(root, "tasks/kiln.yml")["vars"]["KILN"] == "uv run kiln"


def test_task_order(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    pin = _load(root, "tasks/kiln.yml")["tasks"]["pin"]
    assert "internal" not in pin
    assert pin["desc"].strip()
    assert pin["cmds"] == [
        "{{.KILN}} pin{{if .CLI_ARGS}} --ref {{.CLI_ARGS}}{{end}}",
        'uvx --from "rn-forge-kiln @ git+https://github.com/rn-forge/kiln'
        '@$({{.KILN}} pin --show)" kiln apply',
    ]


def test_the_pin_task_passes_the_ref_as_an_option(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    sha = "0123456789abcdef0123456789abcdef01234567"
    run = _run_task(root, "--dry", "kiln:pin", "--", sha)
    assert run.returncode == 0, run.stderr
    assert f"pin --ref {sha}" in run.stdout + run.stderr


def test_the_pin_task_with_no_ref_runs_bare_pin(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    run = _run_task(root, "--dry", "kiln:pin")
    assert run.returncode == 0, run.stderr
    first = next(
        line for line in (run.stdout + run.stderr).splitlines() if " pin" in line
    )
    assert first.rstrip().endswith(" pin")
    assert "--ref" not in first


def test_the_pin_task_takes_no_argument(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    pin = _load(root, "tasks/kiln.yml")["tasks"]["pin"]
    assert "preconditions" not in pin
    assert pin["cmds"][-1].endswith('@$({{.KILN}} pin --show)" kiln apply')


def test_not_in_kiln(tmp_path: Path) -> None:
    root = _root(
        tmp_path, extra='\n[archetype."python-tool"]\nmodule = "rn_forge.kiln"\n'
    )
    cycle.apply(root, home=tmp_path / "home")
    assert "pin" not in _load(root, "tasks/kiln.yml")["tasks"]


def test_an_unpinned_config_runs_kilns_own_ref(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    assert _load(root, "tasks/kiln.yml")["vars"]["KILN"] == archetypes.kiln_command(
        archetypes.KILN_REF
    )
    assert archetypes.KILN_REF in _load(root, "tasks/kiln.yml")["vars"]["KILN"]


def test_docs_generate_runs_the_pinned_kiln(tmp_path: Path) -> None:
    root = _root(tmp_path, extra='\n[kiln]\nref = "v9.9.9"\n')
    cycle.apply(root, home=tmp_path / "home")
    docs = _load(root, "tasks/docs.yml")
    assert docs["vars"]["KILN"] == _load(root, "tasks/kiln.yml")["vars"]["KILN"]
    assert docs["tasks"]["generate"]["cmds"] == ["{{.KILN}} docs-generate ."]


def test_docs_yml_holds_the_three_verbs(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "tasks/docs.yml")["tasks"]
    assert set(tasks) == {"build", "serve", "generate"}
    assert not any("internal" in task for task in tasks.values())


@pytest.mark.parametrize("key", REMOVED_KEYS)
def test_removed_keys_are_refused(tmp_path: Path, key: str) -> None:
    root = _root(
        tmp_path,
        extra=f'\n[tasks]\n[tasks.command_overrides]\n"{key}" = "echo hi"\n',
    )
    with pytest.raises(AppException, match=re.escape(key)):
        TASKS.artifacts(KilnConfig.load(root), root)


def test_an_include_cannot_take_kiln(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + '\n[tasks]\nincludes = [{ namespace = "kiln", taskfile = "tasks/mine.yml" }]\n',
        encoding="utf-8",
    )
    assert "taskgraph.reserved-namespace" in _codes(root)


def test_kiln_doctor_must_be_internal(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    path = root / "tasks/kiln.yml"
    text = path.read_text(encoding="utf-8")
    head, _, tail = text.partition("  doctor:\n")
    path.write_text(
        head + "  doctor:\n" + tail.replace("    internal: true\n", "", 1),
        encoding="utf-8",
    )
    assert "taskgraph.not-internal" in _codes(root)


def test_gate_shrunk_names_kiln_doctor(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    taskfile = root / "Taskfile.yml"
    line = "      - task: kiln:doctor\n"
    text = taskfile.read_text(encoding="utf-8")
    assert line in text
    taskfile.write_text(text.replace(line, ""), encoding="utf-8")
    findings = list(module_findings("tasks", KilnConfig.load(root), root))
    assert any(f.code == "gate.shrunk" and "kiln:doctor" in str(f) for f in findings)


@pytest.mark.parametrize(("archetype", "extra"), ALL_CELLS)
def test_task_layout_accepts_the_rendered_files(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _ci_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    assert _codes(root) == []


@pytest.mark.parametrize("name", [n for n in archetypes.shipped() if n != "node-lib"])
def test_required_validate_names_kiln_doctor(name: str) -> None:
    required = archetypes.load(name).required_validate
    assert required[required.index("python:lint") + 1] == "kiln:doctor"
    for gone in (
        "quality:lint:generated",
        "quality:lint:rn-forge-deps",
        "quality:lint:task-layout",
        "ci:lint:entrypoint",
        "ci:lint:pins",
        "ci:lint:hooks",
    ):
        assert gone not in required


def test_without_mkdocs_kiln_yml_still_renders(tmp_path: Path) -> None:
    root = _root(tmp_path, profile="none")
    cycle.apply(root, home=tmp_path / "home")
    assert (root / "tasks/kiln.yml").is_file()
    cmds = _unmarked(_load(root, "Taskfile.yml")["tasks"]["lint"]["cmds"])
    assert {"task": "kiln:doctor"} in cmds
    assert not (root / "tasks/docs.yml").exists()
    assert _codes(root) == []


TWINE = (
    'uvx --from twine==6.2.0 twine check --strict dist/"$name"/*.whl'
    ' dist/"$name"/*.tar.gz'
)


def _release_script(root: Path, task: str) -> str:
    return "\n".join(_ci_tasks(root)["tasks"][task]["cmds"])  # type: ignore[index]


def test_release_tasks_upload(tmp_path: Path) -> None:
    pypi = _root(tmp_path / "pypi", "python-lib", extra='\n[ci]\nrelease = "pypi"\n')
    build = _release_script(pypi, "release:build")
    publish = _release_script(pypi, "release:publish")
    assert build.count("uv build") == 3
    assert build.count(TWINE) == build.count("uv build")
    for position in [m.start() for m in re.finditer("uv build", build)]:
        assert TWINE in build[position:].split("uv export")[0]
    testpypi = build[build.index('"${TESTPYPI:-}" = true') :]
    assert testpypi.index("uv build") < testpypi.index("release-state")
    assert "continue" in testpypi.split("release-state")[0]
    assert "upload=pypi" in publish
    assert 'if [ "${TESTPYPI:-}" = true ]; then upload=testpypi; fi' in publish
    assert '--notes-file "$notes" --upload "$upload" dist/"$name"/*' in publish
    plain = _root(tmp_path / "plain", "python-lib")
    for task in ("release:build", "release:publish"):
        text = _release_script(plain, task)
        for forbidden in ("twine", "TESTPYPI", "--upload", "upload="):
            assert forbidden not in text, (task, forbidden)


def test_verify_release_from_pypi(tmp_path: Path) -> None:
    pypi = _root(tmp_path / "pypi", "python-lib", extra='\n[ci]\nrelease = "pypi"\n')
    task = _ci_tasks(pypi)["tasks"]["verify-release"]  # type: ignore[index]
    assert task["desc"] == (
        "CI only: Install the release from PyPI, outside the repository, and import it."
    )
    assert task["cmds"] == ["{{.DEVOPS}} verify-release --source pypi {{.CLI_ARGS}}"]
    plain = _ci_tasks(_root(tmp_path / "plain", "python-lib"))["tasks"]
    plain_task = plain["verify-release"]  # type: ignore[index]
    assert plain_task["cmds"] == [
        "{{.DEVOPS}} verify-release --source git {{.CLI_ARGS}}"
    ]
    assert "PyPI" not in plain_task["desc"]
