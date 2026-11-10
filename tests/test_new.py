"""S4.5.1 — `kiln new`: creation.

The end-to-end tests that run `uv init` through the python scaffold are slow;
`tests/modules/python/test_scaffold.py` — the nearest `done` story's tests —
marks none of its own `uv init` tests either, so none are marked here.
"""

from __future__ import annotations

import inspect
import json
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import archetypes, checks, commands
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.checks import derived
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.core.artifacts import GITIGNORE_BLOCK
from rn_forge.kiln.modules.registry import builtin


@pytest.fixture(autouse=True)
def _in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`kiln new` stages beneath the current directory; keep that out of the repo."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


def _last_json(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    out = capsys.readouterr().out.strip().splitlines()
    return json.loads(out[-1])


def test_s4_5_1_flags_match_module_union() -> None:
    """`new`'s config-setting flags are exactly backed by a registered module's `Option`.

    `framework`/`frontend` join both the signature and this set once F5.1/F5.2
    register a module that declares them — see commands.py's `_FLAG_NAMES`
    comment.
    """
    union = {option.flag for module in builtin().modules for option in module.options()}
    assert set(commands._FLAG_NAMES) == union


def test_s4_5_1_preview_without_yes_writes_nothing(tmp_path: Path) -> None:
    directory = tmp_path / "preview"
    commands.new(directory, archetype="python-app", docs="none")
    assert not (directory / ".rn-forge").exists()


def test_s4_5_1_preview_json_lists_artifacts_without_writing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = tmp_path / "preview"
    commands.new(directory, archetype="python-app", docs="none", json=True)
    payload = _last_json(capsys)
    assert payload["root"] == str(directory.resolve())
    assert len(payload["artifacts"]) > 0
    assert all(
        row["action"] in ("create", "insert", "skip") for row in payload["artifacts"]
    )
    assert not (directory / ".rn-forge").exists()


def test_s4_5_1_nonempty_directory_is_refused_and_writes_nothing(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "full"
    directory.mkdir()
    (directory / "x").write_text("x", encoding="utf-8")

    with pytest.raises(AppException, match=str(directory)):
        commands.new(directory, archetype="python-app", docs="none", yes=True)
    assert not (directory / ".rn-forge").exists()


def test_s4_5_1_untested_flag_value_is_refused_without_allow_untested() -> None:
    manifest = archetypes.Archetype.parse(
        tomllib.loads(
            """
            name = "python-app"
            modules = ["core"]
            forbidden_tools = []
            required_validate = []

            [dependencies]
            required = []
            allowed = []

            [untested]
            docs = ["external"]
            """
        ),
        source="fixture",
    )

    with pytest.raises(AppException, match="--docs"):
        commands._flag_layer(
            archetype="python-app",
            docs="external",
            manifest=manifest,
            allow_untested=False,
        )

    flags = commands._flag_layer(
        archetype="python-app", docs="external", manifest=manifest, allow_untested=True
    )
    assert flags["docs"]["profile"] == "external"


@pytest.mark.parametrize("value", [None, ""])
def test_s4_5_1_missing_archetype_is_refused(tmp_path: Path, value: str | None) -> None:
    kwargs: dict[str, Any] = {"docs": "none"}
    if value is not None:
        kwargs["archetype"] = value
    with pytest.raises(AppException, match="--archetype"):
        commands.new(tmp_path / "repo", **kwargs)


def test_s5_1_1_4_backend_is_rejected_for_a_non_web_archetype(tmp_path: Path) -> None:
    directory = tmp_path / "repo"
    with pytest.raises(AppException, match="backend"):
        commands.new(directory, archetype="python-app", docs="none", backend="fastapi")
    assert not directory.exists() or not any(directory.iterdir())


def test_s5_1_1_4_frontend_is_rejected_for_python_web_api(tmp_path: Path) -> None:
    directory = tmp_path / "repo"
    with pytest.raises(AppException, match="frontend"):
        commands.new(
            directory,
            archetype="python-web-api",
            docs="none",
            backend="fastapi",
            frontend="angular",
            allow_untested=True,
        )
    assert not directory.exists() or not any(directory.iterdir())


def test_s5_1_1_4_frontend_is_rejected_for_a_non_web_archetype(tmp_path: Path) -> None:
    directory = tmp_path / "repo"
    with pytest.raises(AppException, match="frontend"):
        commands.new(directory, archetype="python-app", docs="none", frontend="angular")
    assert not directory.exists() or not any(directory.iterdir())


def test_s5_1_1_5_an_unsupported_backend_is_rejected_before_writing(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "repo"
    with pytest.raises(AppException, match="backend"):
        commands.new(
            directory,
            archetype="python-web-api",
            docs="none",
            backend="spring-boot",
            allow_untested=True,
        )
    assert not directory.exists() or not any(directory.iterdir())


@pytest.mark.parametrize("archetype", ["python-web-api", "python-web-app"])
def test_s5_3_1_web_defaults_select_fastapi(archetype: str) -> None:
    manifest = archetypes.load(archetype)
    flags = commands._flag_layer(
        archetype=archetype,
        docs="none",
        manifest=manifest,
        allow_untested=False,
    )
    flags["repository"]["name"] = "demo"
    flags["repository"]["owner"] = "rn-forge"
    resolved = commands.ConfigManager().resolve(flags=flags).config
    assert resolved.backend == "fastapi"
    assert resolved.frontend == ("angular" if archetype == "python-web-app" else None)


@pytest.mark.parametrize(
    ("archetype", "selector", "value"),
    [
        ("python-web-api", "backend", "django"),
        ("python-web-app", "frontend", "svelte"),
    ],
)
def test_s5_3_1_explicit_selectors_override_web_defaults(
    archetype: str, selector: str, value: str
) -> None:
    manifest = archetypes.load(archetype)
    flags = commands._flag_layer(
        archetype=archetype,
        docs="none",
        manifest=manifest,
        allow_untested=True,
        **{selector: value},
    )
    flags["repository"]["name"] = "demo"
    flags["repository"]["owner"] = "rn-forge"
    resolved = commands.ConfigManager().resolve(flags=flags).config
    assert getattr(resolved, selector) == value


@pytest.mark.parametrize("archetype", ["python-web-api", "python-web-app"])
def test_s5_3_1_django_remains_untested_for_both_web_archetypes(archetype: str) -> None:
    manifest = archetypes.load(archetype)
    with pytest.raises(AppException, match="django"):
        commands._flag_layer(
            archetype=archetype,
            docs="none",
            backend="django",
            manifest=manifest,
            allow_untested=False,
        )


def test_s4_5_1_yes_creates_and_passes_every_check(tmp_path: Path) -> None:
    """The slow path: `uv init` through the python scaffold, then a full apply."""
    directory = tmp_path / "demo"
    commands.new(directory, archetype="python-tool", docs="none", yes=True)

    assert (directory / ".rn-forge" / "kiln" / "config.toml").is_file()
    assert (directory / "pyproject.toml").is_file()
    assert checks.run(directory) == []


def test_s4_5_1_yes_json_artifacts_actions_only_create_insert_or_skip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = tmp_path / "demo-json"
    commands.new(directory, archetype="python-tool", docs="none", yes=True, json=True)
    payload = _last_json(capsys)
    assert payload["root"] == str(directory.resolve())
    assert len(payload["artifacts"]) > 0
    assert all(
        row["action"] in ("create", "insert", "skip") for row in payload["artifacts"]
    )


def test_s4_5_1_config_layer_merges_beneath_flags_and_records_source(
    tmp_path: Path,
) -> None:
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "config.toml").write_text("[ci]\nsonar = false\n", encoding="utf-8")

    directory = tmp_path / "demo-layered"
    commands.new(
        directory,
        archetype="python-tool",
        docs="none",
        config=str(layer_dir),
        yes=True,
    )

    written = tomllib.loads(
        (directory / ".rn-forge" / "kiln" / "config.toml").read_text(encoding="utf-8")
    )
    assert written["ci"]["sonar"] is False
    assert written["source"]["location"] == str(layer_dir)


def test_s7_4_1_5_new_pins_kiln(tmp_path: Path) -> None:
    directory = tmp_path / "demo-pinned"
    commands.new(directory, archetype="python-tool", docs="none", yes=True)
    written = tomllib.loads(
        (directory / ".rn-forge" / "kiln" / "config.toml").read_text(encoding="utf-8")
    )
    assert written["kiln"] == {"ref": archetypes.KILN_REF}


def test_s7_4_1_6_a_config_layer_pin_wins(tmp_path: Path) -> None:
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "config.toml").write_text('[kiln]\nref = "v1.2.3"\n', encoding="utf-8")
    directory = tmp_path / "demo-layer-pin"
    commands.new(
        directory,
        archetype="python-tool",
        docs="none",
        config=str(layer_dir),
        yes=True,
    )
    written = tomllib.loads(
        (directory / ".rn-forge" / "kiln" / "config.toml").read_text(encoding="utf-8")
    )
    assert written["kiln"]["ref"] == "v1.2.3"


def test_s6_1_16_3_new_takes_the_name_from_config(tmp_path: Path) -> None:
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "config.toml").write_text(
        '[repository]\nname = "repo-name"\n', encoding="utf-8"
    )

    directory = tmp_path / "dir-name"
    commands.new(
        directory,
        archetype="python-tool",
        docs="none",
        config=str(layer_dir),
        yes=True,
    )

    written = tomllib.loads(
        (directory / ".rn-forge" / "kiln" / "config.toml").read_text(encoding="utf-8")
    )
    assert written["repository"]["name"] == "repo-name"


def _bare_layer_repo(tmp_path: Path, layer: str) -> tuple[str, str]:
    """A bare repo whose `main` holds *layer* as `config.toml`; (git+ URL, commit)."""
    work = tmp_path / "layer-work"
    work.mkdir()
    (work / "config.toml").write_text(layer, encoding="utf-8")
    git = ["git", "-c", "user.name=kiln", "-c", "user.email=kiln@example.com"]
    subprocess.run([*git, "init", "--quiet", "-b", "main", str(work)], check=True)
    subprocess.run([*git, "-C", str(work), "add", "."], check=True)
    subprocess.run([*git, "-C", str(work), "commit", "--quiet", "-m", "l"], check=True)
    sha = subprocess.run(
        ["git", "-C", str(work), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    bare = tmp_path / "layer.git"
    subprocess.run(
        ["git", "clone", "--quiet", "--bare", str(work), str(bare)], check=True
    )
    return f"git+file://{bare}", sha


def test_s4_5_7_1_git_config_merges_beneath_flags_and_records_source(
    tmp_path: Path,
) -> None:
    location, sha = _bare_layer_repo(
        tmp_path, '[ci]\nsonar = false\n\n[docs]\nprofile = "mkdocs"\n'
    )

    directory = tmp_path / "demo-git"
    commands.new(
        directory,
        archetype="python-tool",
        docs="none",
        config=f"{location}@main",
        yes=True,
    )

    written = tomllib.loads(
        (directory / ".rn-forge" / "kiln" / "config.toml").read_text(encoding="utf-8")
    )
    assert written["ci"]["sonar"] is False  # from the layer, no flag sets it
    assert written["docs"]["profile"] == "none"  # the flag wins over the layer
    assert written["source"]["location"] == location
    assert written["source"]["ref"] == "main"
    assert written["source"]["commit"] == sha
    assert len(sha) == 40


def test_s4_5_7_2_unreachable_url_and_missing_ref_name_the_url(
    tmp_path: Path,
) -> None:
    missing = f"git+file://{tmp_path / 'nope.git'}"
    with pytest.raises(AppException) as unreachable:
        commands.new(
            tmp_path / "a",
            archetype="python-tool",
            docs="none",
            config=f"{missing}@main",
        )
    assert missing in str(unreachable.value)

    location, _ = _bare_layer_repo(tmp_path, "[ci]\nsonar = false\n")
    with pytest.raises(AppException) as no_ref:
        commands.new(
            tmp_path / "b",
            archetype="python-tool",
            docs="none",
            config=f"{location}@nope",
        )
    assert location in str(no_ref.value)
    assert not (tmp_path / "a").exists()
    assert not (tmp_path / "b").exists()


def _hashes(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


def test_s4_5_9_1_success_retains_staging_and_target_equals_workspace(
    tmp_path: Path,
) -> None:
    target = tmp_path / "out" / "demo"
    commands.new(target, archetype="python-tool", docs="none", yes=True)

    run = tmp_path / ".staging" / "demo"
    assert all((run / part).is_dir() for part in ("backend", "frontend", "workspace"))
    assert (run / "backend" / "pyproject.toml").is_file()
    assert _hashes(run / "workspace") == _hashes(target)
    assert (tmp_path / ".staging" / ".gitignore").read_text(encoding="utf-8") == "/*\n"


def test_s4_5_9_2_workspace_holds_only_reconciled_files(tmp_path: Path) -> None:
    commands.new(tmp_path / "demo", archetype="python-tool", docs="none", yes=True)

    run = tmp_path / ".staging" / "demo"
    raw = (run / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    assembled = (run / "workspace" / "pyproject.toml").read_text(encoding="utf-8")
    assert raw != assembled
    assert "[tool.pyright]" in assembled
    assert "[tool.pyright]" not in raw
    assert not (run / "backend" / ".rn-forge").exists()
    assert not (run / "backend" / "README.md").exists()


def test_s4_5_9_3_staging_is_ignored_inside_a_git_worktree(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    commands.new(tmp_path / "demo", archetype="python-tool", docs="none", yes=True)

    check = subprocess.run(
        ["git", "check-ignore", ".staging/demo/workspace"], cwd=tmp_path, check=False
    )
    assert check.returncode == 0
    assert not (tmp_path / ".gitignore").exists()


@pytest.mark.parametrize("target_exists", [False, True])
def test_s4_5_9_4_failure_retains_staging_and_writes_no_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target_exists: bool
) -> None:
    def boom(*_args: object) -> None:
        raise AppException("boom")

    monkeypatch.setattr(commands, "instructions_scaffold", boom)
    target = tmp_path / "demo"
    if target_exists:
        target.mkdir()

    with pytest.raises(AppException, match="boom"):
        commands.new(target, archetype="python-tool", docs="none", yes=True)

    assert (tmp_path / ".staging" / "demo" / "backend" / "pyproject.toml").is_file()
    assert target.exists() is target_exists
    assert not target_exists or list(target.iterdir()) == []


def test_s4_5_9_5_existing_staging_is_refused_untouched(tmp_path: Path) -> None:
    run = tmp_path / ".staging" / "demo"
    run.mkdir(parents=True)
    (run / "keep").write_text("review state", encoding="utf-8")

    with pytest.raises(AppException, match="already exists"):
        commands.new(tmp_path / "demo", archetype="python-tool", docs="none", yes=True)

    assert [p.name for p in run.iterdir()] == ["keep"]
    assert not (tmp_path / "demo").exists()


def test_s4_5_11_1_success_leaves_a_git_repository_without_commits(
    tmp_path: Path,
) -> None:
    target = tmp_path / "demo"
    commands.new(target, archetype="python-tool", docs="none", yes=True)

    top = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert Path(top).resolve() == target.resolve()
    head = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        check=False,
    )
    assert head.returncode != 0
    remotes = subprocess.run(
        ["git", "-C", str(target), "remote"], capture_output=True, text=True
    )
    assert remotes.stdout == ""


def test_s4_5_11_2_dry_run_writes_no_git(tmp_path: Path) -> None:
    target = tmp_path / "preview"
    commands.new(target, archetype="python-tool", docs="none", yes=True, dry_run=True)
    assert not target.exists()


def test_s4_5_11_3_failure_or_refusal_creates_no_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    full = tmp_path / "full"
    full.mkdir()
    (full / "x").write_text("x", encoding="utf-8")
    with pytest.raises(AppException):
        commands.new(full, archetype="python-tool", docs="none", yes=True)
    assert not (full / ".git").exists()

    def boom(*_args: object) -> None:
        raise AppException("boom")

    monkeypatch.setattr(commands, "instructions_scaffold", boom)
    failed = tmp_path / "failed"
    with pytest.raises(AppException, match="boom"):
        commands.new(failed, archetype="python-tool", docs="none", yes=True)
    assert not (failed / ".git").exists()


def test_s4_5_11_4_json_plan_does_not_list_git(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commands.new(
        tmp_path / "demo", archetype="python-tool", docs="none", yes=True, json=True
    )
    payload = _last_json(capsys)
    assert not any(".git" in str(row).split("/") for row in payload["artifacts"])


@pytest.mark.parametrize("archetype", ["python-lib", "python-app"])
def test_s4_5_11_5_other_archetypes_get_git(tmp_path: Path, archetype: str) -> None:
    commands.new(tmp_path / "demo", archetype=archetype, docs="none", yes=True)
    assert (tmp_path / "demo" / ".git").is_dir()


def test_s4_5_9_6_no_retention_or_cleanup_flag_and_no_rnf_home() -> None:
    assert set(inspect.signature(commands.new).parameters) == {
        "directory",
        "archetype",
        "docs",
        "backend",
        "frontend",
        "module",
        "config",
        "owner",
        "allow_untested",
        "dry_run",
        "yes",
        "json",
    }
    assert "RNF_HOME" not in inspect.getsource(commands._stage)


UV_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "scaffold" / "uv" / ".gitignore"
)


def test_s5_3_6_1_fresh_scaffolds_have_identical_composed_gitignores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    texts = []
    for run in ("first", "second"):
        cwd = tmp_path / run
        cwd.mkdir()
        monkeypatch.chdir(cwd)
        target = cwd / "demo"
        commands.new(target, archetype="python-web-api", docs="none", yes=True)
        assert (target / ".git").is_dir()
        texts.append((target / ".gitignore").read_bytes())

    assert texts[0] == texts[1]
    text = texts[0].decode("utf-8")
    kiln = GITIGNORE_BLOCK.extract(text)
    assert kiln is not None
    assert text == GITIGNORE_BLOCK.render(
        "## uv ##\n" + UV_FIXTURE.read_text(encoding="utf-8"), kiln
    )


def test_s5_3_6_5_new_seeds_the_workspace_file(tmp_path: Path) -> None:
    target = tmp_path / "demo"
    commands.new(target, archetype="python-tool", docs="none", yes=True)
    workspace = json.loads((target / "demo.code-workspace").read_text("utf-8"))
    assert workspace == {"folders": [{"path": "."}]}


def test_s5_3_6_7_docs_none_omits_the_mkdocs_tree_and_site_tasks(
    tmp_path: Path,
) -> None:
    target = tmp_path / "demo"
    commands.new(target, archetype="python-tool", docs="none", yes=True)

    assert not (target / "docs").exists()
    assert not (target / "mkdocs.yml").exists()
    assert not (target / "tasks" / "docs.yml").exists()
    listed = subprocess.run(
        ["task", "--list-all", "--json"],
        cwd=target,
        capture_output=True,
        text=True,
        check=True,
    )
    names = [task["name"] for task in json.loads(listed.stdout)["tasks"]]
    assert "format" in names
    assert [name for name in names if name.startswith("docs:")] == []
    assert "mdformat" in (target / "tasks" / "quality.yml").read_text("utf-8")
    assert (target / "README.md").is_file()
    assert (target / "CLAUDE.md").is_file()
    assert (target / ".mdformat.toml").is_file()


def test_s13_1_1_4_new_writes_a_current_derived_nav(tmp_path: Path) -> None:
    target = tmp_path / "demo"
    commands.new(target, archetype="python-tool", docs="mkdocs", yes=True)

    assert derived.check(KilnConfig.load(target), target) == []
    nav = (target / "mkdocs.yml").read_text(encoding="utf-8")
    assert "# BEGIN derived nav" in nav
    assert "guides/index.md" in nav
    state = (target / ".rn-forge" / "kiln" / "state.json").read_text("utf-8")
    assert '"mkdocs.yml"' in state


def test_s14_1_1_2_new_writes_tabbed_navigation_features(tmp_path: Path) -> None:
    target = tmp_path / "demo"
    commands.new(target, archetype="python-tool", docs="mkdocs", yes=True)

    mkdocs = (target / "mkdocs.yml").read_text(encoding="utf-8")
    assert "navigation.tabs" in mkdocs
    assert "navigation.indexes" in mkdocs
    assert "navigation.sections" not in mkdocs
    assert "Overview:" not in mkdocs


def test_s14_1_2_5_new_writes_a_current_epic_list(tmp_path: Path) -> None:
    target = tmp_path / "demo"
    commands.new(target, archetype="python-tool", docs="mkdocs", yes=True)

    page = target / "docs" / "specs" / "epics" / "index.md"
    assert "No epics yet." in page.read_text(encoding="utf-8")
    assert derived.check(KilnConfig.load(target), target) == []


def test_new_inside_a_uv_project_leaves_it_untouched(tmp_path: Path) -> None:
    parent = tmp_path / "pyproject.toml"
    parent.write_text('[project]\nname = "host"\nversion = "0.1.0"\n', encoding="utf-8")

    commands.new(
        tmp_path / "out" / "demo", archetype="python-tool", docs="none", yes=True
    )

    assert parent.read_text(encoding="utf-8") == (
        '[project]\nname = "host"\nversion = "0.1.0"\n'
    )


def _lib_layer(tmp_path: Path, body: str) -> str:
    layer = tmp_path / "layer"
    layer.mkdir(exist_ok=True)
    (layer / "config.toml").write_text(body, encoding="utf-8")
    return str(layer)


TWO_PACKAGES = (
    '[archetype.python-lib]\npackages = ["packages/alpha", "packages/beta"]\n'
)
MODULES = '\n[archetype.python-lib.modules]\n"packages/beta" = "rn_forge.beta"\n'


def _new_lib(directory: Path, layer: str, **kwargs: Any) -> None:
    commands.new(
        directory,
        archetype="python-lib",
        docs="mkdocs",
        config=layer,
        owner="rn-forge",
        yes=True,
        **kwargs,
    )


def test_s16_7_10_1_new_with_two_packages_makes_both_members(tmp_path: Path) -> None:
    target = tmp_path / "lib"
    _new_lib(target, _lib_layer(tmp_path, TWO_PACKAGES))

    for name in ("alpha", "beta"):
        member = target / "packages" / name
        assert (member / "pyproject.toml").is_file()
        for seeded in ("mkdocs.yml", "CHANGELOG.md", "README.md"):
            assert (member / seeded).is_file()
        assert (member / "docs").is_dir()
    members = tomllib.loads((target / "pyproject.toml").read_text(encoding="utf-8"))[
        "tool"
    ]["uv"]["workspace"]["members"]
    assert members == ["packages/alpha", "packages/beta"]
    assert KilnConfig.load(target).packages == ("packages/alpha", "packages/beta")


def test_s16_7_10_2_modules_come_from_the_config(tmp_path: Path) -> None:
    target = tmp_path / "lib"
    _new_lib(target, _lib_layer(tmp_path, TWO_PACKAGES + MODULES))

    assert (target / "packages/alpha/src/alpha").is_dir()
    assert (target / "packages/beta/src/rn_forge/beta").is_dir()
    config = tomllib.loads(
        (target / ".rn-forge/kiln/config.toml").read_text(encoding="utf-8")
    )
    assert config["archetype"]["python-lib"]["modules"] == {
        "packages/beta": "rn_forge.beta"
    }


def test_s16_7_10_3_same_result_as_generate_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layer = _lib_layer(tmp_path, TWO_PACKAGES + MODULES)
    listed = tmp_path / "a" / "lib"
    _new_lib(listed, layer)
    stepwise = tmp_path / "b" / "lib"
    stepwise.parent.mkdir()
    monkeypatch.chdir(stepwise.parent)
    commands.new(
        stepwise, archetype="python-lib", docs="mkdocs", owner="rn-forge", yes=True
    )
    commands.generate_package("alpha", path=stepwise)
    commands.generate_package("beta", path=stepwise, module="rn_forge.beta")

    def settled(root: Path) -> dict[str, Any]:
        """The committed config without `[source]` (the layer's location) and the
        default `import_contracts` a layer's table writes out."""
        document = tomllib.loads(
            (root / ".rn-forge/kiln/config.toml").read_text(encoding="utf-8")
        )
        document.pop("source", None)
        document["archetype"]["python-lib"].pop("import_contracts", None)
        return document

    assert settled(listed) == settled(stepwise)
    for name in (
        "pyproject.toml",
        "packages/alpha/pyproject.toml",
        "packages/beta/pyproject.toml",
        "mkdocs.yml",
    ):
        assert (listed / name).read_bytes() == (stepwise / name).read_bytes(), name


def test_s16_7_10_4_a_failing_second_package_leaves_no_directory(
    tmp_path: Path,
) -> None:
    layer = _lib_layer(
        tmp_path,
        '[archetype.python-lib]\npackages = ["packages/alpha", "packages/Bad_Name"]\n',
    )
    target = tmp_path / "lib"

    with pytest.raises(AppException, match="generate.invalid-name"):
        _new_lib(target, layer)

    assert not target.exists()
    assert (tmp_path / ".staging" / "lib" / "workspace" / "packages" / "alpha").is_dir()


def test_s16_7_10_5_a_failing_member_step_leaves_no_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = commands.python_add_package
    calls: list[str] = []

    def flaky(*args: Any, **kwargs: Any) -> None:
        calls.append("call")
        if len(calls) == 2:
            raise AppException("boom")
        real(*args, **kwargs)

    monkeypatch.setattr(commands, "python_add_package", flaky)
    target = tmp_path / "lib"

    with pytest.raises(AppException, match="boom"):
        _new_lib(target, _lib_layer(tmp_path, TWO_PACKAGES))

    assert not target.exists()


def test_s16_7_10_6_new_with_no_packages_is_unchanged(tmp_path: Path) -> None:
    bare = tmp_path / "bare"
    commands.new(
        bare, archetype="python-lib", docs="mkdocs", owner="rn-forge", yes=True
    )
    assert not (bare / "packages").exists()

    layer = _lib_layer(
        tmp_path,
        '[archetype.python-lib]\npackages = ["packages/alpha", "packages/alpha"]\n',
    )
    target = tmp_path / "dup"
    with pytest.raises(AppException, match="generate.package-exists"):
        _new_lib(target, layer)
    assert not target.exists()


def test_s16_7_10_7_preview_with_packages_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    layer = _lib_layer(tmp_path, TWO_PACKAGES)
    target = tmp_path / "lib"
    for yes, dry_run in ((False, False), (True, True)):
        commands.new(
            target,
            archetype="python-lib",
            docs="mkdocs",
            config=layer,
            owner="rn-forge",
            yes=yes,
            dry_run=dry_run,
        )
        assert capsys.readouterr().out
        assert not target.exists()
        assert not (tmp_path / ".staging").exists()


def test_s11_2_2_4_new_python_lib_writes_no_member_and_passes_every_check(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "lib"
    commands.new(directory, archetype="python-lib", docs="mkdocs", yes=True)

    assert not list((directory / "packages").glob("*"))
    document = tomllib.loads((directory / "pyproject.toml").read_text(encoding="utf-8"))
    assert document["tool"]["uv"]["workspace"]["members"] == []
    assert not (directory / "docs" / "reference").exists()
    assert checks.run(directory) == []


STARTER = {
    "src/{package}/main.py",
    "src/{package}/commands.py",
    "src/{package}/product.py",
    "tests/test_cli.py",
    "tests/test_product.py",
}


@pytest.mark.parametrize("archetype", ["python-tool", "python-app"])
def test_s4_9_1_5_new_wires_cli_and_script(tmp_path: Path, archetype: str) -> None:
    directory = tmp_path / "demo-tool"
    commands.new(directory, archetype=archetype, docs="none", yes=True)

    written = tomllib.loads(
        (directory / ".rn-forge" / "kiln" / "config.toml").read_text(encoding="utf-8")
    )
    cli = written["cli"]
    assert cli["name"] == "demo-tool"
    assert cli["commands"] == [{"name": "hello", "target": "demo_tool.commands:hello"}]
    if archetype == "python-tool":
        assert written["lifecycle"] == {"product": "demo_tool.product:PRODUCT"}
    else:
        assert "lifecycle" not in written
    pyproject = tomllib.loads((directory / "pyproject.toml").read_text("utf-8"))
    assert pyproject["project"]["scripts"] == {"demo-tool": "demo_tool.main:app"}


def test_s4_9_1_6_new_records_seeded_and_validates(tmp_path: Path) -> None:
    """Slow like its neighbours: runs `uv init`; marks none, as the module note says."""
    directory = tmp_path / "demo-tool"
    commands.new(directory, archetype="python-tool", docs="none", yes=True)

    paths = {path.format(package="demo_tool") for path in STARTER}
    state_path = directory / ".rn-forge" / "kiln" / "state.json"

    def entries() -> dict[str, Any]:
        return json.loads(state_path.read_text(encoding="utf-8"))["entries"]

    recorded = entries()
    assert all(recorded[path]["kind"] == "seeded" for path in paths)
    assert not [
        path
        for path, entry in recorded.items()
        if path.startswith(("src/", "tests/"))
        and entry["kind"] != "seeded"
        and path not in {"src/demo_tool/__init__.py", "tests/test_package.py"}
    ]
    assert checks.run(directory) == []

    main = directory / "src" / "demo_tool" / "main.py"
    main.write_text("# edited\n", encoding="utf-8")
    before = {path: (directory / path).read_bytes() for path in paths}
    before_entries = {path: recorded[path] for path in paths}

    cycle.apply(directory, home=tmp_path / "home")

    assert {path: (directory / path).read_bytes() for path in paths} == before
    assert main.read_text(encoding="utf-8") == "# edited\n"
    assert {path: entries()[path] for path in paths} == before_entries


def test_s4_8_2_3_new_with_a_module(tmp_path: Path) -> None:
    directory = tmp_path / "demo-tool"
    commands.new(
        directory,
        archetype="python-tool",
        docs="mkdocs",
        module="rn_forge.demo",
        yes=True,
    )
    package = directory / "src/rn_forge/demo"
    for name in ("__init__.py", "py.typed", "main.py", "commands.py", "product.py"):
        assert (package / name).is_file()
    assert not (directory / "src/rn_forge/__init__.py").exists()
    assert not (directory / "src/demo_tool").exists()
    pyproject = tomllib.loads((directory / "pyproject.toml").read_text("utf-8"))
    assert pyproject["tool"]["uv"]["build-backend"]["module-name"] == "rn_forge.demo"
    assert pyproject["project"]["scripts"] == {"demo-tool": "rn_forge.demo.main:app"}

    def read(path: str) -> str:
        return (directory / path).read_text(encoding="utf-8")

    assert ".parents[3] / " in read("src/rn_forge/demo/main.py")
    assert "import rn_forge.demo\n" in read("tests/test_package.py")
    assert "from rn_forge.demo.main import app" in read("tests/test_cli.py")
    assert "--cov=rn_forge.demo " in read("tasks/python.yml")
    assert "::: rn_forge.demo" in read("docs/reference/python-api.md")
    written = tomllib.loads(read(".rn-forge/kiln/config.toml"))
    assert written["archetype"]["python-tool"]["module"] == "rn_forge.demo"
    assert written["cli"]["commands"][0]["target"] == "rn_forge.demo.commands:hello"
    assert written["lifecycle"]["product"] == "rn_forge.demo.product:PRODUCT"
    assert checks.run(directory) == []


def test_s4_8_2_3_new_without_a_module_is_unchanged(
    rendered: Callable[[str], Path],
) -> None:
    root = rendered("python-tool")
    written = tomllib.loads(
        (root / ".rn-forge/kiln/config.toml").read_text(encoding="utf-8")
    )
    assert "module" not in written.get("archetype", {}).get("python-tool", {})
    assert (root / "src/python_tool/py.typed").is_file()


def test_s4_8_2_3_an_invalid_module_is_refused_before_writing(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "demo-tool"
    with pytest.raises(AppException):
        commands.new(directory, archetype="python-tool", module="Rn-Forge", yes=True)
    assert not directory.exists()
    assert not (tmp_path / ".staging").exists()


def test_s4_8_2_3_module_on_another_archetype_is_refused(tmp_path: Path) -> None:
    directory = tmp_path / "demo-lib"
    with pytest.raises(AppException):
        commands.new(
            directory, archetype="python-lib", module="rn_forge.demo", yes=True
        )
    assert not directory.exists()
    assert not (tmp_path / ".staging").exists()


def test_s16_4_7_6_new_writes_the_commented_form(tmp_path: Path) -> None:
    commands.new(tmp_path / "demo", archetype="python-tool", docs="none", yes=True)

    text = (tmp_path / "demo" / ".rn-forge/kiln/config.toml").read_text(
        encoding="utf-8"
    )
    assert '# One of: "default-branch", "every-run".' in text


# S16.6.8 — `repository.owner` is configured.


def _owner_written(directory: Path) -> str:
    text = (directory / ".rn-forge/kiln/config.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)["repository"]["owner"]


def test_s16_6_8_1_new_without_owner_fails(ownerless: None, tmp_path: Path) -> None:
    directory = tmp_path / "demo"

    with pytest.raises(AppException) as raised:
        commands.new(directory, archetype="python-tool", docs="none", yes=True)

    assert raised.value.message.startswith("new.owner-required: ")
    assert "--owner" in raised.value.message
    assert not directory.exists()


def test_s16_6_8_1_new_without_owner_exits_non_zero(
    ownerless: None, tmp_path: Path
) -> None:
    from rn_forge.kiln import main

    code = main.app(["new", str(tmp_path / "demo"), "--archetype", "python-tool"])

    assert code != 0


def test_s16_6_8_2_new_with_owner_writes_it(ownerless: None, tmp_path: Path) -> None:
    directory = tmp_path / "demo"

    commands.new(
        directory, archetype="python-tool", docs="none", owner="acme", yes=True
    )

    assert _owner_written(directory) == "acme"


def test_s16_6_8_2_new_takes_owner_from_config(ownerless: None, tmp_path: Path) -> None:
    layer = tmp_path / "layer"
    layer.mkdir()
    (layer / "config.toml").write_text(
        '[repository]\nowner = "from-config"\n', encoding="utf-8"
    )
    directory = tmp_path / "demo"

    commands.new(
        directory, archetype="python-tool", docs="none", config=str(layer), yes=True
    )

    assert _owner_written(directory) == "from-config"


def test_s16_6_8_2_the_flag_beats_config(ownerless: None, tmp_path: Path) -> None:
    layer = tmp_path / "layer"
    layer.mkdir()
    (layer / "config.toml").write_text(
        '[repository]\nowner = "from-config"\n', encoding="utf-8"
    )
    directory = tmp_path / "demo"

    commands.new(
        directory,
        archetype="python-tool",
        docs="none",
        config=str(layer),
        owner="flag",
        yes=True,
    )

    assert _owner_written(directory) == "flag"


@pytest.mark.parametrize("archetype", ["node-lib", "python-tool"])
def test_s16_7_3_8_new_formats_after_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, archetype: str
) -> None:
    calls: list[tuple[Path, bool]] = []
    frontend = tmp_path / "prepared"
    frontend.mkdir()

    monkeypatch.setattr(commands, "scaffold_backend", lambda *_: None)
    monkeypatch.setattr(commands, "reconcile_backend", lambda *_: None)
    monkeypatch.setattr(
        commands,
        "scaffold_node",
        lambda _raw, config: frontend if config.archetype == "node-lib" else None,
    )
    monkeypatch.setattr(commands, "reconcile_node", lambda *_: None)
    monkeypatch.setattr(
        commands,
        "format_node",
        lambda workspace: calls.append(
            (workspace, (workspace / ".prettierrc").is_file())
        ),
    )

    commands.new(tmp_path / "demo", archetype=archetype, docs="none", yes=True)

    if archetype == "node-lib":
        assert len(calls) == 1
        assert calls[0][1] is True
    else:
        assert calls == []
