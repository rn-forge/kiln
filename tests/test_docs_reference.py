"""`docs/reference/standard-repo.md` describes the instruction-file split."""

from __future__ import annotations

import re
from pathlib import Path

from rn_forge.kiln import archetypes

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs/reference/standard-repo.md"


def _text() -> str:
    return " ".join(REFERENCE.read_text(encoding="utf-8").split())


def test_the_reference_matches() -> None:
    text = _text()
    assert "split by audience" in text
    assert (
        "`AGENTS.md` and `CLAUDE.md` are owner files, and kiln writes neither body"
        in text
    )
    assert "the bodies of `AGENTS.md`" not in text
    assert "`AGENTS.md` points at it" not in text


def test_the_reference_lists_the_yaml_check() -> None:
    text = _text()
    assert text.count("quality:lint:yaml") >= 2
    assert "every YAML file outside" in text


def test_reference_dependency_table_matches_manifests() -> None:
    text = REFERENCE.read_text(encoding="utf-8")
    section = text.split("## 3. The dependency set")[1].split(
        "## 4. The import boundary"
    )[0]
    rows = [line for line in section.splitlines() if line.startswith("| ")]
    for name in archetypes.shipped():
        matching = [r for r in rows if f"`{name}`" in r.split("|")[1]]
        assert matching, name
        dependencies = archetypes.load(name).dependencies
        for row in matching:
            for dependency in [*dependencies.required, *dependencies.allowed]:
                assert f"`{dependency}`" in row, (name, dependency)
            backend = re.search(r'backend = "(\w+)"', row.split("|")[1])
            if backend:
                assert f"`rn-forge-{backend.group(1)}`" in row, (name, row)
