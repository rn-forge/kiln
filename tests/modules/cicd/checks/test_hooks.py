"""S4.11.1 — `ci-hooks`: each `[ci.hooks]` action and declared job names a file that exists."""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.checks import hooks

HOOK = "./.github/actions/a"
CALL = "./.github/workflows/x.yml"


def _codes(root: Path) -> list[str]:
    return sorted(f.code for f in hooks.check(KilnConfig.load(root), root))


def _append(root: Path, text: str) -> None:
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(config.read_text(encoding="utf-8") + text, encoding="utf-8")


def _hook(root: Path) -> None:
    _append(root, f'\n[ci.hooks]\nsetup = ["{HOOK}"]\n')


def _job(root: Path) -> None:
    _append(root, f'\n[[ci.jobs]]\nname = "x"\nuses = "{CALL}"\n')


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_s4_11_1_9_missing_hook_action_is_reported(repo) -> None:
    root = repo()
    _hook(root)
    assert _codes(root) == ["ci.hook-missing"]


def test_s4_11_1_9_a_yaml_hook_action_is_found(repo) -> None:
    root = repo()
    _hook(root)
    _write(root, ".github/actions/a/action.yaml", "name: a\n")
    assert _codes(root) == []


def test_s4_11_1_9_missing_job_workflow_is_reported(repo) -> None:
    root = repo()
    _job(root)
    assert _codes(root) == ["ci.hook-missing"]


@pytest.mark.parametrize("on", ["on: push", "on: [push]", "on: {pull_request: {}}"])
def test_s4_11_1_9_job_workflow_without_workflow_call_is_reported(
    repo, on: str
) -> None:
    root = repo()
    _job(root)
    _write(root, ".github/workflows/x.yml", f"{on}\njobs: {{}}\n")
    assert _codes(root) == ["ci.hook-not-callable"]


@pytest.mark.parametrize(
    "on",
    ["on: workflow_call", "on: [push, workflow_call]", "on: {workflow_call: {}}"],
)
def test_s4_11_1_9_workflow_call_in_any_form_passes(repo, on: str) -> None:
    root = repo()
    _job(root)
    _write(root, ".github/workflows/x.yml", f"{on}\njobs: {{}}\n")
    assert _codes(root) == []


def test_s4_11_1_9_all_present_is_clean(repo) -> None:
    root = repo()
    _hook(root)
    _job(root)
    _write(root, ".github/actions/a/action.yml", "name: a\n")
    _write(root, ".github/workflows/x.yml", "on: workflow_call\njobs: {}\n")
    assert _codes(root) == []


def test_s4_11_1_9_no_hooks_or_jobs_is_clean(repo) -> None:
    assert _codes(repo()) == []


def test_s4_11_1_9_the_check_is_registered() -> None:
    assert "ci-hooks" in checks.names()
