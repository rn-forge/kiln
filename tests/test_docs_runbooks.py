"""S16.3.1 — `docs/runbooks/cutover.md`: the one-time move onto kiln."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs/runbooks/cutover.md"
STEPS = (
    "Branch",
    "Run kiln init",
    "Read the diff file by file",
    "Record a verdict",
    "Land the absorb stories",
    "Bump [kiln] ref and run kiln apply",
    "Merge",
)


def _text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def test_s16_3_1_1_runbook_steps() -> None:
    text = _text()

    assert text.startswith("# Cutting a repository over to kiln")
    found = re.findall(r"^(\d+)\. \*\*(.+?)\.?\*\*", text, re.MULTILINE)
    assert len(found) == len(STEPS)  # mdformat numbers every item `1.`
    for (_, heading), expected in zip(found, STEPS, strict=True):
        assert heading.replace("`", "").startswith(expected)


def test_s16_3_1_2_table_format() -> None:
    assert "| File | What is lost | Verdict | Where it went |" in _text()


def test_s16_3_1_3_listed() -> None:
    index = (ROOT / "docs/runbooks/index.md").read_text(encoding="utf-8")

    assert "](cutover.md)" in index


# S16.6.6 — the runbook says what the rehearsal needed.


def _flat() -> str:
    return " ".join(_text().split())


def test_s16_6_6_1_origin() -> None:
    text = _flat()

    assert "Run it from a checkout whose `origin` is the repository" in text
    assert "the repository name comes from the `origin` remote" in text


def test_s16_6_6_2_python_lib_config() -> None:
    text = _flat()

    assert (
        "A `python-lib` passes `--config` with `packages`, `modules`, "
        "`import_contracts` and `[ci] release`"
    ) in text
    assert (
        "https://github.com/rn-forge/pykit/blob/main/docs/specs/epics/"
        "E16-kiln-adoption/F16.3-cutover.md"
    ) in text


def test_s16_6_6_3_old_workflows() -> None:
    text = _flat()

    assert "`init` exits 1 while the old workflows are present" in text
    assert "because its closing `kiln doctor` checks them" in text
    assert "Delete the old workflows now (`git rm .github/workflows/<old>.yml`)" in text
    assert "right after this read and before step 6" in text


def test_s16_6_6_4_steps_unchanged() -> None:
    found = re.findall(r"^(\d+)\. \*\*(.+?)\.?\*\*", _text(), re.MULTILINE)

    assert len(found) == len(STEPS)
    for (_, heading), expected in zip(found, STEPS, strict=True):
        assert heading.replace("`", "").startswith(expected)


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
