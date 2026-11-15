"""The dependency review job."""

from __future__ import annotations
import pytest
import re
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.artifacts import load_pins
from rn_forge.kiln.modules.cicd.checks import pins as pins_check
from rn_forge.kiln.modules.cicd.config import GENERATED_JOBS
from rn_forge.kiln.modules.core import cycle
from tests.modules.cicd import workflows
from tests.modules.cicd.support import (
    CALL,
    SECURITY_CELLS,
    _cell_root,
    _rendered,
    _root,
    _with_ci,
)


def _review_jobs(root: Path) -> dict[str, dict[str, object]]:
    return workflows.jobs(_rendered(root))


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_5_8_dependency_review_job(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    jobs = _review_jobs(_cell_root(tmp_path, archetype, extra))
    job = jobs["dependency-review"]
    assert job["if"] == "${{ github.event_name == 'pull_request' }}"
    assert job["needs"] == "validate"
    assert job["permissions"] == {"contents": "read"}
    assert isinstance(job["timeout-minutes"], int)
    assert job["runs-on"] == "ubuntu-latest"
    steps = job["steps"]
    assert len(steps) == 2  # type: ignore[arg-type]
    pins = load_pins()
    checkout, review = steps  # type: ignore[misc]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["persist-credentials"] is False
    assert review["uses"] == (
        f"{pins['dependency-review']['uses']}@{pins['dependency-review']['sha']}"
    )
    assert all("actions/setup" not in str(s.get("uses", "")) for s in steps)  # type: ignore[attr-defined]


def test_s4_11_5_8_dependency_review_is_pinned(tmp_path: Path) -> None:
    pin = load_pins()["dependency-review"]
    assert pin["uses"] == "actions/dependency-review-action"
    assert re.fullmatch(r"[0-9a-f]{40}", pin["sha"])
    assert pin["version"]
    for archetype, extra in SECURITY_CELLS:
        root = _cell_root(tmp_path / archetype, archetype, extra)
        cycle.apply(root, home=tmp_path / archetype / "home")
        assert pins_check.check(KilnConfig.load(root), root) == [], archetype


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_5_8_ci_ok_needs_dependency_review(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    jobs = _review_jobs(_cell_root(tmp_path, archetype, extra))
    assert "dependency-review" in jobs["checks-ok"]["needs"]  # type: ignore[operator]


def test_s4_11_5_8_declared_jobs_cannot_take_the_name(tmp_path: Path) -> None:
    assert "dependency-review" in GENERATED_JOBS
    extra = f'\n[[ci.jobs]]\nname = "dependency-review"\nuses = "{CALL}"\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)
