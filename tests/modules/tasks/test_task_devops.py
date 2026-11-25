"""The generated tasks call `kiln-devops`."""

from __future__ import annotations
import pytest
from pathlib import Path
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.config import KilnConfig
from rn_forge.commons.exceptions import AppException
from rn_forge.kiln.modules.core import cycle
from tests.conftest import requires
from tests.modules.tasks.support import (
    ARCHETYPES,
    _ci_tasks,
    _load,
    _node_lib_root,
    _root,
    _run_task,
    _web_root,
)


@pytest.mark.parametrize(
    ("archetype", "extra", "has"),
    [
        ("node-lib", "", True),
        ("python-web-app", 'frontend = "angular"', True),
        ("python-lib", "", False),
        ("python-tool", "", False),
    ],
)
def test_dist_tasks_render_for_node_cells_only(
    tmp_path: Path, archetype: str, extra: str, has: bool
) -> None:
    if archetype == "python-web-app":
        root = _web_root(tmp_path, archetype, "fastapi", extra=extra)
    else:
        root = _root(tmp_path, archetype)
    tasks = _ci_tasks(root)["tasks"]
    names = {"dist:resolve": "dist-resolve", "dist:verify": "dist-verify"}
    for name, verb in names.items():
        if has:
            assert tasks[name]["cmds"] == [f"{{{{.DEVOPS}}}} {verb} {{{{.CLI_ARGS}}}}"]  # type: ignore[index]
            assert tasks[name]["desc"]  # type: ignore[index]
        else:
            assert name not in tasks  # type: ignore[operator]


def test_release_github_writes_notes_with_kiln_devops(
    tmp_path: Path,
) -> None:
    task = _ci_tasks(_node_lib_root(tmp_path))["tasks"]["release:github"]  # type: ignore[index]
    script = task["cmds"][0]
    assert (
        '{{.DEVOPS}} notes CHANGELOG.md "${tag#v}" > "$RUNNER_TEMP/notes.md"' in script
    )
    assert "kiln-devops notes" in task["desc"]
    assert "release-notes.mjs" not in task["desc"]


@pytest.mark.parametrize(
    ("archetype", "has"),
    [("node-lib", True), ("python-web-app", True), ("python-lib", False)],
)
def test_consumer_task_renders_for_node_cells_only(
    tmp_path: Path, archetype: str, has: bool
) -> None:
    root = (
        _web_root(tmp_path, archetype, "fastapi")
        if archetype == "python-web-app"
        else _root(tmp_path, archetype)
    )
    tasks = _ci_tasks(root)["tasks"]
    if has:
        assert tasks["consumer"]["cmds"] == ["{{.DEVOPS}} consumer {{.CLI_ARGS}}"]  # type: ignore[index]
        assert tasks["consumer"]["desc"]  # type: ignore[index]
    else:
        assert "consumer" not in tasks  # type: ignore[operator]


SONAR_DESC = (
    "Run the coverage tests and scan the checked-out branch on SonarCloud, "
    "awaiting the quality gate. Needs SONAR_TOKEN and sonar-scanner on PATH; "
    "pass --dry-run after -- to print the commands."
)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_sonar_on_renders_the_verb_and_its_include(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    task = YamlUtils.load((root / "tasks/sonar.yml").read_text(encoding="utf-8"))[
        "tasks"
    ]["local"]
    assert task["desc"] == SONAR_DESC
    assert task["cmds"] == ["{{.DEVOPS}} sonar-local {{.CLI_ARGS}}"]
    assert task.get("internal") is not True
    taskfile = YamlUtils.load((root / "Taskfile.yml").read_text(encoding="utf-8"))
    assert taskfile["includes"]["sonar"] == "tasks/sonar.yml"


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_sonar_off_renders_neither_file_nor_include(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype, extra="\n[ci]\nsonar = false\n")
    cycle.apply(root, home=tmp_path / "home")
    assert not (root / "tasks/sonar.yml").exists()
    taskfile = YamlUtils.load((root / "Taskfile.yml").read_text(encoding="utf-8"))
    assert "sonar" not in taskfile["includes"]


def _python_test_cmds(root: Path) -> list[object]:
    cycle.apply(root, home=root / "home")
    return _load(root, "tasks/python.yml")["tasks"]["test"]["cmds"]


def test_workspace_test_takes_a_package_and_pytest_args(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "python-lib")
    cmd = "\n".join(str(c) for c in _python_test_cmds(root))
    assert "set -- {{.CLI_ARGS}}" in cmd
    assert "task test: unknown package '$package'; one of: {{.PACKAGES}}" in cmd
    assert 'pytest -q "$@"' in cmd
    desc = _load(root, "Taskfile.yml")["tasks"]["test"]["desc"]
    assert "pass -- <package>" in desc


def test_single_package_test_passes_args_to_pytest(tmp_path: Path) -> None:
    tool = _root(tmp_path / "tool", "python-tool")
    assert _python_test_cmds(tool) == ["uv run pytest -q {{.CLI_ARGS}}"]
    web = _web_root(
        tmp_path / "web", "python-web-app", "fastapi", extra='frontend = "angular"'
    )
    config = KilnConfig.load(web)
    assert _python_test_cmds(web) == [
        f"uv run --directory {config.api_dir} --package {config.name}-api "
        "pytest -q {{.CLI_ARGS}}"
    ]


def test_no_args_form_is_unchanged(tmp_path: Path) -> None:
    cmd = "\n".join(
        str(c) for c in _python_test_cmds(_root(tmp_path / "a", "python-lib"))
    )
    assert "|| [ $? -eq 5 ]" in cmd
    overridden = _root(
        tmp_path / "b",
        extra='\n[tasks]\n[tasks.command_overrides]\n"python:test" = "echo hi"\n',
    )
    assert _python_test_cmds(overridden) == ["echo hi"]


@requires("task")
def test_unknown_package_fails_naming_it(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    cycle.apply(root, home=tmp_path / "home")
    result = _run_task(root, "test", "--", "nope")
    # Task reports a failed command as its own 201, not the command's status.
    assert result.returncode != 0
    assert "unknown package 'nope'" in result.stderr
    assert "alpha" in result.stderr
    assert "beta" in result.stderr


def test_release_task_file_only_with_release_evidence(tmp_path: Path) -> None:
    off = _root(tmp_path / "off")
    cycle.apply(off, home=tmp_path / "home")
    assert not (off / "tasks/release.yml").exists()
    taskfile = YamlUtils.load((off / "Taskfile.yml").read_text(encoding="utf-8"))
    assert "release" not in taskfile["includes"]
    on = _root(tmp_path / "on", extra="\n[ci.checks]\nrelease-evidence = true\n")
    cycle.apply(on, home=tmp_path / "home")
    task = _load(on, "tasks/release.yml")["tasks"]["evidence"]
    assert 'evidence render --run "$1" --release "$2"' in task["cmds"][0]
    taskfile = YamlUtils.load((on / "Taskfile.yml").read_text(encoding="utf-8"))
    assert taskfile["includes"]["release"] == "tasks/release.yml"


def test_release_namespace_is_reserved(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + '\n[tasks]\nincludes = [{ namespace = "release", taskfile = "tasks/mine.yml" }]\n',
        encoding="utf-8",
    )
    with pytest.raises(AppException, match=r"tasks\.includes\.0\.namespace"):
        KilnConfig.load(root)
