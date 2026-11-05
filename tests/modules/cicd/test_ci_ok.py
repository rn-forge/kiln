"""S15.1.3 — `ci-ok`'s `needs` come from the registry and each job's `required`."""

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
    return list(_jobs(root)["ci-ok"]["needs"])  # type: ignore[call-overload]


def _job(name: str, required: str = "") -> str:
    return f'\n[[ci.jobs]]\nname = "{name}"\nuses = "{CALL}"\n{required}'


def test_s15_1_3_1_required_defaults_true() -> None:
    assert CiJob(name="x", uses=CALL).required is True


def test_s15_1_3_2_required_job_gates(tmp_path: Path) -> None:
    extra = _job("gate", "required = true\n") + _job("advisory", "required = false\n")
    root = _write(tmp_path, extra=extra)
    jobs = _jobs(root)
    assert "gate" in jobs["ci-ok"]["needs"]  # type: ignore[operator]
    assert "advisory" not in jobs["ci-ok"]["needs"]  # type: ignore[operator]
    assert jobs["advisory"]["needs"] == "validate"
    assert jobs["gate"]["needs"] == "validate"


def test_s15_1_3_3_registry_jobs_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The `secret-scan` half waits for S15.3.3, which gives the row its job; until
    # then a gating row injected here proves `check_jobs` reaches `ci-ok`.
    root = _write(tmp_path, extra="\n[ci.checks]\nscorecard = true\n")
    jobs = _jobs(root)
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
    assert plain == off
    assert "secret-scan" not in plain
