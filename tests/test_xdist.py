"""S17.3.1: pytest runs on every core."""

import tomllib
from pathlib import Path

from rn_forge.commons.fs.documents import YamlUtils

ROOT = Path(__file__).resolve().parents[1]


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def test_s17_3_1_1_addopts_run_in_parallel() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tokens = pyproject["tool"]["pytest"]["ini_options"]["addopts"].split()
    for token in ("-n", "auto", "--import-mode=importlib", "-ra"):
        assert token in tokens, token
    assert tokens[tokens.index("-n") + 1] == "auto"


def test_s17_3_1_2_xdist_is_a_locked_dev_dependency() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    entries = [
        e
        for e in pyproject["dependency-groups"]["dev"]
        if e.startswith("pytest-xdist>=")
    ]
    assert len(entries) == 1
    floor = entries[0].split(">=")[1]
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked = {package["name"]: package["version"] for package in lock["package"]}
    assert _version_key(floor) <= _version_key(locked["pytest-xdist"])


def test_s17_3_1_3_the_test_task_is_unchanged() -> None:
    tasks = YamlUtils.load((ROOT / "tasks" / "python.yml").read_text(encoding="utf-8"))[
        "tasks"
    ]
    assert tasks["test"]["cmds"] == ["uv run pytest -q"]
    assert tasks["test:coverage"]["cmds"] == [
        "uv run pytest -q --cov=rn_forge.kiln --cov-report=xml:coverage.xml"
    ]
