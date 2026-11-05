"""S15.1.3 — `checks-ok`'s `needs` come from the registry and each job's `required`."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from rn_forge.commons.fs.documents import YamlUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd import CICD, registry
from rn_forge.kiln.modules.cicd.config import CiJob

CALL = "./.github/workflows/call.yml"
ARCHETYPES = (
    "python-lib",
    "python-tool",
    "python-app",
    "python-web-api",
    "python-web-app",
    "node-lib",
)


def _write(tmp_path: Path, archetype: str = "python-lib", extra: str = "") -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    release = "nx-dispatch" if archetype == "node-lib" else "tag-exists"
    text = (
        f'schema_version = 1\n\n[repository]\nname = "demo"\narchetype = "{archetype}"\n\n'
        f'[docs]\nprofile = "mkdocs"\n\n[ci]\nprovider = "github"\nsonar = true\n'
        f'release = "{release}"\n'
    )
    if archetype == "python-lib":
        text += '\n[archetype."python-lib"]\npackages = ["packages/alpha", "packages/beta"]\n'
    if archetype in {"python-web-api", "python-web-app"}:
        text += f'\n[archetype."{archetype}"]\n'
        if archetype == "python-web-app":
            text += 'frontend = "angular"\n'
    config.write_text(text + extra, encoding="utf-8")
    return tmp_path


def _ci(root: Path) -> str:
    config = KilnConfig.load(root)
    return {a.path: a.content for a in CICD.artifacts(config, root)}[
        ".github/workflows/ci.yml"
    ]


def _jobs(root: Path) -> dict[str, dict[str, object]]:
    return YamlUtils.load(_ci(root))["jobs"]


def _needs(root: Path) -> list[str]:
    return list(_jobs(root)["checks-ok"]["needs"])  # type: ignore[call-overload]


def _job(name: str, required: str = "") -> str:
    return f'\n[[ci.jobs]]\nname = "{name}"\nuses = "{CALL}"\n{required}'


def test_s15_1_3_1_required_defaults_true() -> None:
    assert CiJob(name="x", uses=CALL).required is True


def test_s15_1_3_2_required_job_gates(tmp_path: Path) -> None:
    extra = _job("gate", "required = true\n") + _job("advisory", "required = false\n")
    root = _write(tmp_path, extra=extra)
    jobs = _jobs(root)
    assert "gate" in jobs["checks-ok"]["needs"]  # type: ignore[operator]
    assert "advisory" not in jobs["checks-ok"]["needs"]  # type: ignore[operator]
    assert "gate" not in jobs["ci-ok"]["needs"]  # type: ignore[operator]
    assert jobs["advisory"]["needs"] == "validate"
    assert jobs["gate"]["needs"] == "validate"


def test_s15_1_3_3_registry_jobs_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _write(tmp_path, extra="\n[ci.checks]\nscorecard = true\n")
    jobs = _jobs(root)
    assert "secret-scan" in jobs["checks-ok"]["needs"]  # type: ignore[operator]
    assert "secret-scan" not in jobs["ci-ok"]["needs"]  # type: ignore[operator]
    assert all("scorecard" not in j.get("needs", []) for j in jobs.values())

    gating = replace(registry.CHECKS[-1], name="injected", job="injected-job")
    gating = replace(gating, gates=True, switch=registry.Switch.STANDARD)
    monkeypatch.setattr(registry, "CHECKS", (*registry.CHECKS, gating))
    needs = _needs(root)
    assert "injected-job" in needs
    assert "scorecard" not in needs


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_1_3_4_default_render_is_unchanged(tmp_path: Path, archetype: str) -> None:
    plain = _needs(_write(tmp_path / "plain", archetype))
    off = _needs(
        _write(tmp_path / "off", archetype, "\n[ci.checks]\nsecret-scan = false\n")
    )
    assert [n for n in plain if n != "secret-scan"] == off
    assert "secret-scan" not in off


# S15.4.2 — the `plan` job runs `task ci:requirements`.


def _plan_steps(root: Path) -> list[str]:
    steps = _jobs(root)["plan"]["steps"]
    return [str(s.get("run", s.get("name"))) for s in steps]  # type: ignore[union-attr]


def test_s15_4_2_2_plan_job_step(tmp_path: Path) -> None:
    two = _plan_steps(_write(tmp_path / "two"))
    assert "task ci:requirements" in two
    assert two.index("task ci:requirements") < two.index(
        'task ci:plan >> "$GITHUB_OUTPUT"'
    )

    one_root = _write(tmp_path / "one")
    config = one_root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            '["packages/alpha", "packages/beta"]', '["packages/alpha"]'
        ),
        encoding="utf-8",
    )
    assert "task ci:requirements" not in _plan_steps(one_root)

    for archetype in ARCHETYPES:
        if archetype == "python-lib":
            continue
        root = _write(tmp_path / archetype, archetype)
        assert "task ci:requirements" not in _ci(root)


# S15.8.7 — one `ci-ok` logic, and the pre-release barrier.

STEP_IF = "contains(needs.*.result, 'failure') || contains(needs.*.result, 'cancelled')"


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_8_7_1_same_steps(tmp_path: Path, archetype: str) -> None:
    ci = _ci(_write(tmp_path, archetype))
    assert "jq" not in ci
    jobs = YamlUtils.load(ci)["jobs"]
    for name in ("ci-ok", "checks-ok"):
        job = jobs[name]
        assert job["if"] == "always()"
        assert job["permissions"] == {}
        assert [(s["if"], s["run"]) for s in job["steps"]] == [(STEP_IF, "exit 1")]


def _barrier(archetype: str, sonar: bool) -> list[str]:
    needs = ["validate", "dependency-review"]
    if archetype == "node-lib":
        needs += ["test-cloud", "test-local", "smoke"]
    else:
        needs += ["plan", "test", "integration", "smoke", "suites"]
    return needs + (["sonar"] if sonar else []) + ["secret-scan"]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_8_7_2_barrier_needs(tmp_path: Path, archetype: str) -> None:
    extra = _job("gate", "required = true\n") + _job("advisory", "required = false\n")
    root = _write(tmp_path / "on", archetype, extra)
    assert _needs(root) == [*_barrier(archetype, True), "gate"]
    off = _write(tmp_path / "off", archetype)
    config = off / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("sonar = true", "sonar = false"),
        encoding="utf-8",
    )
    assert _needs(off) == _barrier(archetype, False)


def _after(archetype: str) -> list[str]:
    if archetype == "node-lib":
        return ["docs"]
    if archetype == "python-lib":
        return ["release", "external-install", "docs"]
    return ["release"]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_8_7_3_ci_ok_needs(tmp_path: Path, archetype: str) -> None:
    extra = _job("gate", "required = true\n")
    jobs = _jobs(_write(tmp_path, archetype, extra))
    assert jobs["ci-ok"]["needs"] == ["checks-ok", *_after(archetype)]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_8_7_4_release_waits_on_the_barrier(tmp_path: Path, archetype: str) -> None:
    jobs = _jobs(_write(tmp_path, archetype))
    if "release" not in jobs:
        # node-lib releases from `release.yml` until S15.8.5 moves it here.
        assert archetype == "node-lib"
        return
    release = jobs["release"]
    assert release["needs"] == ["plan", "checks-ok"]
    condition = str(release["if"])
    assert "needs.checks-ok.result == 'success'" in condition
    assert "!cancelled()" in condition
    assert "always()" not in condition
    assert "needs.sonar" not in condition
    assert "needs.validate" not in condition
    if archetype == "python-lib":
        assert "release-order != '[]'" in condition


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_8_7_5_skipped_passes(tmp_path: Path, archetype: str) -> None:
    jobs = _jobs(_write(tmp_path, archetype))
    for name in ("ci-ok", "checks-ok"):
        for step in jobs[name]["steps"]:  # type: ignore[attr-defined]
            assert "skipped" not in f"{step.get('if', '')}{step.get('run', '')}"


# S15.3.3 — the `secret-scan` job gates `release` and `ci-ok`.

FORK_GUARD = (
    "${{ github.event_name != 'pull_request' || "
    "github.event.pull_request.head.repo.full_name == github.repository }}"
)
OFF = "\n[ci.checks]\nsecret-scan = false\n"


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_3_3_1_job_shape(tmp_path: Path, archetype: str) -> None:
    job = _jobs(_write(tmp_path, archetype))["secret-scan"]
    assert job["runs-on"] == "ubuntu-latest"
    assert job["timeout-minutes"] == 10
    assert job["permissions"] == {"contents": "read"}
    steps = job["steps"]  # type: ignore[index]
    assert steps[0]["with"] == {"fetch-depth": 0, "persist-credentials": False}
    assert "actions/checkout" in steps[0]["uses"]
    assert steps[1]["uses"] == "./.github/actions/setup"
    assert [s.get("run") for s in steps[2:]] == ["task ci:lint:secrets"]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_3_3_2_fork_guard(tmp_path: Path, archetype: str) -> None:
    assert _jobs(_write(tmp_path, archetype))["secret-scan"]["if"] == FORK_GUARD


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_3_3_3_gates(tmp_path: Path, archetype: str) -> None:
    jobs = _jobs(_write(tmp_path, archetype))
    assert "secret-scan" in jobs["checks-ok"]["needs"]  # type: ignore[operator]
    assert "secret-scan" not in jobs["ci-ok"]["needs"]  # type: ignore[operator]
    steps = jobs["checks-ok"]["steps"]  # type: ignore[index]
    # A skipped scan passes, as dependency-review's does: no step tests for it.
    assert all("skipped" not in f"{s.get('if', '')}{s.get('run', '')}" for s in steps)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_3_3_3b_failed_scan_blocks_release(tmp_path: Path, archetype: str) -> None:
    jobs = _jobs(_write(tmp_path, archetype))
    if "release" not in jobs:
        assert archetype == "node-lib"  # releases from `release.yml` until S15.8.5
        return
    needs = jobs["release"]["needs"]
    assert "checks-ok" in (needs if isinstance(needs, list) else [needs])
    assert "needs.checks-ok.result == 'success'" in str(jobs["release"]["if"])
    assert "secret-scan" in jobs["checks-ok"]["needs"]  # type: ignore[operator]
    assert STEP_IF in jobs["checks-ok"]["steps"][0]["if"]  # type: ignore[index]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s15_3_3_4_off(tmp_path: Path, archetype: str) -> None:
    root = _write(tmp_path, archetype, OFF)
    assert "secret-scan" not in _jobs(root)
    assert "secret-scan" not in _needs(root)


def test_s15_3_3_5_declared_name() -> None:
    from rn_forge.kiln.modules.cicd.config import GENERATED_JOBS

    assert "secret-scan" in GENERATED_JOBS
