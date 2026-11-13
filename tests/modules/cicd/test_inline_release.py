"""The library workspace's release job runs inline in `ci.yml` (S6.11.1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from rn_forge.commons.fs.documents import YamlUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd import CICD

CONFIG = """
schema_version = 1

[repository]
name = "demo"
owner = "rn-forge"
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
DEFAULT_RELEASE = {"python-lib": "pypi", "node-lib": "nx-dispatch"}
ARCHETYPES = (
    "python-tool",
    "python-app",
    "python-web-api",
    "python-web-app",
    "python-lib",
    "node-lib",
)
CI_YML = ".github/workflows/ci.yml"
RELEASE_YML = ".github/workflows/_release.yml"
COMMON_STEPS = [
    "Checkout",
    "Set up the toolchain",
    "Download the check markers",
    "Build releases",
    "Generate provenance",
]


def _render(
    tmp_path: Path, archetype: str, release: str | None = None
) -> dict[str, str]:
    release = release or DEFAULT_RELEASE.get(archetype, "tag-exists")
    root = tmp_path / f"{archetype}-{release}"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    text = CONFIG.format(archetype=archetype, release=release)
    if archetype == "python-lib":
        text += PACKAGES
    elif archetype in {"python-web-api", "python-web-app"}:
        text += f'\n[archetype."{archetype}"]\n'
        if archetype == "python-web-app":
            text += 'frontend = "angular"\n'
    config.write_text(text, encoding="utf-8")
    loaded = KilnConfig.load(root)
    return {a.path: a.content for a in CICD.artifacts(loaded, root)}


def _release_job(files: dict[str, str]) -> dict[str, Any]:
    return YamlUtils.load(files[CI_YML])["jobs"]["release"]


@pytest.mark.parametrize("release", ["pypi", "tag-exists"])
def test_s6_11_1_1_no_reusable_release(tmp_path: Path, release: str) -> None:
    files = _render(tmp_path, "python-lib", release)
    assert RELEASE_YML not in files
    job = _release_job(files)
    assert job["steps"]
    assert "uses" not in job


@pytest.mark.parametrize("release", ["pypi", "tag-exists"])
def test_s6_11_1_2_same_steps(tmp_path: Path, release: str) -> None:
    job = _release_job(_render(tmp_path, "python-lib", release))
    pypi = release == "pypi"
    expected = [
        *COMMON_STEPS,
        *(["Attest PyPI publish"] if pypi else []),
        "Publish releases",
    ]
    assert [s["name"] for s in job["steps"]] == expected
    assert job["permissions"] == {
        "contents": "write",
        "id-token": "write",
        "attestations": "write",
    }
    if pypi:
        assert job["environment"] == "${{ inputs.testpypi && 'testpypi' || 'pypi' }}"
    else:
        assert "environment" not in job
    assert "inputs.release-order" not in str(job)
    assert "needs.plan.outputs.release-order" in str(job["steps"])


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s6_11_1_3_upload_in_top_level(tmp_path: Path, archetype: str) -> None:
    files = _render(tmp_path, archetype)
    if DEFAULT_RELEASE.get(archetype) != "pypi":
        return  # only a `release = "pypi"` upload needs the top-level workflow
    for path, text in files.items():
        if path.startswith(".github/workflows/"):
            called = "workflow_call" in YamlUtils.load(text)["on"]
            assert not (called and "task ci:release:publish" in text), path


@pytest.mark.parametrize(
    "archetype",
    ["python-tool", "python-app", "python-web-api", "python-web-app", "node-lib"],
)
def test_s6_11_1_4_others_unchanged(tmp_path: Path, archetype: str) -> None:
    files = _render(tmp_path, archetype)
    assert RELEASE_YML in files
    assert _release_job(files)["uses"] == "./.github/workflows/_release.yml"
