"""S4.5.6 — `kiln prompt`: shipped one-time procedures."""

from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import commands

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def plain_console():
    yield
    console.set_mode(OutputMode.PLAIN)


def test_s4_5_6_1_lists_port_docs_with_its_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    commands.prompt(json=True)
    prompts = json.loads(capsys.readouterr().out)["prompts"]
    row = next(p for p in prompts if p["name"] == "port-docs")
    assert row["summary"]


def test_s4_5_6_1_plain_list_names_each_prompt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    commands.prompt()
    assert "port-docs" in capsys.readouterr().out


def test_s4_5_6_2_prints_a_prompt_from_any_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    commands.prompt("port-docs")
    assert "Carrying specs and decisions" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_s4_5_6_3_unknown_prompt_names_it() -> None:
    with pytest.raises(AppException, match="nope"):
        commands.prompt("nope")


def test_s4_5_6_4_the_wheel_contains_the_prompts(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    wheel = next(tmp_path.glob("*.whl"))
    assert "rn_forge/kiln/prompts/port-docs.md" in zipfile.ZipFile(wheel).namelist()


def test_s4_5_6_5_the_runbook_is_gone_and_unlinked() -> None:
    assert not (ROOT / "docs/runbooks/carrying-specs-and-decisions.md").exists()
    for page in (ROOT / "docs").rglob("*.md"):
        assert "](carrying-specs-and-decisions" not in page.read_text(encoding="utf-8")
    assert "carrying-specs-and-decisions" not in (ROOT / "mkdocs.yml").read_text(
        encoding="utf-8"
    )
