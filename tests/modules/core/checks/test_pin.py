"""`kiln.pin` — the running kiln is the one the repository pins."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Severity

from rn_forge.kiln import __version__
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig
from rn_forge.kiln.modules.core.checks import pin


def run(root: Path, extra: str = "") -> list:
    path = root / CONFIG_PATH
    path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")
    return pin.check(KilnConfig.load(root), root)


def test_s7_4_3_1_matching_tag_is_clean(repo) -> None:
    assert run(repo(), f'\n[kiln]\nref = "v{__version__}"\n') == []


def test_s7_4_3_2_other_tag_is_a_mismatch(repo) -> None:
    findings = run(repo(), '\n[kiln]\nref = "v0.0.1"\n')
    assert [(f.code, f.severity) for f in findings] == [(pin.MISMATCH, Severity.ERROR)]
    message = findings[0].message
    assert "0.0.1" in message
    assert __version__ in message
    assert "task" in message
    assert "[kiln] ref" in message


def test_s7_4_3_3_branch_ref_is_not_checked(repo) -> None:
    assert run(repo(), '\n[kiln]\nref = "feature/v1"\n') == []


def test_s7_4_3_4_missing_pin_is_a_warning(repo) -> None:
    findings = run(repo())
    assert [(f.code, f.severity) for f in findings] == [(pin.MISSING, Severity.WARNING)]


def test_s7_4_3_5_kiln_itself_needs_no_pin(repo) -> None:
    assert run(repo(), '\n[archetype."python-app"]\nmodule = "rn_forge.kiln"\n') == []
