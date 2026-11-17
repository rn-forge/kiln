"""Job shape in the rendered workflows: checkout, timeouts, `ci-ok`, Sonar, release, cache."""

from __future__ import annotations
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.modules.cicd import CICD
from rn_forge.kiln.modules.core import pins as pins_module
from tests.modules.cicd import workflows
from tests.modules.cicd.support import (
    ARCHETYPES,
    KILN_DOCTOR_FULL_EXPRESSION,
    SETUP_ACTION,
    UPSTREAM_PINS,
    WORKFLOWS,
    _ci_jobs,
    _ci_tasks_text_of,
    _release_roots,
    _release_steps,
    _rendered,
    _root,
    _step_index,
    _web_root,
)


def _assert_checks_out_first(workflow: str, where: str) -> None:
    jobs = YamlUtils.load(workflow)["jobs"]
    for name, job in jobs.items():
        steps = job.get("steps", [])
        for index, step in enumerate(steps):
            if step.get("uses") != SETUP_ACTION:
                continue
            assert index > 0, f"{where}: {name} sets up before checking out"
            previous = steps[index - 1]
            assert str(previous.get("uses", "")).startswith("actions/checkout@"), (
                f"{where}: {name}'s setup step does not follow a checkout"
            )
            if name == "sonar":
                assert previous.get("with", {}).get("fetch-depth") == 0, where


def test_s4_4_5_1_every_job_checks_out_before_the_setup_action(
    tmp_path: Path,
) -> None:
    roots = [_root(tmp_path / archetype, archetype) for archetype in ARCHETYPES] + [
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"'),
    ]
    for root in roots:
        for path, content in _rendered(root).items():
            if path in WORKFLOWS:
                _assert_checks_out_first(content, f"{root.name}:{path}")


def test_s4_4_5_2_setup_action_has_no_checkout(tmp_path: Path) -> None:
    action = _rendered(_root(tmp_path))[".github/actions/setup/action.yml"]
    assert "actions/checkout@" not in action
    assert "fetch-depth" not in action
    parsed = YamlUtils.load(action)
    assert "fetch-depth" not in parsed["inputs"]


def test_s4_4_5_3_kiln_and_rendered_repos_check_out_first(
    rendered: Callable[[str], Path],
) -> None:
    repo = Path(__file__).resolve().parents[3]
    roots = [repo, *(rendered(archetype) for archetype in ARCHETYPES)]
    for root in roots:
        for workflow in sorted((root / ".github" / "workflows").glob("*.yml")):
            _assert_checks_out_first(
                workflow.read_text(encoding="utf-8"), f"{root.name}/{workflow.name}"
            )


def test_s6_3_1_every_job_has_a_timeout(tmp_path: Path) -> None:
    roots = [_root(tmp_path / archetype, archetype) for archetype in ARCHETYPES] + [
        _web_root(tmp_path / "api", "python-web-api"),
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"'),
    ]
    for root in roots:
        workflows = {
            path: content
            for path, content in _rendered(root).items()
            if path.startswith(".github/workflows/")
        }
        assert workflows
        for path, content in workflows.items():
            for name, job in YamlUtils.load(content)["jobs"].items():
                if "uses" in job:  # a caller job takes no timeout
                    continue
                timeout = job.get("timeout-minutes")
                assert isinstance(timeout, int), f"{root.name}:{path}:{name}"


def _ci_ok_roots(tmp_path: Path) -> list[Path]:
    return [_root(tmp_path / archetype, archetype) for archetype in ARCHETYPES] + [
        _root(tmp_path / "nosonar", sonar=False),
        _root(tmp_path / "norelease", release="none"),
        _web_root(tmp_path / "api", "python-web-api"),
        _web_root(tmp_path / "web", "python-web-app", extra='frontend = "angular"'),
    ]


def test_s6_3_2_ci_ok_needs_every_other_job(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        jobs = _ci_jobs(root)
        assert list(jobs)[-1] == "ci-ok", root.name
        covered = {*jobs["checks-ok"]["needs"], *jobs["ci-ok"]["needs"]}  # type: ignore[misc]
        assert covered == set(jobs) - {"ci-ok"}, root.name
        assert jobs["ci-ok"]["if"] == "always()", root.name


def test_s6_3_2_ci_ok_has_no_permissions(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        assert _ci_jobs(root)["ci-ok"]["permissions"] == {}, root.name


def test_s6_3_2_ci_ok_fails_on_failure_or_cancel(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        steps = _ci_jobs(root)["ci-ok"]["steps"]
        assert len(steps) == 1  # type: ignore[arg-type]
        step = steps[0]  # type: ignore[index]
        assert "contains(needs.*.result, 'failure')" in step["if"]
        assert "contains(needs.*.result, 'cancelled')" in step["if"]
        assert step["run"] == "exit 1"


def _sonar_steps(root: Path) -> list[dict[str, object]]:
    return _ci_jobs(root)["sonar"]["steps"]  # type: ignore[return-value]


def test_s6_3_3_scan_passes_the_target_branch_arg(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        if root.name == "nosonar":
            continue
        steps = _sonar_steps(root)
        names = [step["name"] for step in steps]
        target = next(i for i, step in enumerate(steps) if step.get("id") == "target")
        assert target < names.index("Test with coverage"), root.name
        scan = next(step for step in steps if step["name"] == "SonarQube scan")
        assert (
            "${{ steps.target.outputs.branch-arg }}" in scan["with"]["args"]  # type: ignore[index]
        ), root.name


def test_s6_3_3_ref_text_reaches_run_only_through_env(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        if root.name == "nosonar":
            continue
        for step in _sonar_steps(root):
            run = str(step.get("run", ""))
            assert "github.ref_name" not in run, root.name
            assert "github.head_ref" not in run, root.name


def test_s6_7_4_1_the_target_step_is_a_task_call(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        if root.name == "nosonar":
            continue
        step = next(s for s in _sonar_steps(root) if s.get("id") == "target")
        assert step["name"] == "Resolve the analysis target", root.name
        assert step["env"] == {
            "EVENT_NAME": "${{ github.event_name }}",
            "REF_TYPE": "${{ github.ref_type }}",
            "REF_NAME": "${{ github.ref_name }}",
        }, root.name
        assert step["run"] == 'task ci:sonar:target >> "$GITHUB_OUTPUT"', root.name


def test_s6_3_8_sonar_runs_only_on_a_pull_request_or_main(tmp_path: Path) -> None:
    for root in _ci_ok_roots(tmp_path):
        if root.name == "nosonar":
            continue
        condition = " ".join(str(_ci_jobs(root)["sonar"]["if"]).split())
        assert (
            "(github.event_name == 'pull_request' && "
            "github.event.pull_request.head.repo.full_name == github.repository) || "
            "(github.event_name != 'pull_request' && github.ref == 'refs/heads/main')"
        ) in condition, root.name


def test_s6_7_5_6_the_release_job_is_task_calls(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        assert [s["name"] for s in steps] == [
            "Checkout",
            "Set up the toolchain",
            "Check whether this version has been released",
            "Check out the release source",
            "Build",
            "Generate provenance",
            "Publish GitHub Release",
        ], root.name
        for step in steps:
            assert "\n" not in str(step.get("run", "")), (root.name, step["name"])


def test_s6_3_4_check_step_outputs_the_tag_state(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        check = next(step for step in steps if step.get("id") == "check")
        assert check["env"] == {"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}, root.name
        assert check["run"] == 'task ci:release:state >> "$GITHUB_OUTPUT"', root.name


def test_s6_3_4_checkout_of_the_tag_precedes_build(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        index = _step_index(steps, "Check out the release source")
        step = steps[index]
        assert step["id"] == "source"
        assert step["if"] == "steps.check.outputs.should-release == 'true'"
        assert step["env"] == {"TAG": "${{ steps.check.outputs.tag }}"}
        assert step["run"] == 'task ci:release:source >> "$GITHUB_OUTPUT"'
        check = next(i for i, s in enumerate(steps) if s.get("id") == "check")
        assert check < index < _step_index(steps, "Build"), root.name


def test_s6_3_4_draft_is_deleted_before_publish(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        names = [s["name"] for s in steps]
        assert "Delete the leftover draft" not in names, root.name
        publish = steps[_step_index(steps, "Publish GitHub Release")]
        assert publish["run"] == "task ci:release:publish", root.name
        assert _step_index(steps, "Build") < names.index("Publish GitHub Release")


def test_s6_3_4_publish_targets_the_source_commit(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        publish = steps[_step_index(steps, "Publish GitHub Release")]
        assert (
            publish["env"]["SOURCE_SHA"]  # type: ignore[index]
            == "${{ steps.source.outputs.sha }}"
        )
        assert any(step.get("id") == "source" for step in steps)


def test_s6_3_6_release_uploads_distributions_and_sbom_only(tmp_path: Path) -> None:
    for root in _release_roots(tmp_path):
        steps = _release_steps(root)
        publish = steps[_step_index(steps, "Publish GitHub Release")]
        assert publish["run"] == "task ci:release:publish", root.name
        tasks = _ci_tasks_text_of(root)["tasks"]
        run = " ".join(tasks["release:publish"]["cmds"])  # type: ignore[index]
        assert "dist/*.whl dist/*.tar.gz dist/*.cdx.json" in run, root.name
        assert "dist/*" not in run.split(), root.name


def test_s6_3_5_setup_uv_enables_the_cache(tmp_path: Path) -> None:
    action = YamlUtils.load(
        _rendered(_root(tmp_path))[".github/actions/setup/action.yml"]
    )
    install = next(
        step for step in action["runs"]["steps"] if step["name"] == "Install uv"
    )
    assert install["with"]["enable-cache"] is True


def test_s7_4_4_1_uv_cache_follows_the_kiln_pin(tmp_path: Path) -> None:
    action = YamlUtils.load(
        _rendered(_root(tmp_path))[".github/actions/setup/action.yml"]
    )
    install = next(
        step for step in action["runs"]["steps"] if step["name"] == "Install uv"
    )
    assert install["with"]["cache-dependency-glob"].split() == [
        "**/uv.lock",
        ".rn-forge/kiln/config.toml",
    ]


def test_s6_3_5_pins_match_the_upstream_versions() -> None:
    pins_file = Path(pins_module.__file__ or "").parent / "pins.toml"
    pins = tomllib.loads(pins_file.read_text(encoding="utf-8"))
    for key, (sha, version) in UPSTREAM_PINS.items():
        assert (pins[key]["sha"], pins[key]["version"]) == (sha, version), key


def test_s4_6_4_2_ci_sets_the_variable_on_default_branch_pushes(
    tmp_path: Path,
) -> None:
    for archetype in ARCHETYPES:
        root = _root(tmp_path / archetype, archetype)
        jobs = workflows.jobs(_rendered(root))
        step = next(s for s in jobs["validate"]["steps"] if s["name"] == "Validate")
        assert step["run"] == (
            "task lint" if archetype == "python-lib" else "task ci:validate"
        )
        assert step["env"]["KILN_DOCTOR_FULL"] == KILN_DOCTOR_FULL_EXPRESSION, archetype
