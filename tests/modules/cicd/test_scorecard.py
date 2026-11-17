"""`scorecard.yml` and its Dependabot entry."""

from __future__ import annotations
import pytest
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.pins import load_pins
from rn_forge.kiln.modules.cicd.config import GENERATED_JOBS
from tests.modules.cicd.support import (
    ARCHETYPES,
    CALL,
    _ci_jobs,
    _codes,
    _rendered,
    _root,
    _updates,
    _with_ci,
)


SCORECARD = ".github/workflows/scorecard.yml"


def _scorecard_root(tmp_path: Path, archetype: str) -> Path:
    return _with_ci(_root(tmp_path, archetype), "\n[ci.checks]\nscorecard = true\n")


@pytest.mark.parametrize("archetype", [*ARCHETYPES, "node-lib"])
def test_s15_6_1_1_absent_by_default(tmp_path: Path, archetype: str) -> None:
    assert SCORECARD not in _rendered(_root(tmp_path, archetype))


@pytest.mark.parametrize("archetype", [*ARCHETYPES, "node-lib"])
def test_s15_6_1_2_on(tmp_path: Path, archetype: str) -> None:
    workflow = YamlUtils.load(
        _rendered(_scorecard_root(tmp_path, archetype))[SCORECARD]
    )
    assert workflow["on"]["schedule"] == [{"cron": "17 4 * * 1"}]
    assert "workflow_dispatch" in workflow["on"]
    assert list(workflow["jobs"]) == ["analysis"]
    job = workflow["jobs"]["analysis"]
    assert job["permissions"] == {
        "contents": "read",
        "actions": "read",
        "id-token": "write",
        "security-events": "write",
    }
    pins = load_pins()
    checkout, scan, upload = job["steps"]
    assert checkout["uses"] == f"{pins['checkout']['uses']}@{pins['checkout']['sha']}"
    assert checkout["with"] == {"persist-credentials": False}
    assert scan["uses"] == f"{pins['scorecard']['uses']}@{pins['scorecard']['sha']}"
    assert scan["with"] == {
        "results_file": "results.sarif",
        "results_format": "sarif",
        "publish_results": True,
    }
    assert (
        upload["uses"]
        == f"{pins['upload-sarif']['uses']}@{pins['upload-sarif']['sha']}"
    )
    assert upload["uses"].startswith("github/codeql-action/upload-sarif@")
    assert upload["with"] == {"sarif_file": "results.sarif"}


@pytest.mark.parametrize("archetype", [*ARCHETYPES, "node-lib"])
def test_s15_6_1_3_not_gating(tmp_path: Path, archetype: str) -> None:
    jobs = _ci_jobs(_scorecard_root(tmp_path, archetype))
    assert "scorecard" not in jobs
    assert "scorecard" not in jobs["ci-ok"]["needs"]


@pytest.mark.parametrize("archetype", [*ARCHETYPES, "node-lib"])
def test_s15_6_1_4_pins(tmp_path: Path, archetype: str) -> None:
    root = _scorecard_root(tmp_path, archetype)
    assert "ci.unpinned" not in _codes(root)
    assert "ci.permissions" not in _codes(root)
    rendered = _rendered(root)[SCORECARD]
    pins = load_pins()
    for key in ("scorecard", "upload-sarif"):
        assert f"@{pins[key]['sha']} # {pins[key]['version']}" in rendered


def test_s15_6_1_5_generated_job_name(tmp_path: Path) -> None:
    assert "scorecard" in GENERATED_JOBS
    extra = f'\n[[ci.jobs]]\nname = "scorecard"\nuses = "{CALL}"\n'
    root = _with_ci(_root(tmp_path, "python-lib"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)


def _actions_entry(root: Path) -> dict[str, object]:
    return _updates(root)["github-actions"]


def _unique_uses(pins: dict[str, dict[str, str]]) -> list[str]:
    return sorted(
        {"/".join(t["uses"].split("/")[:2]) for t in pins.values() if "uses" in t}
    )


@pytest.mark.parametrize("archetype", ARCHETYPES + ("node-lib",))
def test_s15_7_1_1_github_actions_entry(tmp_path: Path, archetype: str) -> None:
    updates = _updates(_root(tmp_path, archetype))
    entry = updates["github-actions"]
    assert entry["directory"] == "/"
    for key in ("schedule", "cooldown"):
        assert entry[key] == updates["uv"][key]
    assert next(iter(entry["groups"].values())) == next(  # type: ignore[attr-defined]
        iter(updates["uv"]["groups"].values())  # type: ignore[attr-defined]
    )


@pytest.mark.parametrize("archetype", ARCHETYPES + ("node-lib",))
def test_s15_7_1_2_ignore_covers_every_pin(tmp_path: Path, archetype: str) -> None:
    names = [
        i["dependency-name"]
        for i in _actions_entry(_root(tmp_path, archetype))["ignore"]
    ]  # type: ignore[attr-defined,index]
    assert names == sorted(set(names))
    assert names == _unique_uses(load_pins())
    assert "actions/checkout" in names
    assert "github/codeql-action" in names
    assert not any(n.count("/") != 1 for n in names)


def test_s15_7_1_3_new_pin_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pins = load_pins() | {"extra": {"uses": "x/y", "sha": "0" * 40, "version": "v1"}}
    monkeypatch.setattr("rn_forge.kiln.modules.cicd.artifacts.load_pins", lambda: pins)
    names = [i["dependency-name"] for i in _actions_entry(_root(tmp_path))["ignore"]]  # type: ignore[attr-defined,index]
    assert "x/y" in names
