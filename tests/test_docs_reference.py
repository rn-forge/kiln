"""S16.10.6 — `docs/reference/standard-repo.md` describes the instruction-file split."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs/reference/standard-repo.md"


def _text() -> str:
    return " ".join(REFERENCE.read_text(encoding="utf-8").split())


def test_s16_10_6_3_the_reference_matches() -> None:
    text = _text()
    assert "split by audience" in text
    assert "`@AGENTS.md`" in text
    assert "`AGENTS.md` points at it" not in text
