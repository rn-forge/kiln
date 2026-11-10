"""S4.5.6 — `kiln prompt`: shipped one-time procedures."""

from __future__ import annotations

import json
import re
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


def test_s16_8_2_5_adopt_sections(capsys: pytest.CaptureFixture[str]) -> None:
    commands.prompt(json=True)
    names = [p["name"] for p in json.loads(capsys.readouterr().out)["prompts"]]
    assert "adopt" in names
    commands.prompt("adopt")
    assert "Choose the route" in capsys.readouterr().out
    text = (ROOT / "src/rn_forge/kiln/prompts/adopt.md").read_text(encoding="utf-8")
    headings = (
        "Choose the route",
        "Build the reference",
        "Classify the files",
        "Reconcile the files kiln has a block in",
        "Rewrite commands to verbs",
        "Make the gate runnable",
        "Run the gate and sort what is left",
        "Review",
    )
    found = re.findall(r"^## \d+\. (.+)$", text, flags=re.MULTILINE)
    assert tuple(found) == headings


def test_s6_1_15_no_prompt_names_itself_positionally() -> None:
    for prompt_file in (ROOT / "src/rn_forge/kiln/prompts").glob("*.md"):
        text = prompt_file.read_text(encoding="utf-8")
        assert not re.search(r"kiln prompt [a-z]", text), prompt_file.name


def _adopt_sections() -> dict[str, str]:
    text = (ROOT / "src/rn_forge/kiln/prompts/adopt.md").read_text(encoding="utf-8")
    parts = re.split(r"^## (\d+)\. ", text, flags=re.MULTILINE)
    return {parts[i]: " ".join(parts[i + 1].split()) for i in range(1, len(parts), 2)}


def _adopt_text(capsys: pytest.CaptureFixture[str]) -> str:
    commands.prompt("adopt")
    return " ".join(capsys.readouterr().out.split())


def test_s16_1_4_2_prompt_points_at_the_runbook(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert "docs/runbooks/cutover.md" in _adopt_text(capsys)


def test_s16_8_2_6_adopt_has_no_init(capsys: pytest.CaptureFixture[str]) -> None:
    text = _adopt_text(capsys)
    for absent in ("kiln init", "--dry-run", "backups", "--force"):
        assert absent not in text
    for present in (
        "docs/runbooks/cutover.md",
        "kiln new",
        "`task`",
        "byte-for-byte",
    ):
        assert present in text, present


def test_s16_8_2_7_adopt_rewrites_verbs() -> None:
    sections = _adopt_sections()
    section = sections["5"]
    for needle in (
        "uv run",
        "pytest",
        "pnpm exec",
        "`task lint`",
        "`task test`",
        ".prettierignore",
    ):
        assert needle in section, needle
