"""The `node-lib` release tasks, run in a temporary git repository.

The rendered cell is copied into a repository with a local bare `origin`, and
`gh`, `pnpm`, `uv` and `node` are fakes on `PATH` that log their arguments, so no test
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
from tests.conftest import git, requires, write_config
from rn_forge.commons.fs.documents import YamlUtils

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS

pytestmark = requires("task", "git", "bash", "node")

Run = Callable[..., subprocess.CompletedProcess[str]]


def _render_cell(root: Path, tail: str = "") -> Path:
    write_config(root, "node-lib", name="demo", docs="mkdocs", tail=tail)
    cycle.apply(root, home=root / "home")
    shutil.rmtree(root / "home", ignore_errors=True)
    return root


@pytest.fixture(scope="module")
def cell(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _render_cell(tmp_path_factory.mktemp("cell"))


@pytest.fixture(scope="module")
def independent_cell(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _render_cell(
        tmp_path_factory.mktemp("independent"),
        '\n[archetype.node-lib]\nrelease_group = "independent"\n',
    )


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


def _repo(cell: Path, tmp_path: Path, versions: dict[str, str]) -> Path:
    work = tmp_path / "work"
    shutil.copytree(cell, work)
    git(work, "init", "-q", "-b", "main")
    for name, version in versions.items():
        _project(work, name, version)
    git(work, "add", "-A")
    git(work, "commit", "-qm", "c")
    remote = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(work, "remote", "add", "origin", str(remote))
    return work


@pytest.fixture
def repo(cell: Path, tmp_path: Path) -> Path:
    return _repo(cell, tmp_path, {"a": "1.2.3", "b": "1.2.3"})


@pytest.fixture
def independent_repo(independent_cell: Path, tmp_path: Path) -> Path:
    return _repo(independent_cell, tmp_path, {"a": "1.2.3", "b": "2.0.0"})


def _runner(repo: Path, tmp_path: Path) -> Run:
    """Run `task <name>` in `repo`, with fake gh, pnpm, uv and uvx first on PATH.

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
        _stub(bin_dir, "uv", f'echo "uv $*" >> "{log}"\ncat > /dev/null')
        # `uvx` is `{{.DEVOPS}}`: the notes command is faked.
        _stub(bin_dir, "uvx", f'echo "uvx $*" >> "{log}"; echo notes')
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


@pytest.fixture
def run(repo: Path, tmp_path: Path) -> Run:
    return _runner(repo, tmp_path)


@pytest.fixture
def independent_run(independent_repo: Path, tmp_path: Path) -> Run:
    return _runner(independent_repo, tmp_path)


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
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", f"bump {version}")


def test_state_new(run: Run, tmp_path: Path) -> None:
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
def test_state_dist_tag(
    run: Run, repo: Path, tmp_path: Path, version: str, dist: str
) -> None:
    _retag(repo, version)
    assert run("ci:release:state").returncode == 0
    assert _outputs(tmp_path)["dist-tag"] == dist
    assert _outputs(tmp_path)["tag"] == f"v{version}"


def test_state_first_release_means_no_other_v_tag(
    run: Run, repo: Path, tmp_path: Path
) -> None:
    git(repo, "tag", "v1.0.0")
    assert run("ci:release:state").returncode == 0
    assert _outputs(tmp_path)["first-release"] == "false"
    assert _outputs(tmp_path)["mode"] == "new"


@pytest.mark.parametrize(
    ("view", "mode"),
    [("none", "resume"), ("draft", "resume"), ("published", "released")],
)
def test_state_of_a_tagged_version(
    run: Run, repo: Path, tmp_path: Path, view: str, mode: str
) -> None:
    git(repo, "tag", "v1.2.3")
    assert run("ci:release:state", view=view).returncode == 0
    outputs = _outputs(tmp_path)
    assert outputs["mode"] == mode
    # A resumed first release is still a first release.
    assert outputs["first-release"] == "true"


def test_state_fails_when_the_versions_differ(
    run: Run, repo: Path, tmp_path: Path
) -> None:
    _project(repo, "b", "1.2.4")
    done = run("ci:release:state")
    assert done.returncode != 0
    assert "Expected one version" in done.stdout + done.stderr
    assert not (tmp_path / "output").exists()


def test_state_ignores_untagged_projects(run: Run, repo: Path) -> None:
    _project(repo, "app", "9.9.9", tags="scope:app")
    assert run("ci:release:state").returncode == 0


def test_state_refuses_a_tag_that_is_not_at_head(run: Run, repo: Path) -> None:
    git(repo, "tag", "v1.2.3")
    git(repo, "commit", "-q", "--allow-empty", "-m", "later")
    done = run("ci:release:state", view="draft")
    assert done.returncode != 0
    assert "is not at HEAD" in done.stdout + done.stderr


def test_new_mode_tags_head_and_pushes_the_tag_only(run: Run, repo: Path) -> None:
    assert run("ci:release:tag", env={"TAG": "v1.2.3"}).returncode == 0
    assert git(repo, "rev-parse", "v1.2.3^{commit}") == git(repo, "rev-parse", "HEAD")
    done = run("ci:release:push", env={"TAG": "v1.2.3"})
    assert done.returncode == 0, done.stdout + done.stderr
    assert "refs/tags/v1.2.3" in git(repo, "ls-remote", "origin")
    assert git(repo, "ls-remote", "--heads", "origin") == ""


def test_verify_rebuilds_dist_from_the_tagged_source(
    run: Run, cell: Path, tmp_path: Path
) -> None:
    done = run("ci:release:verify", tarball=True)
    assert done.returncode == 0, done.stdout + done.stderr
    assert _calls(tmp_path) == [
        "pnpm exec nx run-many -t pack verify-dist verify-consumer -p tag:publishable"
    ]
    assert "MODE" not in "\n".join(_tasks(cell)["release:verify"]["cmds"])  # type: ignore[arg-type]


def test_verify_fails_without_a_tarball(run: Run) -> None:
    done = run("ci:release:verify")
    assert done.returncode != 0
    assert "::error::No tarball in dist/tarballs" in done.stdout + done.stderr


@pytest.mark.parametrize(
    ("flag", "tail"), [("", ""), ("--first-release", " --first-release")]
)
def test_publish_takes_its_flags_from_the_state(
    run: Run, tmp_path: Path, flag: str, tail: str
) -> None:
    done = run("ci:release:publish", env={"DIST_TAG": "rc", "FIRST_RELEASE_FLAG": flag})
    assert done.returncode == 0, done.stdout + done.stderr
    assert _calls(tmp_path) == [
        f"pnpm exec nx release publish --tag=rc --excludeTaskDependencies{tail}"
    ]


def test_version_prints_the_release_version(run: Run) -> None:
    done = run("version")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "1.2.3"


BUMP = "pnpm exec nx release version {} --git-commit=false --git-tag=false --stage-changes=false"
CHANGELOG = (
    "pnpm exec nx release changelog 1.2.3 --git-commit=false --git-tag=false"
    " --stage-changes=false"
)


def _bump_calls(tmp_path: Path, spec: str, tail: str) -> None:
    calls = _calls(tmp_path)
    assert len(calls) >= 3, calls
    assert calls[0] == BUMP.format(spec)
    assert calls[1] == CHANGELOG + tail
    # The Markdown format task runs mdformat in batches: one call or several.
    assert all(c.startswith("uv run --group docs mdformat") for c in calls[2:])


def test_a_bump_writes_the_changelog_then_formats(run: Run, tmp_path: Path) -> None:
    done = run("version", "--", "minor")
    assert done.returncode == 0, done.stdout + done.stderr
    _bump_calls(tmp_path, "minor", " --first-release")
    assert done.stdout.strip() == ""


def test_no_first_release_flag_once_a_tag_exists(
    run: Run, tmp_path: Path, repo: Path
) -> None:
    git(repo, "tag", "v1.0.0")
    done = run("version", "--", "minor")
    assert done.returncode == 0, done.stdout + done.stderr
    _bump_calls(tmp_path, "minor", "")


def test_an_exact_version_is_passed_through(run: Run, tmp_path: Path) -> None:
    done = run("version", "--", "1.3.0")
    assert done.returncode == 0, done.stdout + done.stderr
    _bump_calls(tmp_path, "1.3.0", " --first-release")


def test_no_argument_has_no_side_effects(run: Run, tmp_path: Path) -> None:
    done = run("version")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "1.2.3"
    assert _calls(tmp_path) == []


def test_notes_come_from_kiln_devops(run: Run, repo: Path, tmp_path: Path) -> None:
    (repo / "dist" / "tarballs").mkdir(parents=True)
    (repo / "dist" / "tarballs" / "x.tgz").write_text("")
    assert run("ci:release:github", env={"TAG": "v1.2.3"}).returncode == 0
    notes = [c for c in _calls(tmp_path) if c.startswith("uvx ")]
    assert len(notes) == 1
    assert notes[0].endswith(" kiln-devops notes CHANGELOG.md 1.2.3")


def test_descriptions(cell: Path) -> None:
    rendered = {a.path: a.content for a in TASKS.artifacts(KilnConfig.load(cell), cell)}
    node = YamlUtils.load(rendered["tasks/node.yml"])["tasks"]["version"]["desc"]
    root = YamlUtils.load(rendered["Taskfile.yml"])["tasks"]["version"]["desc"]
    assert "CHANGELOG.md" in node
    assert "CHANGELOG.md" in root
    assert node == (
        "Print the publishable projects' version, or bump it, write its CHANGELOG.md"
        " section and format it (pass -- patch|minor|major|x.y.z); the root version"
        " task runs it."
    )
    assert root == (
        "Print the publishable projects' version, or bump it, write its CHANGELOG.md"
        " section and format it (pass -- patch|minor|major|x.y.z)."
    )


def test_draft_until_published(run: Run, tmp_path: Path, repo: Path) -> None:
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


def test_only_three_tasks_create_or_edit_a_release(cell: Path) -> None:
    for name, task in _tasks(cell).items():
        text = "\n".join(str(c) for c in task.get("cmds", []))  # type: ignore[attr-defined]
        touches = "gh release create" in text or "gh release edit" in text
        assert touches is (
            name in {"release:github", "release:finalize", "release:latest"}
        ), name
        if name != "release:latest":
            assert "gh release create" not in text or "--draft" in text, name


def test_resume_after_a_partial_publish(run: Run, repo: Path, tmp_path: Path) -> None:
    git(repo, "tag", "v1.2.3")
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


INDEPENDENT_BUMP = (
    "pnpm exec nx release version minor --projects=a --git-commit=false"
    " --git-tag=false --stage-changes=false"
)
INDEPENDENT_CHANGELOG = (
    "pnpm exec nx release changelog 1.2.3 --projects=a --git-commit=false"
    " --git-tag=false --stage-changes=false"
)


def test_independent_version_prints_each_project(
    independent_run: Run, tmp_path: Path
) -> None:
    done = independent_run("version")
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.strip() == "a 1.2.3\nb 2.0.0"
    assert _calls(tmp_path) == []


def test_independent_bump_versions_one_project(
    independent_run: Run, tmp_path: Path
) -> None:
    done = independent_run("version", "--", "minor", "a")
    assert done.returncode == 0, done.stdout + done.stderr
    calls = _calls(tmp_path)
    assert calls[0] == INDEPENDENT_BUMP
    assert calls[1] == INDEPENDENT_CHANGELOG + " --first-release"
    assert len(calls) >= 3
    assert all(c.startswith("uv run --group docs mdformat") for c in calls[2:])


@pytest.mark.parametrize(
    ("tag", "first"), [("a-v1.0.0", ""), ("b-v1.0.0", " --first-release")]
)
def test_independent_bump_drops_first_release_once_the_project_is_tagged(
    independent_run: Run, independent_repo: Path, tmp_path: Path, tag: str, first: str
) -> None:
    git(independent_repo, "tag", tag)
    done = independent_run("version", "--", "minor", "a")
    assert done.returncode == 0, done.stdout + done.stderr
    assert _calls(tmp_path)[1] == INDEPENDENT_CHANGELOG + first


def test_independent_bump_needs_a_project(independent_run: Run, tmp_path: Path) -> None:
    done = independent_run("version", "--", "minor")
    assert done.returncode != 0
    assert "pass a bump and a project" in done.stdout + done.stderr
    assert _calls(tmp_path) == []


def test_independent_bump_refuses_an_unknown_project(independent_run: Run) -> None:
    done = independent_run("version", "--", "minor", "zzz")
    assert done.returncode != 0
    assert "zzz is not a publishable project" in done.stdout + done.stderr


def _tag_all(repo: Path, *tags: str) -> None:
    for tag in tags:
        git(repo, "tag", tag)


def test_independent_state_lists_every_new_project(
    independent_run: Run, tmp_path: Path
) -> None:
    done = independent_run("ci:release:state")
    assert done.returncode == 0, done.stdout + done.stderr
    assert _outputs(tmp_path) == {
        "tags": "a-v1.2.3 b-v2.0.0",
        "new": "a-v1.2.3 b-v2.0.0",
        "tag": "a-v1.2.3",
    }
    assert "::notice::a: new (a-v1.2.3, npm tag latest)" in done.stdout + done.stderr


def test_independent_state_orders_dependencies_first(
    independent_run: Run, independent_repo: Path, tmp_path: Path
) -> None:
    (independent_repo / "libs" / "a" / "package.json").write_text(
        json.dumps({"name": "a", "version": "1.2.3", "dependencies": {"b": "^2"}}),
        encoding="utf-8",
    )
    done = independent_run("ci:release:state")
    assert done.returncode == 0, done.stdout + done.stderr
    assert _outputs(tmp_path)["tags"] == "b-v2.0.0 a-v1.2.3"
    assert _outputs(tmp_path)["tag"] == "b-v2.0.0"


def test_independent_state_refuses_a_dependency_cycle(
    independent_run: Run, independent_repo: Path
) -> None:
    for name, other in (("a", "b"), ("b", "a")):
        (independent_repo / "libs" / name / "package.json").write_text(
            json.dumps(
                {"name": name, "version": "1.0.0", "peerDependencies": {other: "*"}}
            ),
            encoding="utf-8",
        )
    done = independent_run("ci:release:state")
    assert done.returncode != 0
    assert "dependency cycle among publishable projects" in done.stdout + done.stderr


def test_independent_state_skips_released_projects(
    independent_run: Run, independent_repo: Path, tmp_path: Path
) -> None:
    _tag_all(independent_repo, "a-v1.2.3")
    done = independent_run("ci:release:state", view="published")
    assert done.returncode == 0, done.stdout + done.stderr
    # `b` has no tag, so the same fake answer cannot make it released.
    assert _outputs(tmp_path) == {
        "tags": "b-v2.0.0",
        "new": "b-v2.0.0",
        "tag": "b-v2.0.0",
    }


def test_independent_state_resumes_a_draft(
    independent_run: Run, independent_repo: Path, tmp_path: Path
) -> None:
    _tag_all(independent_repo, "a-v1.2.3")
    done = independent_run("ci:release:state", view="draft")
    assert done.returncode == 0, done.stdout + done.stderr
    outputs = _outputs(tmp_path)
    assert outputs["tags"] == "a-v1.2.3 b-v2.0.0"
    assert outputs["new"] == "b-v2.0.0"


def test_independent_state_refuses_a_tag_not_at_head(
    independent_run: Run, independent_repo: Path
) -> None:
    _tag_all(independent_repo, "a-v1.2.3")
    git(independent_repo, "commit", "-q", "--allow-empty", "-m", "later")
    done = independent_run("ci:release:state", view="draft")
    assert done.returncode != 0
    assert "is not at HEAD" in done.stdout + done.stderr


def test_independent_state_with_nothing_to_release(
    independent_run: Run, independent_repo: Path, tmp_path: Path
) -> None:
    _tag_all(independent_repo, "a-v1.2.3", "b-v2.0.0")
    done = independent_run("ci:release:state", view="published")
    assert done.returncode == 0, done.stdout + done.stderr
    assert _outputs(tmp_path) == {"tags": "", "new": "", "tag": ""}


def test_independent_state_with_no_publishable_project(
    independent_run: Run, independent_repo: Path, tmp_path: Path
) -> None:
    for name in ("a", "b"):
        shutil.rmtree(independent_repo / "libs" / name)
    done = independent_run("ci:release:state")
    assert done.returncode == 0, done.stdout + done.stderr
    assert _outputs(tmp_path) == {"tags": "", "new": "", "tag": ""}


def test_independent_tag_and_push_handle_every_new_tag(
    independent_run: Run, independent_repo: Path
) -> None:
    env = {"NEW_TAGS": "a-v1.2.3 b-v2.0.0"}
    assert independent_run("ci:release:tag", env=env).returncode == 0
    head = git(independent_repo, "rev-parse", "HEAD")
    for tag in ("a-v1.2.3", "b-v2.0.0"):
        assert git(independent_repo, "rev-parse", f"{tag}^{{commit}}") == head
    done = independent_run("ci:release:push", env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    remote = git(independent_repo, "ls-remote", "origin")
    assert "refs/tags/a-v1.2.3" in remote
    assert "refs/tags/b-v2.0.0" in remote
    assert git(independent_repo, "ls-remote", "--heads", "origin") == ""


def _tarballs(repo: Path, *names: str) -> None:
    (repo / "dist" / "tarballs").mkdir(parents=True, exist_ok=True)
    for name in names:
        (repo / "dist" / "tarballs" / name).write_text("")


def test_independent_github_release_carries_only_its_tarball(
    independent_run: Run, independent_repo: Path, tmp_path: Path
) -> None:
    _tarballs(independent_repo, "a-1.2.3.tgz", "b-2.0.0.tgz")
    done = independent_run("ci:release:github", env={"TAGS": "a-v1.2.3"})
    assert done.returncode == 0, done.stdout + done.stderr
    calls = _calls(tmp_path)
    creates = [c for c in calls if c.startswith("gh release create")]
    assert len(creates) == 1
    assert creates[0].startswith(
        "gh release create a-v1.2.3 dist/tarballs/a-1.2.3.tgz --verify-tag "
    )
    assert creates[0].endswith(" --draft")
    notes = [c for c in calls if c.startswith("uvx ")]
    assert len(notes) == 1
    assert notes[0].endswith(" notes libs/a/CHANGELOG.md 1.2.3")


def test_independent_github_release_names_a_scoped_tarball(
    independent_run: Run, independent_repo: Path, tmp_path: Path
) -> None:
    (independent_repo / "libs" / "a" / "package.json").write_text(
        json.dumps({"name": "@s/a", "version": "1.2.3"}), encoding="utf-8"
    )
    _tarballs(independent_repo, "s-a-1.2.3.tgz")
    done = independent_run("ci:release:github", env={"TAGS": "a-v1.2.3"})
    assert done.returncode == 0, done.stdout + done.stderr
    creates = [c for c in _calls(tmp_path) if c.startswith("gh release create")]
    assert creates[0].startswith(
        "gh release create a-v1.2.3 dist/tarballs/s-a-1.2.3.tgz "
    )


def test_independent_github_release_fails_without_its_tarball(
    independent_run: Run, independent_repo: Path
) -> None:
    _tarballs(independent_repo, "b-2.0.0.tgz")
    done = independent_run("ci:release:github", env={"TAGS": "a-v1.2.3"})
    assert done.returncode != 0
    assert "dist/tarballs/a-1.2.3.tgz" in done.stdout + done.stderr


def test_independent_publish_runs_per_project(
    independent_run: Run, independent_repo: Path, tmp_path: Path
) -> None:
    env = {"TAGS": "a-v1.2.3 b-v2.0.0"}
    done = independent_run("ci:release:publish", env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    stem = "pnpm exec nx release publish --projects={} --tag=latest --excludeTaskDependencies"
    assert _calls(tmp_path) == [
        stem.format("a") + " --first-release",
        stem.format("b") + " --first-release",
    ]
    (tmp_path / "calls.log").unlink()
    _tag_all(independent_repo, "a-v1.0.0")
    assert independent_run("ci:release:publish", env=env).returncode == 0
    assert _calls(tmp_path) == [stem.format("a"), stem.format("b") + " --first-release"]


def test_independent_finalize_publishes_each_draft(
    independent_run: Run, tmp_path: Path
) -> None:
    done = independent_run("ci:release:finalize", env={"TAGS": "a-v1.2.3 b-v2.0.0"})
    assert done.returncode == 0, done.stdout + done.stderr
    assert _calls(tmp_path) == [
        "gh release edit a-v1.2.3 --draft=false",
        "gh release edit b-v2.0.0 --draft=false",
    ]


def test_independent_cell_has_no_latest_task(
    cell: Path, independent_cell: Path
) -> None:
    assert "release:latest" in _tasks(cell)
    assert "release:latest" not in _tasks(independent_cell)
