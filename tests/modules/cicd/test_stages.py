"""Stage names of the one-workflow contract (F15.8)."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

import pytest

from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd import CICD
from rn_forge.kiln.modules.tasks import TASKS

_spec = importlib.util.spec_from_file_location(
    "cicd_workflows", Path(__file__).with_name("workflows.py")
)
assert _spec is not None and _spec.loader is not None
workflows = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(workflows)

CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "{archetype}"

[docs]
profile = "mkdocs"

[ci]
provider = "github"
sonar = true
release = "{release}"
"""

PACKAGES = """
[archetype."python-lib"]
packages = ["packages/alpha", "packages/beta"]
"""


def _render(tmp_path: Path, archetype: str) -> dict[str, str]:
    root = tmp_path / archetype
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    release = "nx-dispatch" if archetype == "node-lib" else "tag-exists"
    text = CONFIG.format(archetype=archetype, release=release)
    if archetype == "python-lib":
        text += PACKAGES
    config.write_text(text, encoding="utf-8")
    loaded = KilnConfig.load(root)
    files = {a.path: a.content for a in CICD.artifacts(loaded, root)}
    files.update({a.path: a.content for a in TASKS.artifacts(loaded, root)})
    return files


def _jobs(tmp_path: Path, archetype: str) -> dict[str, dict[str, Any]]:
    return workflows.jobs(_render(tmp_path, archetype))


def test_s15_8_1_1_lib_jobs(tmp_path: Path) -> None:
    names = [n for n in _jobs(tmp_path, "python-lib") if n != "secret-scan"]
    assert names == [
        "validate",
        "dependency-review",
        "plan",
        "test",
        "integration",
        "smoke",
        "suites",
        "sonar",
        "release",
        "verify-release",
        "docs",
        "checks-ok",
        "ci-ok",
    ]


def test_s15_8_1_3_test_task(tmp_path: Path) -> None:
    files = _render(tmp_path, "python-lib")
    tasks = YamlUtils.load(files["tasks/ci.yml"])["tasks"]
    assert "test" in tasks and "verify" not in tasks
    assert "pytest" in "\n".join(tasks["test"]["cmds"])
    steps = _jobs(tmp_path, "python-lib")["test"]["steps"]
    assert any(s.get("run") == "task ci:test -- ${{ matrix.name }}" for s in steps)


def test_s15_8_1_4_node_jobs(tmp_path: Path) -> None:
    jobs = _jobs(tmp_path, "node-lib")
    assert {"test-cloud", "test-local", "smoke"} <= set(jobs)
    assert not {"ci-cloud", "ci-local", "package"} & set(jobs)
    for name in ("sonar", "smoke"):
        assert jobs[name]["needs"] == ["validate", "test-cloud", "test-local"]
    assert {"test-cloud", "test-local", "smoke"} <= set(jobs["checks-ok"]["needs"])
    files = _render(tmp_path, "node-lib")
    tasks = YamlUtils.load(files["tasks/ci.yml"])["tasks"]
    assert {"affected", "package"} <= set(tasks)
    smoke_runs = [s.get("run") for s in jobs["smoke"]["steps"]]
    assert "task ci:package" in smoke_runs


@pytest.mark.parametrize(
    "archetype",
    [
        "python-lib",
        "python-tool",
        "python-app",
        "python-web-api",
        "python-web-app",
        "node-lib",
    ],
)
def test_s15_8_1_5_no_old_name(tmp_path: Path, archetype: str) -> None:
    files = _render(tmp_path, archetype)
    text = "\n".join(
        c for p, c in files.items() if p.startswith((".github/", "tasks/"))
    )
    for old in (r"ci:verify(?![-\w])", "ci-cloud", "ci-local"):
        assert not re.search(old, text), old
    jobs = workflows.jobs(files)
    assert "package" not in jobs
    assert "verify" not in jobs


def test_s15_8_2_7_job(tmp_path: Path) -> None:
    jobs = _jobs(tmp_path, "python-lib")
    assert not {"postgres", "redis"} & set(jobs)
    job = jobs["integration"]
    assert job["strategy"]["matrix"] == {
        "include": "${{ fromJSON(needs.plan.outputs.integration) }}"
    }
    assert "needs.plan.outputs.integration != '[]'" in job["if"]
    runs = [s.get("run") for s in job["steps"]]
    assert "task ci:integration -- ${{ matrix.name }}" in runs
    assert "services" not in job
    upload = job["steps"][-1]
    assert upload["with"]["name"] == "ok-${{ matrix.marker }}"
    for name in ("sonar", "release", "ci-ok"):
        needs = jobs[name]["needs"]
        assert not {"postgres", "redis"} & set(needs), name
    assert "integration" in jobs["sonar"]["needs"]
    assert "integration" in jobs["checks-ok"]["needs"]


def test_s15_8_2_8_task(tmp_path: Path) -> None:
    tasks = YamlUtils.load(_render(tmp_path, "python-lib")["tasks/ci.yml"])["tasks"]
    assert tasks["integration"]["cmds"] == ["{{.DEVOPS}} integration {{.CLI_ARGS}}"]
    assert not {"postgres", "redis"} & set(tasks)


# S15.8.3 — single-package Python archetypes get a plan of one.

SINGLE = ("python-tool", "python-app", "python-web-api", "python-web-app")
STAGES = ("plan", "test", "integration", "smoke", "suites")


def _render_single(tmp_path: Path, archetype: str, extra: str = "") -> dict[str, str]:
    root = tmp_path / archetype
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    text = CONFIG.format(archetype=archetype, release="tag-exists")
    if archetype in {"python-web-api", "python-web-app"}:
        text += f'\n[archetype."{archetype}"]\n'
        if archetype == "python-web-app":
            text += 'frontend = "angular"\n'
    config.write_text(text + extra, encoding="utf-8")
    loaded = KilnConfig.load(root)
    files = {a.path: a.content for a in CICD.artifacts(loaded, root)}
    files.update({a.path: a.content for a in TASKS.artifacts(loaded, root)})
    return files


@pytest.mark.parametrize("archetype", SINGLE)
def test_s15_8_3_3_jobs(tmp_path: Path, archetype: str) -> None:
    lib = _jobs(tmp_path, "python-lib")
    jobs = workflows.jobs(_render_single(tmp_path, archetype))
    # Only a repository with two members checks their internal ranges.
    lib["plan"]["steps"] = [
        s for s in lib["plan"]["steps"] if s["name"] != "Check internal ranges"
    ]
    for stage in STAGES:
        assert jobs[stage] == lib[stage], stage
    validate = [s.get("run") for s in jobs["validate"]["steps"]]
    assert "task ci:validate" in validate
    assert "task ci:adapters" not in validate


@pytest.mark.parametrize("archetype", SINGLE)
def test_s15_8_3_4_validate_task(tmp_path: Path, archetype: str) -> None:
    files = _render_single(tmp_path, archetype)
    tasks = YamlUtils.load(files["tasks/ci.yml"])["tasks"]
    assert tasks["validate"]["cmds"] == [
        {"task": ":lint"},
        {"task": ":typecheck"},
        {"task": ":docs:build"},
    ]
    assert tasks["test"]["cmds"] == [{"task": ":test"}]
    assert {"plan", "integration", "smoke", "suite"} <= set(tasks)
    root = YamlUtils.load(files["Taskfile.yml"])["tasks"]
    assert {"task": "node:test"} in root["test"]["cmds"] or archetype != (
        "python-web-app"
    )


@pytest.mark.parametrize("archetype", SINGLE)
def test_s15_8_3_5_needs(tmp_path: Path, archetype: str) -> None:
    jobs = workflows.jobs(_render_single(tmp_path, archetype))
    assert jobs["sonar"]["needs"] == ["validate", "test", "integration", "smoke"]
    assert jobs["checks-ok"]["needs"] == [
        "validate",
        "dependency-review",
        "plan",
        "test",
        "integration",
        "smoke",
        "suites",
        "sonar",
        "secret-scan",
    ]
    assert jobs["release"]["needs"] == ["plan", "checks-ok"]
    assert jobs["ci-ok"]["needs"] == ["checks-ok", "release", "verify-release"]


@pytest.mark.parametrize("archetype", SINGLE)
def test_s15_8_3_6_suites_are_declared(tmp_path: Path, archetype: str) -> None:
    suites = workflows.jobs(_render_single(tmp_path, archetype))["suites"]
    assert suites["strategy"]["matrix"] == {
        "include": "${{ fromJSON(needs.plan.outputs.suites) }}"
    }
    assert "needs.plan.outputs.suites != '[]'" in suites["if"]


# S15.8.4 — `verify-release` for every Python archetype.


def _lib_files(tmp_path: Path, release: str) -> dict[str, str]:
    root = tmp_path / f"lib-{release}"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        CONFIG.format(archetype="python-lib", release=release) + PACKAGES,
        encoding="utf-8",
    )
    loaded = KilnConfig.load(root)
    files = {a.path: a.content for a in CICD.artifacts(loaded, root)}
    files.update({a.path: a.content for a in TASKS.artifacts(loaded, root)})
    return files


def test_s15_8_4_3_task(tmp_path: Path) -> None:
    for release, source in (("tag-exists", "git"), ("pypi", "pypi")):
        tasks = YamlUtils.load(_lib_files(tmp_path, release)["tasks/ci.yml"])["tasks"]
        assert tasks["verify-release"]["cmds"] == [
            f"{{{{.DEVOPS}}}} verify-release --source {source} {{{{.CLI_ARGS}}}}"
        ]
        assert "external-install" not in tasks
    for archetype in SINGLE:
        tasks = YamlUtils.load(_render_single(tmp_path, archetype)["tasks/ci.yml"])[
            "tasks"
        ]
        assert "verify-release" in tasks
        assert "external-install" not in tasks


def test_s15_8_4_4_lib_job(tmp_path: Path) -> None:
    jobs = workflows.jobs(_lib_files(tmp_path, "tag-exists"))
    assert "external-install" not in jobs
    job = jobs["verify-release"]
    assert job["needs"] == ["release"]
    assert job["if"] == (
        "${{ !cancelled() && needs.release.result == 'success' && "
        "github.event_name == 'push' && github.ref_name == 'main' }}"
    )
    assert job["steps"][-1]["run"] == "task ci:verify-release"


@pytest.mark.parametrize("archetype", SINGLE)
def test_s15_8_4_5_single_package_job(tmp_path: Path, archetype: str) -> None:
    jobs = workflows.jobs(_render_single(tmp_path, archetype))
    tag = (
        "${{ steps.check.outputs.should-release == 'true' "
        "&& steps.check.outputs.tag || '' }}"
    )
    assert jobs["release"]["outputs"] == {"tag": tag}
    job = jobs["verify-release"]
    assert job["needs"] == ["release"]
    assert "needs.release.outputs.tag != ''" in job["if"]
    assert "!cancelled()" in job["if"]
    last = job["steps"][-1]
    assert last["run"] == 'task ci:verify-release -- "$TAG"'
    assert last["env"]["TAG"] == "${{ needs.release.outputs.tag }}"


def test_s15_8_4_6_none(tmp_path: Path) -> None:
    assert "verify-release" not in workflows.jobs(_lib_files(tmp_path, "none"))
    root = tmp_path / "single-none"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        CONFIG.format(archetype="python-tool", release="none"), encoding="utf-8"
    )
    loaded = KilnConfig.load(root)
    files = {a.path: a.content for a in CICD.artifacts(loaded, root)}
    jobs = workflows.jobs(files)
    assert "verify-release" not in jobs
    assert "verify-release" not in jobs["ci-ok"]["needs"]
