"""The node package job and dispatch release."""

from __future__ import annotations
import pytest
from pathlib import Path
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.pins import load_pins
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS
from tests.modules.cicd.support import (
    ARCHETYPES,
    CI_YML,
    _ci_jobs,
    _node_lib_ci,
    _rendered,
    _root,
)


def test_s9_1_4_1_package_job_matches_ngkit(tmp_path: Path) -> None:
    job = _node_lib_ci(tmp_path)["jobs"]["smoke"]  # type: ignore[index]
    pins = load_pins()
    assert job["needs"] == ["validate", "test-cloud", "test-local"]
    assert job["if"] == (
        "${{ always() && (needs.test-cloud.result == 'success' "
        "|| needs.test-local.result == 'success') }}"
    )
    assert job["timeout-minutes"] == 15
    assert job["permissions"] == {"contents": "read"}
    checkout, setup, pack, upload = job["steps"]
    assert checkout["with"] == {
        "filter": "tree:0",
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    assert setup["uses"].startswith("./.github/actions/setup")
    assert pack["run"] == "task ci:smoke"
    upload_pin = pins["upload-artifact"]
    assert upload["uses"] == f"{upload_pin['uses']}@{upload_pin['sha']}"
    assert upload["with"] == {
        "name": "package-tarballs",
        "path": "dist/tarballs/*.tgz",
        "retention-days": 14,
    }


def test_s9_1_4_3_ci_ok_needs_smoke_even_without_sonar(tmp_path: Path) -> None:
    on = _ci_jobs(_root(tmp_path / "on", "node-lib"))
    assert on["checks-ok"]["needs"][-2:] == ["sonar", "secret-scan"]  # type: ignore[index]
    off = _ci_jobs(_root(tmp_path / "off", "node-lib", sonar=False))
    assert off["checks-ok"]["needs"][-2:] == ["smoke", "secret-scan"]  # type: ignore[index]
    assert off["ci-ok"]["needs"] == ["checks-ok", "release", "verify-release", "docs"]  # type: ignore[index]
    assert "smoke" in off


RELEASE_YML = ".github/workflows/release.yml"


def test_s9_1_5_1_nx_dispatch_is_node_libs_default(tmp_path: Path) -> None:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        'schema_version = 1\n\n[repository]\nname = "demo"\nowner = "rn-forge"\narchetype = "node-lib"\n',
        encoding="utf-8",
    )
    rendered = _rendered(tmp_path)
    assert RELEASE_YML not in rendered
    assert "release" in YamlUtils.load(rendered[CI_YML])["jobs"]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s9_1_5_1_nx_dispatch_is_refused_elsewhere(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype, release="nx-dispatch")
    with pytest.raises(ValueError, match=r"ci\.release"):
        _rendered(root)


@pytest.mark.parametrize("release", ["tag-exists", "pypi"])
def test_s9_1_5_1_node_lib_refuses_the_other_modes(
    tmp_path: Path, release: str
) -> None:
    root = _root(tmp_path, "node-lib", release=release)
    with pytest.raises(ValueError, match=r"ci\.release"):
        _rendered(root)


def test_s9_1_5_2_release_none_renders_no_release_yml_and_no_release_tasks(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "node-lib", release="none")
    rendered = _rendered(root)
    assert RELEASE_YML not in rendered
    jobs = YamlUtils.load(rendered[CI_YML])["jobs"]
    assert "release" not in jobs
    assert "release" not in jobs["ci-ok"]["needs"]
    config = KilnConfig.load(root)
    tasks = {a.path: a.content for a in TASKS.artifacts(config, root)}["tasks/ci.yml"]
    assert "release:" not in tasks
    assert "published-install" not in tasks


def test_s9_1_5_3_the_rendered_run_lines_name_no_forbidden_tool(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "node-lib")
    cycle.apply(root, home=tmp_path / "home")
    codes = [f.code for f in checks.run(root)]
    assert not [c for c in codes if c.startswith("ci.entrypoint")], codes
