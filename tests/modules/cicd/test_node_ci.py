"""Node CI: affected jobs, Nx Cloud, and the retired helpers."""

from __future__ import annotations
import hashlib
import json
import pytest
import subprocess
from collections.abc import Callable
from pathlib import Path
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.commons.lang.models import ModelValidationError
from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.pins import load_pins
from rn_forge.kiln.modules.core import cycle
from tests.modules.cicd.support import (
    CALL,
    CI_YML,
    KILN_DOCTOR_FULL_EXPRESSION,
    NGKIT,
    NGKIT_REF,
    _cell_root,
    _ci_jobs,
    _node_lib_ci,
    _rendered,
    _root,
    _web_root,
    _with_ci,
)


RETIRED_HELPERS = tuple(
    f"tools/ci/{name}.mjs"
    for name in (
        "resolve-dist-workspace-deps",
        "verify-dist-manifest",
        "assemble-site",
        "release-notes",
    )
)


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [
        ("python-tool", ""),
        ("python-lib", ""),
        ("node-lib", ""),
        ("python-web-app", 'frontend = "angular"'),
    ],
)
def test_s9_4_4_4_no_rendered_file_names_tools_ci(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    leaks = [
        path.relative_to(root).as_posix()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and ".git/" not in path.as_posix()
        and b"tools/ci" in path.read_bytes()
    ]
    assert leaks == []


def test_s9_4_4_5_apply_deletes_the_retired_helpers(tmp_path: Path) -> None:
    root = _root(tmp_path, "node-lib")
    cycle.apply(root, home=tmp_path / "home")
    state_path = root / ".rn-forge" / "kiln" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    for path in RETIRED_HELPERS:
        body = "// retired\n"
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        state["entries"][path] = {
            "begin_marker": None,
            "content_hash": hashlib.sha256(body.encode()).hexdigest(),
            "end_marker": None,
            "kind": "managed",
            "path": path,
        }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    cycle.apply(root, home=tmp_path / "home")
    assert not any((root / path).exists() for path in RETIRED_HELPERS)
    after = json.loads(state_path.read_text(encoding="utf-8"))["entries"]
    assert not set(RETIRED_HELPERS) & set(after)
    assert [f.code for f in checks.run(root) if f.code.startswith("artifact")] == []


def test_s9_4_4_4_node_lib_renders_nothing_under_tools(tmp_path: Path) -> None:
    rendered = _rendered(_root(tmp_path, "node-lib"))
    assert not any(p.startswith("tools/") for p in rendered)
    assert not any("check-template" in p for p in rendered)


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [
        ("python-app", ""),
        ("python-tool", ""),
        ("python-lib", ""),
        ("python-web-api", ""),
        ("python-web-app", 'frontend = "angular"'),
    ],
)
def test_s9_1_10_1_other_archetypes_render_none(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    rendered = _rendered(_cell_root(tmp_path, archetype, extra))
    assert not any(p.startswith("tools/") for p in rendered)


AGENTS = ".nx/workflows/agents.yaml"


def test_s9_1_2_1_node_lib_jobs_are_the_affected_set(tmp_path: Path) -> None:
    jobs = _node_lib_ci(tmp_path)["jobs"]
    assert list(jobs) == [  # type: ignore[arg-type]
        "validate",
        "dependency-review",
        "secret-scan",
        "test-cloud",
        "test-local",
        "sonar",
        "smoke",
        "release",
        "verify-release",
        "docs",
        "checks-ok",
        "ci-ok",
    ]
    assert jobs["test-cloud"]["needs"] == "validate"  # type: ignore[index]
    assert jobs["test-local"]["needs"] == "validate"  # type: ignore[index]
    python = _ci_jobs(_root(tmp_path / "py", "python-tool"))
    node_validate = jobs["validate"]  # type: ignore[index]
    node_steps = node_validate.pop("steps")
    python_validate = python["validate"]  # type: ignore[index]
    python_steps = python_validate.pop("steps")
    assert node_validate == python_validate
    assert [s.get("name") for s in node_steps] == [s.get("name") for s in python_steps]
    assert [s for s in node_steps if s.get("name") != "Validate"] == [
        s for s in python_steps if s.get("name") != "Validate"
    ]
    assert jobs["dependency-review"] == python["dependency-review"]  # type: ignore[index]


def test_s9_1_2_2_triggers_and_concurrency(tmp_path: Path) -> None:
    ci = _node_lib_ci(tmp_path)
    triggers = ci[True] if True in ci else ci["on"]  # type: ignore[index]
    assert triggers["push"] == {"branches": ["main"]}  # type: ignore[index]
    assert triggers["pull_request"] == {"branches": ["main"]}  # type: ignore[index]
    assert triggers["workflow_dispatch"] == {  # type: ignore[index]
        "inputs": {
            "use-nx-cloud": {
                "description": "Use Nx Cloud distributed CI (leave unchecked to validate on a GitHub runner)",
                "required": False,
                "type": "boolean",
                "default": False,
            }
        }
    }
    assert ci["concurrency"] == {
        "group": "ci-${{ github.ref }}",
        "cancel-in-progress": "${{ github.event_name == 'pull_request' }}",
    }
    assert ci["permissions"] == {"contents": "read"}
    for name in ("test-cloud", "test-local"):
        assert ci["jobs"][name]["permissions"] == {  # type: ignore[index]
            "actions": "read",
            "contents": "read",
        }


def test_s9_1_2_3_ci_cloud_matches_ngkit(tmp_path: Path) -> None:
    job = _node_lib_ci(tmp_path)["jobs"]["test-cloud"]  # type: ignore[index]
    pins = load_pins()
    assert job["if"] == (
        "${{ (github.event_name == 'workflow_dispatch' && inputs.use-nx-cloud) "
        "|| (github.event_name != 'workflow_dispatch' && vars.USE_NX_CLOUD == 'true') }}"
    )
    assert job["env"] == {
        "NX_CLOUD_ACCESS_TOKEN": "${{ secrets.NX_CLOUD_ACCESS_TOKEN }}"
    }
    checkout, setup, shas, affected, fix = job["steps"]
    assert checkout["with"] == {
        "filter": "tree:0",
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    assert setup["uses"].startswith("./.github/actions/setup")
    assert setup["with"]["github-token"] == "${{ secrets.GITHUB_TOKEN }}"
    assert setup["with"]["start-ci-run"] == (
        "--distribute-on=\"${{ vars.NX_CLOUD_AGENTS || '3' }} linux-medium\" "
        '--stop-agents-after="lint,test,build,e2e-ci"'
    )
    assert shas["uses"].startswith(f"nrwl/nx-set-shas@{pins['nx-set-shas']['sha']}")
    assert affected == {"run": "task ci:test -- lint test build e2e-ci"}
    assert fix == {"run": "pnpm exec nx fix-ci", "if": "always()"}


def test_s9_1_2_4_ci_local_matches_ngkit(tmp_path: Path) -> None:
    job = _node_lib_ci(tmp_path)["jobs"]["test-local"]  # type: ignore[index]
    pins = load_pins()
    assert job["if"] == (
        "${{ (github.event_name == 'workflow_dispatch' && inputs.use-nx-cloud == false) "
        "|| (github.event_name != 'workflow_dispatch' && vars.USE_NX_CLOUD != 'true') }}"
    )
    assert "env" not in job
    checkout, setup, e2e, cache, install, deps, shas, affected = job["steps"]
    assert checkout["with"] == {
        "filter": "tree:0",
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    assert setup["with"] == {"github-token": "${{ secrets.GITHUB_TOKEN }}"}
    assert e2e["id"] == "e2e"
    assert e2e["run"] == 'task ci:test:has-e2e >> "$GITHUB_OUTPUT"'
    assert cache["uses"].startswith(f"actions/cache@{pins['cache']['sha']}")
    assert cache["id"] == "playwright-cache"
    assert cache["with"]["path"] == "~/.cache/ms-playwright"
    assert install["run"] == "task ci:test:playwright"
    assert install["if"] == (
        "steps.e2e.outputs.has-e2e == 'true' "
        "&& steps.playwright-cache.outputs.cache-hit != 'true'"
    )
    assert deps["run"] == "task ci:test:playwright-deps"
    assert deps["if"] == (
        "steps.e2e.outputs.has-e2e == 'true' "
        "&& steps.playwright-cache.outputs.cache-hit == 'true'"
    )
    assert shas["uses"].startswith("nrwl/nx-set-shas@")
    assert affected == {"run": "task ci:test -- lint test build e2e"}


def test_s9_1_2_6_ci_ok_needs_every_job_and_checks_both_paths(tmp_path: Path) -> None:
    jobs = _node_lib_ci(tmp_path)["jobs"]
    assert jobs["checks-ok"]["needs"] == [  # type: ignore[index]
        "validate",
        "dependency-review",
        "test-cloud",
        "test-local",
        "smoke",
        "sonar",
        "secret-scan",
    ]
    ok = jobs["ci-ok"]  # type: ignore[index]
    assert ok["needs"] == ["checks-ok", "release", "verify-release", "docs"]
    assert ok["if"] == "always()"
    assert ok["permissions"] == {}
    (step,) = ok["steps"]
    assert "jq" not in step["run"]


def test_s9_1_2_6_declared_jobs_join_ci_ok(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\n'
    jobs = _ci_jobs(_with_ci(_root(tmp_path, "node-lib"), extra))
    assert jobs["checks-ok"]["needs"][-1] == "extra"  # type: ignore[index]


def test_s9_1_2_7_agents_yaml_is_ngkits_under_t1(tmp_path: Path) -> None:
    lines = _rendered(_root(tmp_path, "node-lib"))[AGENTS].splitlines()
    assert lines[0].startswith("# Generated by kiln ")
    assert "ci-template" not in "\n".join(lines)
    assert "image: 'ubuntu22.04-node24.14-v1'" in lines[4]
    if not (NGKIT / ".git").exists():
        pytest.skip("no ngkit checkout beside this repository")
    golden = subprocess.run(
        ["git", "-C", str(NGKIT), "show", f"{NGKIT_REF}:{AGENTS}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert golden[0].startswith("# ci-template:")
    assert golden[1:] == lines[1:]


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [
        ("python-app", ""),
        ("python-tool", ""),
        ("python-lib", ""),
        ("python-web-api", ""),
        ("python-web-app", 'frontend = "angular"'),
    ],
)
def test_s9_1_2_other_archetypes_render_no_node_lib_ci(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    rendered = _rendered(_cell_root(tmp_path, archetype, extra))
    assert AGENTS not in rendered
    assert "use-nx-cloud" not in rendered[CI_YML]
    assert "nx-set-shas" not in rendered[CI_YML]


CLOUD_IF = (
    "${{ (github.event_name == 'workflow_dispatch' && inputs.use-nx-cloud) "
    "|| (github.event_name != 'workflow_dispatch' && vars.USE_NX_CLOUD == 'true') }}"
)


LOCAL_IF = (
    "${{ (github.event_name == 'workflow_dispatch' && inputs.use-nx-cloud == false) "
    "|| (github.event_name != 'workflow_dispatch' && vars.USE_NX_CLOUD != 'true') }}"
)


def test_s9_2_8_1_ci_cloud_runs_only_when_asked(tmp_path: Path) -> None:
    assert _node_lib_ci(tmp_path)["jobs"]["test-cloud"]["if"] == CLOUD_IF  # type: ignore[index]


def test_s9_2_8_2_ci_local_is_the_default_path(tmp_path: Path) -> None:
    assert _node_lib_ci(tmp_path)["jobs"]["test-local"]["if"] == LOCAL_IF  # type: ignore[index]


def test_s9_2_8_3_dispatch_input_defaults_to_false(tmp_path: Path) -> None:
    ci = _node_lib_ci(tmp_path)
    triggers = ci[True] if True in ci else ci["on"]  # type: ignore[index]
    inputs = triggers["workflow_dispatch"]["inputs"]  # type: ignore[index]
    assert inputs["use-nx-cloud"]["default"] is False


def _evaluate(expression: str, event: str, use_nx_cloud: bool | None, var: str) -> bool:
    """Evaluate one of the two `if` expressions for an event, the dispatch input
    and the repository variable ('' is unset)."""
    python = (
        expression.removeprefix("${{")
        .removesuffix("}}")
        .replace("&&", " and ")
        .replace("||", " or ")
        .replace("github.event_name", "event")
        .replace("inputs.use-nx-cloud", "use_nx_cloud")
        .replace("vars.USE_NX_CLOUD", "var")
        .replace("false", "False")
    )
    return bool(
        eval(python, {}, {"event": event, "use_nx_cloud": use_nx_cloud, "var": var})
    )  # noqa: S307


@pytest.mark.parametrize(
    ("event", "use_nx_cloud", "var", "cloud"),
    [
        ("push", None, "", False),
        ("push", None, "true", True),
        ("push", None, "false", False),
        ("pull_request", None, "", False),
        ("pull_request", None, "true", True),
        ("pull_request", None, "false", False),
        ("workflow_dispatch", True, "", True),
        ("workflow_dispatch", False, "", False),
        ("workflow_dispatch", True, "false", True),
        ("workflow_dispatch", False, "true", False),
    ],
)
def test_s9_2_8_5_exactly_one_of_ci_cloud_and_ci_local_runs(
    tmp_path: Path, event: str, use_nx_cloud: bool | None, var: str, cloud: bool
) -> None:
    jobs = _node_lib_ci(tmp_path)["jobs"]
    ran_cloud = _evaluate(jobs["test-cloud"]["if"], event, use_nx_cloud, var)  # type: ignore[index]
    ran_local = _evaluate(jobs["test-local"]["if"], event, use_nx_cloud, var)  # type: ignore[index]
    assert (ran_cloud, ran_local) == (cloud, not cloud)


def test_s9_2_8_4_web_app_config_has_no_nx_cloud(
    tmp_path: Path, rendered: Callable[[str], Path]
) -> None:
    root = _web_root(tmp_path, "python-web-app", extra="nx_cloud = false")
    with pytest.raises(ModelValidationError) as caught:
        KilnConfig.load(root)
    kinds = {error.path: error.kind for error in caught.value.errors}
    assert kinds["archetype.python-web-app.nx_cloud"] == "extra_forbidden"

    document = KilnConfig.load(rendered("python-web-app")).to_document()
    assert "nx_cloud" not in document["archetype"]["python-web-app"]


def test_s9_3_4_3_validate_step_runs_ci_validate(
    tmp_path: Path,
) -> None:
    expected = {
        "python-app": "task ci:validate",
        "python-tool": "task ci:validate",
        "python-lib": "task lint",
        "node-lib": "task ci:validate",
    }
    for archetype, run in expected.items():
        root = _root(tmp_path / archetype, archetype)
        workflow = _rendered(root)[".github/workflows/ci.yml"]
        job = YamlUtils.load(workflow)["jobs"]["validate"]
        step = next(s for s in job["steps"] if s["name"] == "Validate")
        assert step["run"] == run, archetype
        assert step["env"]["KILN_DOCTOR_FULL"] == KILN_DOCTOR_FULL_EXPRESSION, archetype
        assert job["timeout-minutes"] == 20, archetype
        comment = "# The Nx projects are checked by test-cloud or test-local; this job runs the rest."
        assert (comment in workflow) == (archetype == "node-lib"), archetype
