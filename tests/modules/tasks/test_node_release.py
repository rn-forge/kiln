"""S15.8.5 — the `node-lib` release tasks, run in a temporary git repository.

The rendered cell is copied into a repository with a local bare `origin`, and
`gh`, `pnpm` and `node` are fakes on `PATH` that log their arguments, so no test
reaches the network or a real GitHub.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from rn_forge.commons.fs.documents import YamlUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS

CONFIG = """
schema_version = 1

[repository]
name = "demo"
owner = "rn-forge"
archetype = "node-lib"

[docs]
profile = "mkdocs"
"""

pytestmark = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("task", "git", "bash", "node")),
    reason="task, git, bash and node are needed",
)

Run = Callable[..., subprocess.CompletedProcess[str]]


@pytest.fixture(scope="module")
def cell(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("cell")
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    cycle.apply(root, home=root / "home")
    shutil.rmtree(root / "home", ignore_errors=True)
    return root


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _project(repo: Path, name: str, version: str, tags: str = "publishable") -> None:
    folder = repo / "libs" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "project.json").write_text(
        json.dumps({"name": name, "tags": tags.split(",")}), encoding="utf-8"
    )
    (folder / "package.json").write_text(
        json.dumps({"name": name, "version": version}), encoding="utf-8"
    )


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def repo(cell: Path, tmp_path: Path) -> Path:
    work = tmp_path / "work"
    shutil.copytree(cell, work)
    _git(work, "init", "-q", "-b", "main")
    _project(work, "a", "1.2.3")
    _project(work, "b", "1.2.3")
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "c")
    remote = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    _git(work, "remote", "add", "origin", str(remote))
    return work


@pytest.fixture
def run(repo: Path, tmp_path: Path) -> Run:
    """Run `task <name>` in `repo`, with fake gh, pnpm and node first on PATH.

    `view` is what `gh release view <tag> --json isDraft` reports: `none` (no
    release), `draft` or `published`. Every fake appends its arguments to the log.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    output = tmp_path / "output"

    def go(
        *args: str,
        env: dict[str, str] | None = None,
        view: str = "none",
        tarball: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        reply = {"none": "exit 1", "draft": "echo true", "published": "echo false"}
        _stub(
            bin_dir,
            "gh",
            f'echo "gh $*" >> "{log}"\n'
            f'case "$*" in "release view"*) {reply[view]} ;; esac',
        )
        make = "mkdir -p dist/tarballs; : > dist/tarballs/x.tgz" if tarball else ":"
        _stub(bin_dir, "pnpm", f'echo "pnpm $*" >> "{log}"\n{make}')
        # `-e` is `task version` reading package.json files; the release-notes script is faked.
        real = shutil.which("node")
        _stub(
            bin_dir,
            "node",
            f'if [ "$1" = -e ]; then exec "{real}" "$@"; fi\necho "node $*" >> "{log}"; echo notes',
        )
        return subprocess.run(
            ["task", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            env={
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "GITHUB_OUTPUT": str(output),
                "RUNNER_TEMP": str(tmp_path),
                "GITHUB_REF_NAME": "main",
                **(env or {}),
            },
        )

    return go


def _calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "calls.log"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def _outputs(tmp_path: Path) -> dict[str, str]:
    text = (tmp_path / "output").read_text(encoding="utf-8")
    return dict(line.split("=", 1) for line in text.splitlines())


def _tasks(cell: Path) -> dict[str, dict[str, object]]:
    rendered = {a.path: a.content for a in TASKS.artifacts(KilnConfig.load(cell), cell)}
    return YamlUtils.load(rendered["tasks/ci.yml"])["tasks"]


def _retag(repo: Path, version: str) -> None:
    for name in ("a", "b"):
        _project(repo, name, version)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", f"bump {version}")


def test_s15_8_5_3_state_new(run: Run, tmp_path: Path) -> None:
    done = run("ci:release:state")
    assert done.returncode == 0, done.stdout + done.stderr
    assert _outputs(tmp_path) == {
        "tag": "v1.2.3",
        "mode": "new",
        "first-release": "true",
        "dist-tag": "latest",
    }


@pytest.mark.parametrize(
    ("version", "dist"),
    [("1.2.3", "latest"), ("1.3.0-rc.1", "rc"), ("2.0.0-beta.0", "beta")],
)
def test_s15_8_5_3_state_dist_tag(
    run: Run, repo: Path, tmp_path: Path, version: str, dist: str
) -> None:
    _retag(repo, version)
    assert run("ci:release:state").returncode == 0
    assert _outputs(tmp_path)["dist-tag"] == dist
    assert _outputs(tmp_path)["tag"] == f"v{version}"


def test_s15_8_5_3_state_first_release_means_no_other_v_tag(
    run: Run, repo: Path, tmp_path: Path
) -> None:
    _git(repo, "tag", "v1.0.0")
    assert run("ci:release:state").returncode == 0
    assert _outputs(tmp_path)["first-release"] == "false"
    assert _outputs(tmp_path)["mode"] == "new"


@pytest.mark.parametrize(
    ("view", "mode"),
    [("none", "resume"), ("draft", "resume"), ("published", "released")],
)
def test_s15_8_5_3_state_of_a_tagged_version(
    run: Run, repo: Path, tmp_path: Path, view: str, mode: str
) -> None:
    _git(repo, "tag", "v1.2.3")
    assert run("ci:release:state", view=view).returncode == 0
    outputs = _outputs(tmp_path)
    assert outputs["mode"] == mode
    # A resumed first release is still a first release.
    assert outputs["first-release"] == "true"


def test_s15_8_5_3_state_fails_when_the_versions_differ(
    run: Run, repo: Path, tmp_path: Path
) -> None:
    _project(repo, "b", "1.2.4")
    done = run("ci:release:state")
    assert done.returncode != 0
    assert "Expected one version" in done.stdout + done.stderr
    assert not (tmp_path / "output").exists()


def test_s15_8_5_3_state_ignores_untagged_projects(run: Run, repo: Path) -> None:
    _project(repo, "app", "9.9.9", tags="scope:app")
    assert run("ci:release:state").returncode == 0


def test_s15_8_5_3_state_refuses_a_tag_that_is_not_at_head(
    run: Run, repo: Path
) -> None:
    _git(repo, "tag", "v1.2.3")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "later")
    done = run("ci:release:state", view="draft")
    assert done.returncode != 0
    assert "is not at HEAD" in done.stdout + done.stderr


def test_s15_8_5_4_new_mode_tags_head_and_pushes_the_tag_only(
    run: Run, repo: Path
) -> None:
    assert run("ci:release:tag", env={"TAG": "v1.2.3"}).returncode == 0
    assert _git(repo, "rev-parse", "v1.2.3^{commit}") == _git(repo, "rev-parse", "HEAD")
    done = run("ci:release:push", env={"TAG": "v1.2.3"})
    assert done.returncode == 0, done.stdout + done.stderr
    assert "refs/tags/v1.2.3" in _git(repo, "ls-remote", "origin")
    assert _git(repo, "ls-remote", "--heads", "origin") == ""


def test_s15_8_5_5_verify_rebuilds_dist_from_the_tagged_source(
    run: Run, cell: Path, tmp_path: Path
) -> None:
    done = run("ci:release:verify", tarball=True)
    assert done.returncode == 0, done.stdout + done.stderr
    assert _calls(tmp_path) == [
        "pnpm exec nx run-many -t pack verify-dist verify-consumer -p tag:publishable"
    ]
    assert "MODE" not in "\n".join(_tasks(cell)["release:verify"]["cmds"])  # type: ignore[arg-type]


def test_s15_8_5_5_verify_fails_without_a_tarball(run: Run) -> None:
    done = run("ci:release:verify")
    assert done.returncode != 0
    assert "::error::No tarball in dist/tarballs" in done.stdout + done.stderr


@pytest.mark.parametrize(
    ("flag", "tail"), [("", ""), ("--first-release", " --first-release")]
)
def test_s15_8_5_6_publish_takes_its_flags_from_the_state(
    run: Run, tmp_path: Path, flag: str, tail: str
) -> None:
    done = run("ci:release:publish", env={"DIST_TAG": "rc", "FIRST_RELEASE_FLAG": flag})
    assert done.returncode == 0, done.stdout + done.stderr
    assert _calls(tmp_path) == [
        f"pnpm exec nx release publish --tag=rc --excludeTaskDependencies{tail}"
    ]


def test_s15_8_5_7_version_prints_the_release_version(run: Run) -> None:
    done = run("version")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "1.2.3"


def test_s15_8_5_7_version_with_a_bump_runs_nx_and_nothing_else(
    run: Run, tmp_path: Path
) -> None:
    done = run("version", "--", "minor")
    assert done.returncode == 0, done.stdout + done.stderr
    assert _calls(tmp_path) == [
        "pnpm exec nx release version minor --git-commit=false --git-tag=false --stage-changes=false"
    ]
    assert done.stdout.strip() == ""


def test_s15_8_5_11_draft_until_published(run: Run, tmp_path: Path, repo: Path) -> None:
    (repo / "dist" / "tarballs").mkdir(parents=True)
    (repo / "dist" / "tarballs" / "x.tgz").write_text("")
    assert run("ci:release:github", env={"TAG": "v1.2.3"}).returncode == 0
    creates = [c for c in _calls(tmp_path) if c.startswith("gh release create")]
    assert len(creates) == 1
    assert creates[0].startswith("gh release create v1.2.3 ")
    assert creates[0].endswith(" --draft")
    (tmp_path / "calls.log").unlink()
    assert run("ci:release:finalize", env={"TAG": "v1.2.3"}).returncode == 0
    assert _calls(tmp_path) == ["gh release edit v1.2.3 --draft=false"]


def test_s15_8_5_11_only_three_tasks_create_or_edit_a_release(cell: Path) -> None:
    for name, task in _tasks(cell).items():
        text = "\n".join(str(c) for c in task.get("cmds", []))  # type: ignore[attr-defined]
        touches = "gh release create" in text or "gh release edit" in text
        assert touches is (
            name in {"release:github", "release:finalize", "release:latest"}
        ), name
        if name != "release:latest":
            assert "gh release create" not in text or "--draft" in text, name


def test_s15_8_5_12_resume_after_a_partial_publish(
    run: Run, repo: Path, tmp_path: Path
) -> None:
    _git(repo, "tag", "v1.2.3")
    (repo / "dist" / "tarballs").mkdir(parents=True)
    (repo / "dist" / "tarballs" / "x.tgz").write_text("")
    assert run("ci:release:state", view="draft").returncode == 0
    outputs = _outputs(tmp_path)
    assert (outputs["mode"], outputs["first-release"]) == ("resume", "true")

    assert run("ci:release:github", env={"TAG": "v1.2.3"}, view="draft").returncode == 0
    gh = [c for c in _calls(tmp_path) if "release delete" in c or "release create" in c]
    assert gh[0] == "gh release delete v1.2.3 --yes"
    assert gh[1].startswith("gh release create v1.2.3 ") and gh[1].endswith("--draft")

    (tmp_path / "calls.log").unlink()
    flag = "--first-release"
    env = {"DIST_TAG": outputs["dist-tag"], "FIRST_RELEASE_FLAG": flag}
    assert run("ci:release:publish", env=env).returncode == 0
    assert _calls(tmp_path) == [
        "pnpm exec nx release publish --tag=latest --excludeTaskDependencies --first-release"
    ]
    assert run("ci:release:finalize", env={"TAG": "v1.2.3"}).returncode == 0
    assert "gh release edit v1.2.3 --draft=false" in _calls(tmp_path)

    assert run("ci:release:state", view="published").returncode == 0
    assert _outputs(tmp_path)["mode"] == "released"
