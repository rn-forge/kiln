"""S15.1.4 — the CI page's checks matrix is a derived region."""

from __future__ import annotations

from pathlib import Path

from rn_forge.kiln.modules.cicd import registry
from rn_forge.kiln.modules.docs import generate

BEGIN = "<!-- BEGIN derived ci-matrix -->"
END = "<!-- END derived ci-matrix -->"


def _page(root: Path, body: str | None) -> Path:
    page = root / "docs" / "architecture" / "ci.md"
    page.parent.mkdir(parents=True)
    fence = "" if body is None else f"{BEGIN}\n{body}\n{END}\n"
    page.write_text(f"# CI\n\n{fence}", encoding="utf-8")
    return page


def test_s15_1_4_1_region_is_filled(tmp_path: Path) -> None:
    page = _page(tmp_path, "")
    generate.generate(tmp_path)
    assert registry.render_matrix(None) in page.read_text(encoding="utf-8")
    assert not generate.stale(tmp_path)


def test_s15_1_4_2_stale_is_reported(tmp_path: Path) -> None:
    _page(tmp_path, "old")
    findings = generate.stale(tmp_path)
    assert [f.path for f in findings] == ["docs/architecture/ci.md"]


def test_s15_1_4_3_absent_fence_is_ignored(tmp_path: Path) -> None:
    page = _page(tmp_path, None)
    before = page.read_text(encoding="utf-8")
    assert generate.generate(tmp_path) == ([], [])
    assert page.read_text(encoding="utf-8") == before
    assert not generate.stale(tmp_path)
