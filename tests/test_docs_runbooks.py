"""S16.3.1 — `docs/runbooks/cutover.md`: the one-time move onto kiln."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs/runbooks/cutover.md"
STEPS = (
    "Branch",
    "Build the reference",
    "Bring the files over",
    "Read the diff file by file",
    "Record a verdict",
    "Land the absorb stories",
    "Rebuild the reference and re-run the overlay",
    "Reconcile and gate",
    "Merge",
)


def _text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def _flat() -> str:
    return " ".join(_text().split())


def test_s16_8_2_1_runbook_steps() -> None:
    text = _text()

    assert text.startswith("# Cutting a repository over to kiln")
    found = re.findall(r"^(\d+)\. \*\*(.+?)\.?\*\*", text, re.MULTILINE)
    assert len(found) == len(STEPS)  # mdformat numbers every item `1.`
    for (_, heading), expected in zip(found, STEPS, strict=True):
        assert heading.replace("`", "").startswith(expected)


def test_s16_8_2_2_runbook_has_no_init() -> None:
    text = _text()

    for absent in ("kiln init", "backups/"):
        assert absent not in text
    for present in (
        "kiln new",
        "kiln diff --old",
        "byte-for-byte",
        "S16.3.1",
        "S17.2.1",
        "ADR-0019",
    ):
        assert present in text, present


def test_s16_8_2_3_table_format() -> None:
    assert "| File | What is lost | Verdict | Where it went |" in _text()


def test_s16_8_2_4_listed() -> None:
    index = (ROOT / "docs/runbooks/index.md").read_text(encoding="utf-8")

    assert "](cutover.md)" in index


def test_s16_6_13_5_runbook_names_migrate() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "node-lib" in text
    assert "nx migrate" in text
    assert "pnpm audit" in text


def test_s16_7_3_10_docs() -> None:
    assert "prettier@~3.9.10" in _flat()
    for page in (
        "docs/adr/ADR-0012.md",
        "docs/specs/epics/E9-node-archetypes/index.md",
        "docs/specs/epics/E9-node-archetypes/F9.2-one-node-scaffold.md",
        "docs/reference/standard-repo.md",
    ):
        text = " ".join((ROOT / page).read_text(encoding="utf-8").split())
        assert "Revised 2026-11-09 (S16.7.3)" in text, page


def _folded(page: str) -> str:
    return " ".join((ROOT / page).read_text(encoding="utf-8").split())


def test_s16_7_9_1_runbook_documents_the_library_step() -> None:
    text = _folded("docs/runbooks/creating-a-repo.md")
    for needle in (
        "nx g @nx/angular:library",
        "--publishable",
        "pnpm exec nx lint <n> --fix",
        "@angular/common",
        "@nx/dependency-checks",
    ):
        assert needle in text, needle
    assert not re.search(r"node-lib` \*\(deferred\)\*", text)


def test_s16_7_9_2_f9_2_records_the_supersession() -> None:
    text = _folded("docs/specs/epics/E9-node-archetypes/F9.2-one-node-scaffold.md")
    assert text.count("Revised 2026-11-09 (S16.7.9)") == 1


def test_s16_9_3_1_runbook_regenerates_the_nav() -> None:
    flat = _flat()
    start = flat.index("**Bring the files over.**")
    end = flat.index("**Read the diff file by file.**")
    step = flat[start:end]

    assert "mkdocs.yml" in step
    assert "task docs:generate" in step
    assert "`nav` is a derived region" in step


def test_s17_3_6_1_the_board_says_acceptance_is_tests() -> None:
    flat = " ".join((ROOT / "docs/specs/index.md").read_text(encoding="utf-8").split())

    for needle in (
        "Every acceptance item a script can check is a test named after the "
        "story, so `task validate` is the whole scripted check",
        "Paste the tail of `task validate` into the story's *What the build "
        "settled* block",
        "holds only what needs the owner's judgement",
        "never holds a shell script",
        "no column-aligned comments",
        "The owner has accepted F16.8 to F16.10",
    ):
        assert needle in flat


def test_s16_8_3_4_docs_name_no_adopt_prompt() -> None:
    docs = ROOT / "docs"
    skipped = {docs / d for d in ("specs", "plans", "adr", "releases")}
    for page in docs.rglob("*.md"):
        if any(parent in skipped for parent in page.parents):
            continue
        text = page.read_text(encoding="utf-8")
        assert "--name adopt" not in text, page
        assert "adopt prompt" not in text, page
    assert not (docs / "runbooks/adopting-a-repo.md").exists()
    for name in ("docs/runbooks/index.md", "mkdocs.yml"):
        assert "adopting-a-repo" not in (ROOT / name).read_text(encoding="utf-8")


def test_s16_8_3_5_cutover_step_8_keeps_its_gate() -> None:
    flat = _flat()
    for present in (
        "Reconcile and gate",
        "task validate",
        "KILN_DOCTOR_FULL=1 task validate",
        "task kiln:apply",
    ):
        assert present in flat, present
    assert "--name adopt" not in flat


def test_s16_9_12_4_runbook_drops_the_standard_exclude() -> None:
    flat = _flat()
    start = flat.index("**Bring the files over.**")
    end = flat.index("**Read the diff file by file.**")
    step = flat[start:end]

    assert ".mdformat.toml" in step
    assert "exclude" in step
