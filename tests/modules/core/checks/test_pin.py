"""`kiln.pin` — the running kiln is the one the repository pins."""

from __future__ import annotations

from pathlib import Path

import pytest
from rn_forge.commons.findings import Severity

from tests.conftest import INSTALLED_COMMIT, run_check

from rn_forge.kiln import __version__
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig
from rn_forge.kiln.modules.core.checks import pin


def run(root: Path, extra: str = "") -> list:
    path = root / CONFIG_PATH
    path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")
    return pin.check(KilnConfig.load(root), root)


def test_matching_tag_is_clean(repo) -> None:
    assert run(repo(), f'\n[kiln]\nref = "v{__version__}"\n') == []


def test_other_tag_is_a_mismatch(repo) -> None:
    findings = run(repo(), '\n[kiln]\nref = "v0.0.1"\n')
    assert [(f.code, f.severity) for f in findings] == [(pin.MISMATCH, Severity.ERROR)]
    message = findings[0].message
    assert "0.0.1" in message
    assert __version__ in message
    assert "task" in message
    assert "[kiln] ref" in message


def test_sha_ref_is_not_checked(repo, kiln_remote_sha: str) -> None:
    assert run(repo(), f'\n[kiln]\nref = "{kiln_remote_sha}"\n') == []


def test_sha_pin_other_than_the_installed_commit_is_a_mismatch(
    repo, fake_install, kiln_remote_sha: str
) -> None:
    fake_install()
    findings = run(repo(), f'\n[kiln]\nref = "{kiln_remote_sha}"\n')
    assert [(f.code, f.severity) for f in findings] == [(pin.MISMATCH, Severity.ERROR)]
    message = findings[0].message
    assert kiln_remote_sha[:12] in message
    assert INSTALLED_COMMIT[:12] in message
    assert "task" in message
    assert "[kiln] ref" in message


def test_sha_pin_matching_the_installed_commit_is_clean(
    repo, fake_install, kiln_remote_sha: str
) -> None:
    fake_install(kiln_remote_sha)
    assert run(repo(), f'\n[kiln]\nref = "{kiln_remote_sha}"\n') == []


def test_other_tag_is_a_mismatch_from_an_install(repo, fake_install) -> None:
    fake_install()
    findings = run(repo(), '\n[kiln]\nref = "v0.0.1"\n')
    assert [(f.code, f.severity) for f in findings] == [(pin.MISMATCH, Severity.ERROR)]


def test_missing_pin_is_a_warning(repo) -> None:
    findings = run(repo())
    assert [(f.code, f.severity) for f in findings] == [(pin.MISSING, Severity.WARNING)]


def test_kiln_itself_needs_no_pin(repo) -> None:
    assert run(repo(), '\n[archetype."python-app"]\nmodule = "rn_forge.kiln"\n') == []


def test_pin_runs_through_the_registry(repo) -> None:
    run_check(pin.NAME, repo())
