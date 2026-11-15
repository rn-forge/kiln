"""One Pages site."""

from __future__ import annotations
import subprocess
from pathlib import Path
from rn_forge.kiln.modules.cicd.artifacts import load_pins
from rn_forge.kiln.modules.core import cycle
from tests.conftest import requires
from tests.modules.cicd.support import (
    CI_YML,
    DOCS_HOOKS,
    _ci_jobs,
    _job_steps,
    _node_lib_ci,
    _rendered,
    _root,
    _with_ci,
)


SITE_ROOT = Path(__file__).resolve().parents[3]


def _docs_job(tmp_path: Path) -> dict[str, object]:
    return _node_lib_ci(tmp_path)["jobs"]["docs"]  # type: ignore[index,return-value]


def test_s9_1_11_1_node_lib_renders_no_docs_yml_and_one_docs_job(
    tmp_path: Path,
) -> None:
    rendered = _rendered(_root(tmp_path / "files", "node-lib"))
    assert ".github/workflows/docs.yml" not in rendered
    job = _docs_job(tmp_path / "jobs")
    assert job["needs"] == ["checks-ok", "release", "verify-release"]
    assert job["if"] == (
        "${{ !cancelled() && needs.checks-ok.result == 'success' && "
        "!contains(needs.*.result, 'failure') && "
        "!contains(needs.*.result, 'cancelled') && "
        "github.event_name == 'push' && github.ref_name == 'main' }}"
    )
    assert job["timeout-minutes"] == 30
    assert job["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }
    assert job["environment"] == {
        "name": "github-pages",
        "url": "${{ steps.deployment.outputs.page_url }}",
    }
    assert job["concurrency"] == {"group": "pages", "cancel-in-progress": False}


def test_s9_1_11_1_node_lib_without_mkdocs_has_no_docs_job(tmp_path: Path) -> None:
    jobs = _ci_jobs(_root(tmp_path, "node-lib", profile="none"))
    assert "docs" not in jobs
    assert "docs" not in jobs["ci-ok"]["needs"]  # type: ignore[index,operator]


def test_s9_1_11_2_steps(tmp_path: Path) -> None:
    pins = load_pins()
    steps = _docs_job(tmp_path)["steps"]
    checkout, setup, mkdocs, site, pages, upload, deploy = steps  # type: ignore[misc]
    assert checkout["with"] == {
        "filter": "tree:0",
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    assert setup["uses"].startswith("./.github/actions/setup")
    assert "if" not in mkdocs
    assert mkdocs["run"] == "task docs:build"
    assert site["run"] == "task ci:docs:site"
    for step, name in ((pages, "configure-pages"), (upload, "upload-pages-artifact")):
        assert step["uses"] == f"{pins[name]['uses']}@{pins[name]['sha']}"
    assert upload["with"] == {"path": ".docs-site", "include-hidden-files": True}
    assert deploy["id"] == "deployment"
    assert (
        deploy["uses"]
        == f"{pins['deploy-pages']['uses']}@{pins['deploy-pages']['sha']}"
    )


def test_s9_3_1_3_docs_job_steps_have_no_id_env_or_if(tmp_path: Path) -> None:
    job = _docs_job(tmp_path)
    steps = job["steps"]
    assert [s.get("uses", s.get("run")) for s in steps][2:4] == [  # type: ignore[attr-defined,union-attr]
        "task docs:build",
        "task ci:docs:site",
    ]
    for step in steps:  # type: ignore[attr-defined]
        assert "env" not in step
        assert "if" not in step
        assert step.get("id") in (None, "deployment")
    assert job["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }


def test_s9_3_1_3_nx_set_shas_is_used_twice(tmp_path: Path) -> None:
    text = _root(tmp_path, "node-lib") / CI_YML
    cycle.apply(_root(tmp_path / "r", "node-lib"), home=tmp_path / "home")
    text = (tmp_path / "r" / CI_YML).read_text(encoding="utf-8")
    assert text.count("nrwl/nx-set-shas") == 2


def test_s9_1_11_2_docs_hooks_run_on_the_assembled_site(tmp_path: Path) -> None:
    root = _with_ci(_root(tmp_path, "node-lib"), DOCS_HOOKS)
    steps = _job_steps(root, ".github/workflows/ci.yml", "docs")
    site = next(i for i, s in enumerate(steps) if s.get("run") == "task ci:docs:site")
    assert steps[site + 1 : site + 3] == [
        {
            "name": f"Run ./.github/actions/{n}",
            "uses": f"./.github/actions/{n}",
            "env": {"SITE_DIR": ".docs-site"},
        }
        for n in ("a", "b")
    ]


@requires("actionlint")
def test_s9_1_11_2_actionlint_passes(tmp_path: Path) -> None:
    root = _root(tmp_path, "node-lib")
    cycle.apply(root, home=tmp_path / "home")
    result = subprocess.run(
        ["actionlint", ".github/workflows/ci.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_s9_1_11_6_the_idea_row_is_gone() -> None:
    ideas = (SITE_ROOT / "docs" / "specs" / "ideas" / "index.md").read_text(
        encoding="utf-8"
    )
    assert "node-docs-site-assembly" not in ideas
