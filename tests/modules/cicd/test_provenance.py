"""Build provenance, attestation, and release permissions."""

from __future__ import annotations
import pytest
import re
import subprocess
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.pins import load_pins
from rn_forge.kiln.modules.cicd.checks import pins as pins_check
from rn_forge.kiln.modules.core import cycle
from tests.conftest import requires
from tests.modules.cicd.support import (
    ARCHETYPES,
    CALL,
    DEPENDABOT,
    DOCS_HOOKS,
    RELEASE_PERMISSIONS,
    SECURITY_CELLS,
    WORKFLOWS,
    _action,
    _cell_root,
    _ci_jobs,
    _hook_entry,
    _job_steps,
    _lib_jobs,
    _lib_root,
    _pypi_root,
    _release_steps,
    _rendered,
    _root,
    _step_index,
    _with_ci,
)


SUBJECTS = "dist/*.whl\ndist/*.tar.gz\ndist/*.cdx.json\n"


LIB_SUBJECTS = "dist/*/*.whl\ndist/*/*.tar.gz\ndist/*/*.cdx.json\n"


SINGLE_RELEASE_CELLS = [(a, e) for a, e in SECURITY_CELLS if a != "python-lib"]


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_6_3_release_job_permissions(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    allowed = {
        ("ci.yml", "release"),
        ("ci.yml", "docs"),
        ("_docs.yml", "docs"),
        ("docs.yml", "deploy"),
    }
    for path, content in _rendered(root).items():
        if not path.startswith(".github/workflows/"):
            continue
        workflow = Path(path).name
        for name, job in YamlUtils.load(content)["jobs"].items():
            permissions = job.get("permissions") or {}
            if (workflow, name) in {("ci.yml", "release"), ("_release.yml", "release")}:
                assert permissions == RELEASE_PERMISSIONS, archetype
                continue
            assert "attestations" not in permissions, f"{workflow}:{name}"
            if "id-token" in permissions:
                assert (workflow, name) in allowed, f"{workflow}:{name}"


@pytest.mark.parametrize(("archetype", "extra"), SINGLE_RELEASE_CELLS)
def test_s4_11_6_4_single_package_release_attests_before_publishing(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    steps = _release_steps(_cell_root(tmp_path, archetype, extra))
    names = [s.get("name") for s in steps]
    build, provenance, publish = (
        names.index(n)
        for n in ("Build", "Generate provenance", "Publish GitHub Release")
    )
    assert build < provenance < publish
    pin = load_pins()["attest"]
    step = steps[provenance]
    assert step["uses"] == f"{pin['uses']}@{pin['sha']}"
    assert step["if"] == "steps.check.outputs.should-release == 'true'"
    assert step["with"] == {"subject-path": SUBJECTS}  # type: ignore[comparison-overlap]
    assert steps[publish]["run"] == "task ci:release:publish"


def test_s4_11_6_4_lib_release_attests_between_build_and_publish(
    tmp_path: Path,
) -> None:
    steps = _lib_jobs(tmp_path)["release"]["steps"]  # type: ignore[assignment]
    tail = steps[3:]  # type: ignore[index]
    assert [s["name"] for s in tail] == [
        "Build releases",
        "Generate provenance",
        "Publish releases",
    ]
    build, provenance, publish = tail
    env = {
        "GH_TOKEN": "${{ github.token }}",
        "SELECTED": "${{ needs.plan.outputs.release-order }}",
    }
    assert build["run"] == "task ci:release:build"
    assert build["env"] == env
    assert build["id"] == "build"
    pin = load_pins()["attest"]
    assert provenance["uses"] == f"{pin['uses']}@{pin['sha']}"
    assert provenance["if"] == "steps.build.outputs.built != '0'"
    assert provenance["with"] == {"subject-path": LIB_SUBJECTS}
    assert publish["run"] == "task ci:release:publish"
    assert publish["env"] == env


def test_s4_11_6_5_attest_is_pinned(tmp_path: Path) -> None:
    pin = load_pins()["attest"]
    assert pin["uses"] == "actions/attest"
    assert re.fullmatch(r"[0-9a-f]{40}", pin["sha"])
    assert pin["version"]
    assert "attest-provenance" not in load_pins()
    for archetype, extra in SECURITY_CELLS:
        root = _cell_root(tmp_path / archetype, archetype, extra)
        cycle.apply(root, home=tmp_path / archetype / "home")
        assert pins_check.check(KilnConfig.load(root), root) == [], archetype


@pytest.mark.parametrize(("archetype", "extra"), SECURITY_CELLS)
def test_s4_11_6_6_release_none_renders_no_attestation(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _cell_root(tmp_path, archetype, extra)
    config = root / ".rn-forge" / "kiln" / "config.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(_release_none(text), encoding="utf-8")
    rendered = _rendered(root)
    assert "release" not in _ci_jobs(root)
    for path, content in rendered.items():
        if path != DEPENDABOT:  # its ignore list names every pinned action
            assert "attest" not in content, path
        if not path.startswith(".github/workflows/"):
            continue
        for name, job in YamlUtils.load(content)["jobs"].items():
            if "id-token" in (job.get("permissions") or {}):
                assert (Path(path).name, name) in {
                    ("ci.yml", "docs"),
                    ("_docs.yml", "docs"),
                    ("docs.yml", "deploy"),
                }, f"{path}:{name}"


def _release_none(text: str) -> str:
    if 'release = "tag-exists"' in text:
        return text.replace('release = "tag-exists"', 'release = "none"')
    return text + '\n[ci]\nrelease = "none"\n'


def _docs_hook_steps(*names: str) -> list[dict[str, object]]:
    return [
        {
            "name": f"Run ./.github/actions/{n}",
            "uses": f"./.github/actions/{n}",
            "env": {"SITE_DIR": "${{ runner.temp }}/site"},
        }
        for n in names
    ]


def test_s4_11_7_1_docs_hooks_render_before_the_upload(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-lib"), DOCS_HOOKS)
    steps = _job_steps(root, ".github/workflows/ci.yml", "docs")
    names = [s["name"] for s in steps]
    upload = names.index("Upload Pages artifact")
    assert steps[upload - 2 : upload] == _docs_hook_steps("a", "b")
    assert names[upload - 3] == "Deploy the package sites and build the root site"


def test_s4_11_7_1_docs_hooks_render_in_the_single_package_docs_job(
    tmp_path: Path,
) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), DOCS_HOOKS)
    steps = _job_steps(root, ".github/workflows/ci.yml", "docs")
    names = [s["name"] for s in steps]
    upload = names.index("Upload Pages artifact")
    assert steps[upload - 2 : upload] == _docs_hook_steps("a", "b")
    assert names[upload - 3] == "Build docs site"


@pytest.mark.parametrize("archetype", ["python-lib", "python-tool"])
def test_s4_11_7_2_no_docs_hooks_is_byte_identical(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    plain = _rendered(root)
    empty = _rendered(_with_ci(root, "hooks = { docs = [] }\n"))
    for workflow in WORKFLOWS:
        assert plain.get(workflow) == empty.get(workflow), workflow


def test_s4_11_7_3_docs_hooks_are_not_setup_hooks(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), DOCS_HOOKS)
    assert "Run ./" not in _action(root)


@pytest.mark.parametrize(
    "path",
    [
        "./.github/actions/setup",
        ".github/actions/x",
        "./actions/x",
        "./.github/actions/X",
        "./.github/actions/a/b",
        "./.github/workflows/x.yml",
    ],
)
def test_s4_11_7_4_bad_docs_hook_paths_are_refused(tmp_path: Path, path: str) -> None:
    root = _with_ci(
        _root(tmp_path, "python-tool"), f'\n[ci.hooks]\ndocs = ["{path}"]\n'
    )
    with pytest.raises(AppException, match=r"ci\.hooks\.docs"):
        KilnConfig.load(root)


def test_s4_11_7_4_duplicate_docs_hooks_are_refused(tmp_path: Path) -> None:
    extra = '\n[ci.hooks]\ndocs = ["./.github/actions/a", "./.github/actions/a"]\n'
    with pytest.raises(AppException):
        KilnConfig.load(_with_ci(_root(tmp_path / "dup", "python-tool"), extra))
    both = (
        '\n[ci.hooks]\nsetup = ["./.github/actions/a"]\n'
        'docs = ["./.github/actions/a"]\n'
    )
    KilnConfig.load(_with_ci(_root(tmp_path / "both", "python-tool"), both))


def test_s4_11_7_5_docs_hooks_without_docs_are_refused(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool", profile="none"), DOCS_HOOKS)
    with pytest.raises(AppException, match="nothing deploys Pages"):
        _rendered(root)


def test_s4_11_7_6_dependabot_covers_docs_hooks(tmp_path: Path) -> None:
    extra = (
        '\n[ci.hooks]\nsetup = ["./.github/actions/a"]\n'
        'docs = ["./.github/actions/b", "./.github/actions/a"]\n'
    )
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    assert _hook_entry(root)["directories"] == [
        "/.github/actions/a",
        "/.github/actions/b",
    ]


@requires("actionlint")
def test_s4_11_7_7_actionlint_passes_on_a_docs_hook(tmp_path: Path) -> None:
    root = _with_ci(
        _root(tmp_path, "python-lib"),
        '\n[ci.hooks]\ndocs = ["./.github/actions/a"]\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    action = root / ".github" / "actions" / "a" / "action.yml"
    action.parent.mkdir(parents=True)
    action.write_text(
        "name: x\ndescription: x\nruns:\n  using: composite\n  steps:\n"
        "    - run: echo hi\n      shell: bash\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["actionlint", ".github/workflows/ci.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _ci_workflow(root: Path) -> dict[str, object]:
    return YamlUtils.load(_rendered(root)[".github/workflows/ci.yml"])


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_11_8_1_default_is_byte_identical(tmp_path: Path, archetype: str) -> None:
    plain = _rendered(_root(tmp_path / "plain", archetype))
    named = _rendered(
        _with_ci(
            _root(tmp_path / "named", archetype), 'doctor_full = "default-branch"\n'
        )
    )
    assert plain[".github/workflows/ci.yml"] == named[".github/workflows/ci.yml"]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_11_8_2_every_run_sets_the_variable(tmp_path: Path, archetype: str) -> None:
    default = _ci_workflow(_root(tmp_path / "default", archetype))
    every = _ci_workflow(
        _with_ci(_root(tmp_path / "every", archetype), 'doctor_full = "every-run"\n')
    )
    steps = every["jobs"]["validate"]["steps"]  # type: ignore[index]
    step = next(s for s in steps if s["name"] == "Validate")
    assert step["env"] == {"KILN_DOCTOR_FULL": "1"}
    step["env"] = next(
        s
        for s in default["jobs"]["validate"]["steps"]  # type: ignore[index]
        if s["name"] == "Validate"
    )["env"]
    assert every == default


def test_s4_11_8_3_bad_value_is_refused(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-tool"), 'doctor_full = "always"\n')
    with pytest.raises(AppException, match=r"ci\.doctor_full"):
        KilnConfig.load(root)


@requires("actionlint")
def test_s4_11_8_4_actionlint_passes_on_every_run(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "python-app"), 'doctor_full = "every-run"\n')
    cycle.apply(root, home=tmp_path / "home")
    result = subprocess.run(
        ["actionlint", ".github/workflows/ci.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _ci_text(root: Path) -> dict[str, object]:
    return YamlUtils.load(_rendered(root)[".github/workflows/ci.yml"])


def test_s7_6_4_1_dispatch_takes_testpypi(tmp_path: Path) -> None:
    on = _ci_text(_pypi_root(tmp_path / "pypi"))["on"]
    assert on["workflow_dispatch"] == {  # type: ignore[index]
        "inputs": {
            "testpypi": {
                "type": "boolean",
                "default": False,
                "description": "Upload every package to TestPyPI; no tags or releases",
            }
        }
    }
    plain = _ci_text(_root(tmp_path / "plain", "python-lib"))["on"]
    assert plain["workflow_dispatch"] == {}  # type: ignore[index]


def test_s7_6_4_2_release_job_environment(tmp_path: Path) -> None:
    release = _ci_jobs(_pypi_root(tmp_path))["release"]
    assert release["environment"] == "${{ inputs.testpypi && 'testpypi' || 'pypi' }}"
    assert release["permissions"] == RELEASE_PERMISSIONS
    plain = _lib_jobs(tmp_path / "plain")["release"]
    assert "environment" not in plain
    push = "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    dispatch = "github.event_name == 'workflow_dispatch' && inputs.testpypi"
    expected = str(plain["if"]).replace(push, f"(({push}) || ({dispatch}))")
    assert f"(({push}) || ({dispatch}))" in str(release["if"])
    assert release["if"] == expected


def test_s7_6_4_3_release_steps_pass_testpypi(tmp_path: Path) -> None:
    steps = _release_steps(_pypi_root(tmp_path))
    expected = "${{ github.event_name == 'workflow_dispatch' && inputs.testpypi }}"
    for name in ("Build releases", "Publish releases"):
        step = steps[_step_index(steps, name)]
        assert step["env"]["TESTPYPI"] == expected, name  # type: ignore[index]
    provenance = steps[_step_index(steps, "Generate provenance")]
    assert str(provenance["if"]).endswith(" && env.TESTPYPI != 'true'")
    plain = _release_steps(_lib_root(tmp_path / "plain"))
    for step in plain:
        assert "TESTPYPI" not in str(step)


def test_s7_6_4_4_pypi_needs_a_workspace(tmp_path: Path) -> None:
    root = _pypi_root(tmp_path, "python-tool")
    with pytest.raises(ValueError, match=r"ci\.release"):
        _rendered(root)


@pytest.mark.parametrize("sonar", [True, False])
def test_s7_6_4_5_pypi_keeps_every_tag_exists_job(tmp_path: Path, sonar: bool) -> None:
    plain = _ci_jobs(_root(tmp_path / "plain", "python-lib", sonar=sonar))
    pypi = _ci_jobs(_pypi_root(tmp_path / "pypi", sonar=sonar))
    assert list(pypi) == list(plain)
    assert pypi["ci-ok"]["needs"] == plain["ci-ok"]["needs"]
    for name in plain:
        assert pypi[name].get("needs") == plain[name].get("needs"), name
    assert "release" in pypi["ci-ok"]["needs"]  # type: ignore[operator]
    assert "verify-release" in pypi["ci-ok"]["needs"]  # type: ignore[operator]


def test_s7_6_6_1_declared_job_can_write_contents(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\ncontents = "write"\n'
    job = _ci_jobs(_with_ci(_root(tmp_path, "python-tool"), extra))["extra"]
    assert job["permissions"] == {"contents": "write"}


def test_s7_6_6_2_declared_job_reads_by_default(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\n'
    job = _ci_jobs(_with_ci(_root(tmp_path, "python-tool"), extra))["extra"]
    assert job["permissions"] == {"contents": "read"}


def test_s7_6_6_3_bad_contents_is_refused(tmp_path: Path) -> None:
    extra = f'\n[[ci.jobs]]\nname = "extra"\nuses = "{CALL}"\ncontents = "admin"\n'
    root = _with_ci(_root(tmp_path, "python-tool"), extra)
    with pytest.raises(AppException):
        KilnConfig.load(root)
