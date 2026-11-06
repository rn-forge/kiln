"""Stage names of the one-workflow contract (F15.8)."""

from __future__ import annotations

import importlib.util
import json
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
    assert jobs["smoke"]["needs"] == ["validate", "test-cloud", "test-local"]
    assert jobs["sonar"]["needs"] == ["validate", "test-cloud", "test-local", "smoke"]
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
    assert jobs["sonar"]["needs"] == [
        "validate",
        "test",
        "integration",
        "smoke",
        "suites",
    ]
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
    assert jobs["ci-ok"]["needs"] == [
        "checks-ok",
        "release",
        "verify-release",
        "docs",
    ]


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


# S15.8.5 — `node-lib` releases from `ci.yml`.

RELEASE_TASKS = (
    "state",
    "author",
    "tag",
    "verify",
    "push",
    "github",
    "publish",
    "finalize",
    "latest",
)


def _node(tmp_path: Path, release: str = "nx-dispatch") -> dict[str, str]:
    root = tmp_path / f"node-{release}"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        CONFIG.format(archetype="node-lib", release=release), encoding="utf-8"
    )
    loaded = KilnConfig.load(root)
    files = {a.path: a.content for a in CICD.artifacts(loaded, root)}
    files.update({a.path: a.content for a in TASKS.artifacts(loaded, root)})
    return files


def test_s15_8_5_1_no_release_yml(tmp_path: Path) -> None:
    files = _node(tmp_path)
    assert ".github/workflows/release.yml" not in files
    assert not [p for p in files if p.endswith("/release.yml")]


def test_s15_8_5_2_release_job(tmp_path: Path) -> None:
    job = workflows.jobs(_node(tmp_path))["release"]
    assert job["needs"] == ["checks-ok"]
    assert job["if"] == (
        "${{ !cancelled() && needs.checks-ok.result == 'success' && "
        "github.event_name == 'push' && github.ref == 'refs/heads/main' }}"
    )
    assert job["concurrency"] == {"group": "release", "cancel-in-progress": False}
    assert job["permissions"] == {"contents": "write", "id-token": "write"}
    assert "tag" in job["outputs"]
    runs = [s.get("run", "") for s in job["steps"]]
    assert [r for r in runs if r.startswith("task ")] == [
        f"task ci:release:{name}" for name in RELEASE_TASKS
    ]
    text = json.dumps(job)
    assert "inputs." not in text
    assert "ci:release:gate" not in text and "ci:release:version" not in text
    assert job["steps"][0]["id"] == "app-token"
    assert job["steps"][1]["with"]["token"] == "${{ steps.app-token.outputs.token }}"


def test_s15_8_5_4_modes_gate_the_steps(tmp_path: Path) -> None:
    job = workflows.jobs(_node(tmp_path))["release"]
    by_run = {s.get("run"): s for s in job["steps"]}
    new = "${{ steps.state.outputs.mode == 'new' }}"
    not_released = "${{ steps.state.outputs.mode != 'released' }}"
    assert by_run["task ci:release:tag"]["if"] == new
    assert by_run["task ci:release:push"]["if"] == new
    for name in ("author", "verify", "github", "publish", "finalize", "latest"):
        assert by_run[f"task ci:release:{name}"]["if"] == not_released, name
    assert "if" not in by_run["task ci:release:state"]
    notice = by_run['echo "::notice::$TAG is already released"']
    assert notice["if"] == "${{ steps.state.outputs.mode == 'released' }}"
    assert job["outputs"]["tag"] == (
        "${{ steps.state.outputs.mode != 'released' && steps.state.outputs.tag || '' }}"
    )


def test_s15_8_5_6_publish_flags(tmp_path: Path) -> None:
    job = workflows.jobs(_node(tmp_path))["release"]
    publish = next(s for s in job["steps"] if s.get("run") == "task ci:release:publish")
    assert publish["env"] == {
        "DIST_TAG": "${{ steps.state.outputs.dist-tag }}",
        "FIRST_RELEASE_FLAG": (
            "${{ steps.state.outputs.first-release == 'true' && '--first-release' || '' }}"
        ),
    }
    assert "DRY_RUN" not in json.dumps(job)


def test_s15_8_5_7_version_task(tmp_path: Path) -> None:
    files = _node(tmp_path)
    root = YamlUtils.load(files["Taskfile.yml"])["tasks"]
    assert root["version"]["cmds"] == [{"task": "ci:version"}]
    cmds = "\n".join(YamlUtils.load(files["tasks/ci.yml"])["tasks"]["version"]["cmds"])
    assert (
        "pnpm exec nx release version {{.CLI_ARGS}} --git-commit=false "
        "--git-tag=false --stage-changes=false"
    ) in cmds


def test_s15_8_5_8_verify_release(tmp_path: Path) -> None:
    files = _node(tmp_path)
    jobs = workflows.jobs(files)
    job = jobs["verify-release"]
    assert job["needs"] == ["release"]
    assert "needs.release.outputs.tag != ''" in job["if"]
    assert job["steps"][-1]["run"] == "task ci:verify-release"
    assert job["steps"][-1]["env"]["TAG"] == "${{ needs.release.outputs.tag }}"
    tasks = YamlUtils.load(files["tasks/ci.yml"])["tasks"]
    assert "verify-release" in tasks and "published-install" not in tasks
    assert "gh release download" in "\n".join(tasks["verify-release"]["cmds"])


def test_s15_8_5_9_ci_ok(tmp_path: Path) -> None:
    jobs = workflows.jobs(_node(tmp_path))
    assert jobs["ci-ok"]["needs"] == ["checks-ok", "release", "verify-release", "docs"]
    none = _node(tmp_path, "none")
    jobs = workflows.jobs(none)
    assert not {"release", "verify-release"} & set(jobs)
    assert jobs["ci-ok"]["needs"] == ["checks-ok", "docs"]
    tasks = YamlUtils.load(none["tasks/ci.yml"])["tasks"]
    assert not [t for t in tasks if t.startswith("release:") or t == "verify-release"]


def test_s15_8_5_10_no_dispatch_inputs(tmp_path: Path) -> None:
    files = _node(tmp_path)
    for path, text in files.items():
        if not path.startswith(".github/workflows/"):
            continue
        triggers = YamlUtils.load(text).get("on") or {}
        inputs = (triggers.get("workflow_dispatch") or {}).get("inputs") or {}
        assert not {
            "specifier",
            "exact-version",
            "dist-tag",
            "dry-run",
            "first-release",
        } & set(inputs), path
    jobs = workflows.jobs(files)
    assert "github.event_name == 'push'" in jobs["release"]["if"]


# S15.8.6 — `docs` is a stage of `ci.yml`.

DOCS_IF = (
    "${{ !cancelled() && needs.checks-ok.result == 'success' "
    "&& !contains(needs.*.result, 'failure') "
    "&& !contains(needs.*.result, 'cancelled') "
    "&& github.event_name == 'push' && github.ref_name == 'main' }}"
)
PLAN_TERM = "&& needs.plan.outputs.docs == 'true' "
ALL_ARCHETYPES = (*SINGLE, "python-lib", "node-lib")


def _docs_render(
    tmp_path: Path,
    archetype: str,
    release: str,
    *,
    sonar: bool = True,
    docs: bool = True,
    extra: str = "",
) -> dict[str, str]:
    root = tmp_path / f"{archetype}-{release}-{sonar}-{docs}"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    text = CONFIG.format(archetype=archetype, release=release)
    text = text.replace("sonar = true", f"sonar = {str(sonar).lower()}")
    if not docs:
        text = text.replace('[docs]\nprofile = "mkdocs"', '[docs]\nprofile = "none"')
    if archetype == "python-lib":
        text += PACKAGES
    elif archetype in {"python-web-api", "python-web-app"}:
        text += f'\n[archetype."{archetype}"]\n'
        if archetype == "python-web-app":
            text += 'frontend = "angular"\n'
    config.write_text(text + extra, encoding="utf-8")
    loaded = KilnConfig.load(root)
    files = {a.path: a.content for a in CICD.artifacts(loaded, root)}
    files.update({a.path: a.content for a in TASKS.artifacts(loaded, root)})
    return files


def _release_for(archetype: str, release: str) -> str:
    if release == "none":
        return "none"
    return {"python-lib": "pypi", "node-lib": "nx-dispatch"}.get(archetype, release)


@pytest.mark.parametrize("archetype", ALL_ARCHETYPES)
@pytest.mark.parametrize("release", ["tag-exists", "none"])
def test_s15_8_6_1_no_docs_yml(tmp_path: Path, archetype: str, release: str) -> None:
    files = _docs_render(tmp_path, archetype, _release_for(archetype, release))
    assert ".github/workflows/docs.yml" not in files


@pytest.mark.parametrize("archetype", SINGLE)
def test_s15_8_6_2_job(tmp_path: Path, archetype: str) -> None:
    job = workflows.jobs(_docs_render(tmp_path, archetype, "tag-exists"))["docs"]
    assert job["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }
    assert job["environment"]["name"] == "github-pages"
    assert job["concurrency"] == {"group": "pages", "cancel-in-progress": False}
    steps = job["steps"]
    uses = [s.get("uses", "") for s in steps]
    runs = [s.get("run") for s in steps]
    assert uses[0].startswith("actions/checkout@")
    assert uses[1] == "./.github/actions/setup"
    assert runs[2] == "task setup"
    assert runs[3] == 'task docs:build -- "$RUNNER_TEMP/site"'
    assert uses[-2].startswith("actions/upload-pages-artifact@")
    assert uses[-1].startswith("actions/deploy-pages@")
    assert steps[-1]["id"] == "deployment"
    assert job["environment"]["url"] == "${{ steps.deployment.outputs.page_url }}"


@pytest.mark.parametrize("archetype", SINGLE)
def test_s15_8_6_2b_hook_steps(tmp_path: Path, archetype: str) -> None:
    extra = '\n[ci.hooks]\ndocs = ["./.github/actions/a", "./.github/actions/b"]\n'
    steps = workflows.jobs(
        _docs_render(tmp_path, archetype, "tag-exists", extra=extra)
    )["docs"]["steps"]
    names = [s.get("name") for s in steps]
    assert names[-2:] == ["Upload Pages artifact", "Deploy to GitHub Pages"]
    assert [s["uses"] for s in steps if "SITE_DIR" in s.get("env", {})] == [
        "./.github/actions/a",
        "./.github/actions/b",
    ]


GATES = [
    ("tag-exists", True),
    ("tag-exists", False),
    ("none", True),
    ("none", False),
]


@pytest.mark.parametrize(("release", "sonar"), GATES)
@pytest.mark.parametrize("archetype", ["python-tool", "python-lib", "node-lib"])
def test_s15_8_6_3_gate(
    tmp_path: Path, archetype: str, release: str, sonar: bool
) -> None:
    release = _release_for(archetype, release)
    jobs = workflows.jobs(_docs_render(tmp_path, archetype, release, sonar=sonar))
    rendered = ["release", "verify-release"] if release != "none" else []
    plan = ["plan"] if archetype == "python-lib" else []
    assert jobs["docs"]["needs"] == ["checks-ok", *plan, *rendered]
    assert jobs["docs"]["if"].replace(PLAN_TERM, "") == DOCS_IF
    assert ("sonar" in jobs) is sonar
    barrier = set(jobs["checks-ok"]["needs"])
    if archetype == "node-lib":
        assert {"test-cloud", "test-local", "smoke"} <= barrier
    else:
        assert {"test", "integration", "smoke", "suites"} <= barrier


@pytest.mark.parametrize("archetype", ALL_ARCHETYPES)
def test_s15_8_6_3b_skipped_release_deploys(tmp_path: Path, archetype: str) -> None:
    release = _release_for(archetype, "tag-exists")
    cond = workflows.jobs(_docs_render(tmp_path, archetype, release))["docs"]["if"]
    assert "needs.release.result" not in cond
    assert "needs.verify-release.result" not in cond


@pytest.mark.parametrize("archetype", ALL_ARCHETYPES)
def test_s15_8_6_4_ci_ok(tmp_path: Path, archetype: str) -> None:
    release = _release_for(archetype, "tag-exists")
    jobs = workflows.jobs(_docs_render(tmp_path, archetype, release))
    assert jobs["ci-ok"]["needs"] == ["checks-ok", "release", "verify-release", "docs"]


@pytest.mark.parametrize("archetype", ALL_ARCHETYPES)
def test_s15_8_6_5_no_profile(tmp_path: Path, archetype: str) -> None:
    release = _release_for(archetype, "tag-exists")
    jobs = workflows.jobs(_docs_render(tmp_path, archetype, release, docs=False))
    assert "docs" not in jobs
    assert "docs" not in jobs["ci-ok"]["needs"]


def test_s15_8_6_6_node_lib_gate(tmp_path: Path) -> None:
    job = workflows.jobs(_docs_render(tmp_path, "node-lib", "nx-dispatch"))["docs"]
    assert job["needs"] == ["checks-ok", "release", "verify-release"]
    assert job["if"] == DOCS_IF
    assert "test-cloud" not in str(job["needs"]) + job["if"]
    assert "test-local" not in str(job["needs"]) + job["if"]


def test_s15_8_6_7_lib_gate(tmp_path: Path) -> None:
    job = workflows.jobs(_docs_render(tmp_path, "python-lib", "pypi"))["docs"]
    assert job["needs"] == ["checks-ok", "plan", "release", "verify-release"]
    assert PLAN_TERM in job["if"]
    assert job["if"].replace(PLAN_TERM, "") == DOCS_IF


SONAR_IF = (
    "${{ !cancelled() && !contains(needs.*.result, 'failure') "
    "&& github.actor != 'dependabot[bot]' "
    "&& ((github.event_name == 'pull_request' "
    "&& github.event.pull_request.head.repo.full_name == github.repository) "
    "|| (github.event_name != 'pull_request' "
    "&& github.ref == 'refs/heads/main')) }}"
)
TEST_STAGES = ("test", "test-cloud", "test-local", "integration", "smoke", "suites")


@pytest.mark.parametrize("archetype", ALL_ARCHETYPES)
def test_s15_8_8_1_same_guard(tmp_path: Path, archetype: str) -> None:
    release = _release_for(archetype, "tag-exists")
    jobs = workflows.jobs(_docs_render(tmp_path, archetype, release))
    assert jobs["sonar"]["if"] == SONAR_IF


@pytest.mark.parametrize("archetype", ALL_ARCHETYPES)
def test_s15_8_8_2_needs(tmp_path: Path, archetype: str) -> None:
    release = _release_for(archetype, "tag-exists")
    jobs = workflows.jobs(_docs_render(tmp_path, archetype, release))
    rendered = [s for s in TEST_STAGES if s in jobs]
    assert sorted(jobs["sonar"]["needs"]) == sorted(["validate", *rendered])


@pytest.mark.parametrize("archetype", ALL_ARCHETYPES)
def test_s15_8_8_3_gate_waits(tmp_path: Path, archetype: str) -> None:
    release = _release_for(archetype, "tag-exists")
    jobs = workflows.jobs(_docs_render(tmp_path, archetype, release))
    steps = jobs["sonar"]["steps"]
    args = "".join(str(s.get("with", {}).get("args", "")) for s in steps)
    assert "-Dsonar.qualitygate.wait=true" in args
