"""The `umbrella` job and the umbrella release."""

from __future__ import annotations
import pytest
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from tests.modules.cicd.support import (
    ARCHETYPES,
    _ci_jobs,
    _ci_tasks_text_of,
    _rendered,
    _root,
    _sonar_root,
)


UMBRELLA_ARCHETYPES = (*ARCHETYPES, "python-web-api", "python-web-app")


UMBRELLA_IF = (
    "${{ !cancelled() && needs.checks-ok.result == 'success' && "
    "needs.release.result != 'failure' && github.event_name == 'push' && "
    "github.ref == 'refs/heads/main' }}"
)


def _umbrella_root(
    tmp_path: Path, archetype: str, on: bool, evidence: bool = False
) -> Path:
    root = _sonar_root(tmp_path, archetype)
    if on:
        config = root / ".rn-forge" / "kiln" / "config.toml"
        extra = "release-evidence = true\n" if evidence else ""
        config.write_text(
            config.read_text(encoding="utf-8")
            + f"\n[ci.checks]\numbrella-release = true\n{extra}",
            encoding="utf-8",
        )
    return root


def _umbrella_files(
    root: Path,
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    jobs = _ci_jobs(root)
    return jobs, _ci_tasks_text_of(root)["tasks"]  # type: ignore[return-value]


@pytest.mark.parametrize("archetype", [*UMBRELLA_ARCHETYPES, "node-lib"])
def test_off_by_default(tmp_path: Path, archetype: str) -> None:
    jobs, tasks = _umbrella_files(_umbrella_root(tmp_path, archetype, False))
    assert "umbrella" not in jobs
    assert "release:umbrella" not in tasks


@pytest.mark.parametrize("archetype", UMBRELLA_ARCHETYPES)
def test_umbrella_job_when_enabled(tmp_path: Path, archetype: str) -> None:
    jobs, tasks = _umbrella_files(_umbrella_root(tmp_path, archetype, True))
    job = jobs["umbrella"]
    assert job["needs"] == ["checks-ok", "release"]
    assert job["permissions"] == {"contents": "write"}
    assert job["concurrency"] == {"group": "release", "cancel-in-progress": False}
    steps = job["steps"]
    assert "actions/checkout" in steps[0]["uses"]  # type: ignore[index]
    assert steps[1]["uses"] == "./.github/actions/setup"  # type: ignore[index]
    assert steps[2]["run"] == "task ci:release:umbrella"  # type: ignore[index]
    assert len(steps) == 3  # type: ignore[arg-type]
    assert steps[2]["env"] == {"GH_TOKEN": "${{ github.token }}"}  # type: ignore[index]
    for name, other in jobs.items():
        if name != "umbrella":
            assert "umbrella" not in str(other.get("steps", "")), name
    assert tasks["release:umbrella"]["cmds"] == [  # type: ignore[index]
        '{{.DEVOPS}} umbrella --sha "$GITHUB_SHA"'
    ]


@pytest.mark.parametrize("archetype", UMBRELLA_ARCHETYPES)
def test_umbrella_attaches_evidence_when_both_checks_are_on(
    tmp_path: Path, archetype: str
) -> None:
    jobs, tasks = _umbrella_files(_umbrella_root(tmp_path, archetype, True, True))
    assert jobs["umbrella"]["permissions"] == {"contents": "write", "actions": "read"}
    command = tasks["release:umbrella"]["cmds"][0]  # type: ignore[index]
    assert command.endswith(" --evidence")


@pytest.mark.parametrize("archetype", UMBRELLA_ARCHETYPES)
def test_needs_a_release(tmp_path: Path, archetype: str) -> None:
    root = _umbrella_root(tmp_path, archetype, True)
    config = root / ".rn-forge" / "kiln" / "config.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text + '\n[ci]\nrelease = "none"\n'
        if "[ci]" not in text
        else text.replace('release = "tag-exists"', 'release = "none"'),
        encoding="utf-8",
    )
    with pytest.raises(
        AppException,
        match=r"cicd\.render: ci\.checks\.umbrella-release needs \[ci\] release other than none",
    ):
        _rendered(root)


@pytest.mark.parametrize("archetype", UMBRELLA_ARCHETYPES)
def test_docs_only_shipped_transition(tmp_path: Path, archetype: str) -> None:
    jobs = _ci_jobs(_umbrella_root(tmp_path, archetype, True))
    assert jobs["umbrella"]["if"] == UMBRELLA_IF
    assert "release-order" not in str(jobs["umbrella"]["if"])
    if archetype == "python-lib":
        assert "release-order != '[]'" in str(jobs["release"]["if"])


@pytest.mark.parametrize("archetype", UMBRELLA_ARCHETYPES)
def test_umbrella_is_needed_by_ci_ok_only_when_enabled(
    tmp_path: Path, archetype: str
) -> None:
    on = _ci_jobs(_umbrella_root(tmp_path / "on", archetype, True))
    assert "umbrella" in on["ci-ok"]["needs"]  # type: ignore[operator]
    off = _ci_jobs(_umbrella_root(tmp_path / "off", archetype, False))
    assert "umbrella" not in off["ci-ok"]["needs"]  # type: ignore[operator]


def test_node_lib_off_by_default(tmp_path: Path) -> None:
    jobs, tasks = _umbrella_files(_umbrella_root(tmp_path, "node-lib", False))
    assert "umbrella" not in jobs
    assert "release:umbrella" not in tasks


def test_node_lib_on(tmp_path: Path) -> None:
    jobs, tasks = _umbrella_files(_umbrella_root(tmp_path, "node-lib", True))
    job = jobs["umbrella"]
    assert job["needs"] == ["checks-ok", "release"]
    assert job["if"] == UMBRELLA_IF
    assert job["permissions"] == {"contents": "write"}
    assert job["concurrency"] == {"group": "release", "cancel-in-progress": False}
    steps = job["steps"]
    assert steps[2]["run"] == "task ci:release:umbrella"  # type: ignore[index]
    assert len(steps) == 3  # type: ignore[arg-type]
    for name, other in jobs.items():
        if name != "umbrella":
            assert "umbrella" not in str(other.get("steps", "")), name
    assert "umbrella" in jobs["ci-ok"]["needs"]  # type: ignore[operator]
    assert "release:umbrella" in tasks
    # `released` mode is the docs-only push: `release` still succeeds, its tag
    # output is empty, and `umbrella` (which needs `release`, not
    # `verify-release`) runs on `release.result != 'failure'`.
    release_steps = str(jobs["release"]["steps"])
    assert "steps.state.outputs.mode == 'released'" in release_steps
    assert "verify-release" not in job["needs"]  # type: ignore[operator]


def test_the_setup_action_follows_the_constant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    path = ".github/actions/setup/action.yml"
    assert 'python-version: "3.14"' in _rendered(root)[path]

    monkeypatch.setattr(
        "rn_forge.kiln.modules.cicd.artifacts.PYTHON_VERSION", "3.99", raising=False
    )

    assert 'python-version: "3.99"' in _rendered(root)[path]
