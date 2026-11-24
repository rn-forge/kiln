"""`task-layout` reads only the repository's own includes and the config."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import run_check

from rn_forge.kiln.modules.tasks.checks import layout

OWNED = "version: '3'\ntasks:\n  go:\n    desc: Go\n    cmds: [echo hi]\n"


def codes(root: Path) -> list[str]:
    return [f.code for f in run_check(layout.NAME, root)]


def declare(root: Path, extra_refs: str = "") -> None:
    """Declare a repository-owned include `own` in `config.toml`."""
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + '\n[tasks]\nincludes = [{ namespace = "own", taskfile = "tasks/own.yml" }]\n'
        + extra_refs,
        encoding="utf-8",
    )


def test_no_includes_means_no_findings_and_no_file_is_read(repo) -> None:
    assert codes(repo()) == []


def test_an_include_must_exist(repo) -> None:
    root = repo()
    declare(root)
    [finding] = run_check(layout.NAME, root)
    assert finding.code == "taskgraph.missing-include"
    assert "tasks/own.yml" in finding.message


def test_an_owned_include_that_exists_passes(repo) -> None:
    root = repo(**{"tasks__own.yml": OWNED})
    declare(root, '[tasks.extra_refs]\nvalidate = ["own:go"]\n')
    assert codes(root) == []


def test_an_extra_ref_into_an_owned_include_must_name_a_task(repo) -> None:
    root = repo(**{"tasks__own.yml": OWNED})
    declare(root, '[tasks.extra_refs]\nvalidate = ["own:nope"]\n')
    [finding] = run_check(layout.NAME, root)
    assert finding.code == "taskgraph.unresolved"
    assert "own:nope" in finding.message
    assert finding.path == "tasks/own.yml"


def test_a_cycle_through_an_owned_include_is_reported(repo) -> None:
    owned = (
        "version: '3'\ntasks:\n  go:\n    desc: Go\n    cmds:\n      - task: :test\n"
    )
    root = repo(**{"tasks__own.yml": owned})
    declare(root, '[tasks.extra_refs]\ntest = ["own:go"]\n')
    [finding] = run_check(layout.NAME, root)
    assert finding.code == "taskgraph.cycle"
    assert "own:go -> test -> own:go" in finding.message or (
        "test -> own:go -> test" in finding.message
    )
