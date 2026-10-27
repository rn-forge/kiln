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


def test_s6_1_12_adopt_is_shipped(capsys: pytest.CaptureFixture[str]) -> None:
    commands.prompt(json=True)
    names = [p["name"] for p in json.loads(capsys.readouterr().out)["prompts"]]
    assert "adopt" in names
    commands.prompt("adopt")
    text = capsys.readouterr().out
    for heading in (
        "Choose the route",
        "Prepare",
        "Preview and sort the plan",
        "Apply",
        "Reconcile the files kiln inserted a block into",
        "Seeded files that kiln's checks need in a given shape",
        "Convert the specs to kiln's work model",
        "Make the gate runnable",
        "Run the gate and sort what is left",
        "Review",
    ):
        assert f". {heading}" in text


def test_s6_1_15_no_prompt_names_itself_positionally() -> None:
    for prompt_file in (ROOT / "src/rn_forge/kiln/prompts").glob("*.md"):
        text = prompt_file.read_text(encoding="utf-8")
        assert not re.search(r"kiln prompt [a-z]", text), prompt_file.name


def _adopt_sections() -> dict[str, str]:
    text = (ROOT / "src/rn_forge/kiln/prompts/adopt.md").read_text(encoding="utf-8")
    parts = re.split(r"^## (\d+)\. ", text, flags=re.MULTILINE)
    return {parts[i]: " ".join(parts[i + 1].split()) for i in range(1, len(parts), 2)}


def test_s6_6_3_1_adopt_names_what_init_now_does(
    capsys: pytest.CaptureFixture[str],
) -> None:
    commands.prompt("adopt")
    text = " ".join(capsys.readouterr().out.split())
    assert "task format" in text
    assert "separate commit" in text
    assert "init.kiln-dev-dependency-missing" not in text


def test_s6_6_3_2_adopt_says_where_quality_findings_appear() -> None:
    sections = _adopt_sections()
    bullet = next(
        part
        for part in sections["6"].split(" - ")
        if "docs.packages-area-missing" in part
    )
    assert "task lint" in bullet
    assert (
        "`init`'s closing check, like a plain `kiln doctor`, runs only the "
        "ownership checks; `task lint` also runs `rn-forge-deps`, "
        "`docs-structure` and `docs-site`, so read its findings too."
    ) in sections["9"]
