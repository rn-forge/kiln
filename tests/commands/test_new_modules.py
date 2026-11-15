"""`kiln new`: the starter and `--module`."""

from __future__ import annotations
import json
import pytest
import tomllib
from collections.abc import Callable
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.kiln import checks
from rn_forge.kiln.modules.core import cycle
from tests.conftest import new_repo
from typing import Any


@pytest.fixture(autouse=True)
def _in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`kiln new` stages beneath the current directory; keep that out of the repo."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


STARTER = {
    "src/{package}/main.py",
    "src/{package}/commands.py",
    "src/{package}/product.py",
    "tests/test_cli.py",
    "tests/test_product.py",
}


@pytest.mark.parametrize("archetype", ["python-tool", "python-app"])
def test_s4_9_1_5_new_wires_cli_and_script(tmp_path: Path, archetype: str) -> None:
    directory = tmp_path / "demo-tool"
    new_repo(directory, archetype=archetype, docs="none", yes=True)

    written = tomllib.loads(
        (directory / ".rn-forge" / "kiln" / "config.toml").read_text(encoding="utf-8")
    )
    cli = written["cli"]
    assert cli["name"] == "demo-tool"
    assert cli["commands"] == [{"name": "hello", "target": "demo_tool.commands:hello"}]
    if archetype == "python-tool":
        assert written["lifecycle"] == {"product": "demo_tool.product:PRODUCT"}
    else:
        assert "lifecycle" not in written
    pyproject = tomllib.loads((directory / "pyproject.toml").read_text("utf-8"))
    assert pyproject["project"]["scripts"] == {"demo-tool": "demo_tool.main:app"}


def test_s4_9_1_6_new_records_seeded_and_validates(tmp_path: Path) -> None:
    """Slow like its neighbours: runs `uv init`; marks none, as the module note says."""
    directory = tmp_path / "demo-tool"
    new_repo(directory, archetype="python-tool", docs="none", yes=True)

    paths = {path.format(package="demo_tool") for path in STARTER}
    state_path = directory / ".rn-forge" / "kiln" / "state.json"

    def entries() -> dict[str, Any]:
        return json.loads(state_path.read_text(encoding="utf-8"))["entries"]

    recorded = entries()
    assert all(recorded[path]["kind"] == "seeded" for path in paths)
    assert not [
        path
        for path, entry in recorded.items()
        if path.startswith(("src/", "tests/"))
        and entry["kind"] != "seeded"
        and path not in {"src/demo_tool/__init__.py", "tests/test_package.py"}
    ]
    assert checks.run(directory) == []

    main = directory / "src" / "demo_tool" / "main.py"
    main.write_text("# edited\n", encoding="utf-8")
    before = {path: (directory / path).read_bytes() for path in paths}
    before_entries = {path: recorded[path] for path in paths}

    cycle.apply(directory, home=tmp_path / "home")

    assert {path: (directory / path).read_bytes() for path in paths} == before
    assert main.read_text(encoding="utf-8") == "# edited\n"
    assert {path: entries()[path] for path in paths} == before_entries


def test_s4_8_2_3_new_with_a_module(tmp_path: Path) -> None:
    directory = tmp_path / "demo-tool"
    new_repo(
        directory,
        archetype="python-tool",
        docs="mkdocs",
        module="rn_forge.demo",
        yes=True,
    )
    package = directory / "src/rn_forge/demo"
    for name in ("__init__.py", "py.typed", "main.py", "commands.py", "product.py"):
        assert (package / name).is_file()
    assert not (directory / "src/rn_forge/__init__.py").exists()
    assert not (directory / "src/demo_tool").exists()
    pyproject = tomllib.loads((directory / "pyproject.toml").read_text("utf-8"))
    assert pyproject["tool"]["uv"]["build-backend"]["module-name"] == "rn_forge.demo"
    assert pyproject["project"]["scripts"] == {"demo-tool": "rn_forge.demo.main:app"}

    def read(path: str) -> str:
        return (directory / path).read_text(encoding="utf-8")

    assert ".parents[3] / " in read("src/rn_forge/demo/main.py")
    assert "import rn_forge.demo\n" in read("tests/test_package.py")
    assert "from rn_forge.demo.main import app" in read("tests/test_cli.py")
    assert "--cov=rn_forge.demo " in read("tasks/python.yml")
    assert "::: rn_forge.demo" in read("docs/reference/python-api.md")
    written = tomllib.loads(read(".rn-forge/kiln/config.toml"))
    assert written["archetype"]["python-tool"]["module"] == "rn_forge.demo"
    assert written["cli"]["commands"][0]["target"] == "rn_forge.demo.commands:hello"
    assert written["lifecycle"]["product"] == "rn_forge.demo.product:PRODUCT"
    assert checks.run(directory) == []


def test_s4_8_2_3_new_without_a_module_is_unchanged(
    rendered: Callable[[str], Path],
) -> None:
    root = rendered("python-tool")
    written = tomllib.loads(
        (root / ".rn-forge/kiln/config.toml").read_text(encoding="utf-8")
    )
    assert "module" not in written.get("archetype", {}).get("python-tool", {})
    assert (root / "src/python_tool/py.typed").is_file()


def test_s4_8_2_3_an_invalid_module_is_refused_before_writing(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "demo-tool"
    with pytest.raises(AppException):
        new_repo(directory, archetype="python-tool", module="Rn-Forge", yes=True)
    assert not directory.exists()
    assert not (tmp_path / ".staging").exists()


def test_s4_8_2_3_module_on_another_archetype_is_refused(tmp_path: Path) -> None:
    directory = tmp_path / "demo-lib"
    with pytest.raises(AppException):
        new_repo(directory, archetype="python-lib", module="rn_forge.demo", yes=True)
    assert not directory.exists()
    assert not (tmp_path / ".staging").exists()
