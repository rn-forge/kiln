"""A command override reaches the rendered task file as one quoted scalar."""

from __future__ import annotations
import re
from pathlib import Path
import pytest
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import artifacts
from tests.conftest import requires
from tests.modules.tasks.support import _load, _root, _run_task

TEMPLATES = Path(artifacts.__file__).parent / "templates" / "tasks"


def _apply_override(tmp_path: Path, text: str) -> Path:
    root = _root(
        tmp_path,
        "python-tool",
        extra=f'\n[tasks]\n[tasks.command_overrides]\n"workspace:clean" = {_toml(text)}\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    return root


def _toml(text: str) -> str:
    return "'''" + text + "'''"


@requires("task")
def test_an_override_with_a_colon_runs_as_one_command(tmp_path: Path) -> None:
    root = _apply_override(tmp_path, 'echo "a: b"')
    assert _load(root, "tasks/workspace.yml")["tasks"]["clean"]["cmds"] == [
        'echo "a: b"'
    ]
    result = _run_task(root, "clean")
    assert result.returncode == 0
    assert "a: b" in result.stdout


@pytest.mark.parametrize(
    "text",
    [
        "echo a: b",
        "- echo x",
        "# not a command",
        "{{.X}} run",
        "echo \"q\" 'r' \\ s",
        "echo >&2 x",
        "echo café",
    ],
)
def test_an_override_round_trips_through_yaml(tmp_path: Path, text: str) -> None:
    root = _apply_override(tmp_path, text)
    assert _load(root, "tasks/workspace.yml")["tasks"]["clean"]["cmds"] == [text]


def test_every_overridable_task_is_used_by_a_template_and_no_other_is() -> None:
    used = {
        name
        for path in TEMPLATES.glob("*.j2")
        for name in re.findall(r'override\("([^"]+)"\)', path.read_text())
    }
    assert used == set(artifacts.OVERRIDABLE)
