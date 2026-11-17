"""`kiln new`: flags, previews, config layers and pins.

The end-to-end tests that run `uv init` through the python scaffold are slow;
`tests/modules/python/test_scaffold.py` marks none of its own `uv init` tests
either, so none are marked here.
"""

from __future__ import annotations
import pytest
import subprocess
import tomllib
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.kiln import archetypes, checks
from rn_forge.kiln.commands.new import FLAG_NAMES, flag_layer
from rn_forge.kiln.modules.core.config.manager import ConfigManager
from rn_forge.kiln.modules.registry import builtin
from tests.conftest import new_repo, requires
from typing import Any
from tests.commands.new_support import _last_json


@pytest.fixture(autouse=True)
def _in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`kiln new` stages beneath the current directory; keep that out of the repo."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


def test_flags_match_module_union() -> None:
    """`new`'s config-setting flags are exactly backed by a registered module's `Option`.

    `framework`/`frontend` join both the signature and this set once
    a module that declares them is registered — see `FLAG_NAMES` in commands/new.py
    comment.
    """
    union = {option.flag for module in builtin().modules for option in module.options()}
    assert set(FLAG_NAMES) == union


def test_preview_without_yes_writes_nothing(tmp_path: Path) -> None:
    directory = tmp_path / "preview"
    new_repo(directory, archetype="python-app", docs="none")
    assert not (directory / ".rn-forge").exists()


def test_preview_json_lists_artifacts_without_writing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = tmp_path / "preview"
    new_repo(directory, archetype="python-app", docs="none", json=True)
    payload = _last_json(capsys)
    assert payload["root"] == str(directory.resolve())
    assert len(payload["artifacts"]) > 0
    assert all(
        row["action"] in ("create", "insert", "skip") for row in payload["artifacts"]
    )
    assert not (directory / ".rn-forge").exists()


def test_nonempty_directory_is_refused_and_writes_nothing(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "full"
    directory.mkdir()
    (directory / "x").write_text("x", encoding="utf-8")

    with pytest.raises(AppException, match=str(directory)):
        new_repo(directory, archetype="python-app", docs="none", yes=True)
    assert not (directory / ".rn-forge").exists()


def test_untested_flag_value_is_refused_without_allow_untested() -> None:
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
        flag_layer(
            archetype="python-app",
            docs="external",
            manifest=manifest,
            allow_untested=False,
        )

    flags = flag_layer(
        archetype="python-app", docs="external", manifest=manifest, allow_untested=True
    )
    assert flags["docs"]["profile"] == "external"


@pytest.mark.parametrize("value", [None, ""])
def test_missing_archetype_is_refused(tmp_path: Path, value: str | None) -> None:
    kwargs: dict[str, Any] = {"docs": "none"}
    if value is not None:
        kwargs["archetype"] = value
    with pytest.raises(AppException, match="--archetype"):
        new_repo(tmp_path / "repo", **kwargs)


@pytest.mark.parametrize(
    ("match", "kwargs"),
    [
        pytest.param(
            "backend",
            {"archetype": "python-app", "backend": "fastapi"},
            id="backend-on-a-non-web-archetype",
        ),
        pytest.param(
            "frontend",
            {
                "archetype": "python-web-api",
                "backend": "fastapi",
                "frontend": "angular",
                "allow_untested": True,
            },
            id="frontend-on-python-web-api",
        ),
        pytest.param(
            "frontend",
            {"archetype": "python-app", "frontend": "angular"},
            id="frontend-on-a-non-web-archetype",
        ),
        pytest.param(
            "backend",
            {
                "archetype": "python-web-api",
                "backend": "spring-boot",
                "allow_untested": True,
            },
            id="unsupported-backend",
        ),
    ],
)
def test_a_refused_selector_is_rejected_before_writing(
    tmp_path: Path, match: str, kwargs: dict[str, Any]
) -> None:
    directory = tmp_path / "repo"
    with pytest.raises(AppException, match=match):
        new_repo(directory, docs="none", **kwargs)
    assert not directory.exists() or not any(directory.iterdir())


@pytest.mark.parametrize("archetype", ["python-web-api", "python-web-app"])
def test_web_defaults_select_fastapi(archetype: str) -> None:
    manifest = archetypes.load(archetype)
    flags = flag_layer(
        archetype=archetype,
        docs="none",
        manifest=manifest,
        allow_untested=False,
    )
    flags["repository"]["name"] = "demo"
    flags["repository"]["owner"] = "rn-forge"
    resolved = ConfigManager().resolve(flags=flags).config
    assert resolved.backend == "fastapi"
    assert resolved.frontend == ("angular" if archetype == "python-web-app" else None)


@pytest.mark.parametrize(
    ("archetype", "selector", "value"),
    [
        ("python-web-api", "backend", "django"),
        ("python-web-app", "frontend", "svelte"),
    ],
)
def test_explicit_selectors_override_web_defaults(
    archetype: str, selector: str, value: str
) -> None:
    manifest = archetypes.load(archetype)
    flags = flag_layer(
        archetype=archetype,
        docs="none",
        manifest=manifest,
        allow_untested=True,
        **{selector: value},
    )
    flags["repository"]["name"] = "demo"
    flags["repository"]["owner"] = "rn-forge"
    resolved = ConfigManager().resolve(flags=flags).config
    assert getattr(resolved, selector) == value


@pytest.mark.parametrize("archetype", ["python-web-api", "python-web-app"])
def test_django_remains_untested_for_both_web_archetypes(
    tmp_path: Path, archetype: str
) -> None:
    with pytest.raises(AppException, match="django"):
        new_repo(
            tmp_path / "demo",
            archetype=archetype,
            docs="none",
            backend="django",
            yes=True,
        )
    assert not (tmp_path / "demo").exists()


@requires("uv")
def test_yes_creates_and_passes_every_check(tmp_path: Path) -> None:
    """The slow path: `uv init` through the python scaffold, then a full apply."""
    directory = tmp_path / "demo"
    new_repo(directory, archetype="python-tool", docs="none", yes=True)

    assert (directory / ".rn-forge" / "kiln" / "config.toml").is_file()
    assert (directory / "pyproject.toml").is_file()
    assert checks.run(directory) == []


def test_yes_json_artifacts_actions_only_create_insert_or_skip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = tmp_path / "demo-json"
    new_repo(directory, archetype="python-tool", docs="none", yes=True, json=True)
    payload = _last_json(capsys)
    assert payload["root"] == str(directory.resolve())
    assert len(payload["artifacts"]) > 0
    assert all(
        row["action"] in ("create", "insert", "skip") for row in payload["artifacts"]
    )


def test_config_layer_merges_beneath_flags(tmp_path: Path) -> None:
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "config.toml").write_text("[ci]\nsonar = false\n", encoding="utf-8")

    directory = tmp_path / "demo-layered"
    new_repo(
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


def test_new_with_a_local_config_records_no_source(tmp_path: Path) -> None:
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "config.toml").write_text("[ci]\nsonar = false\n", encoding="utf-8")

    directory = tmp_path / "demo-local-layer"
    new_repo(
        directory,
        archetype="python-tool",
        docs="none",
        config=str(layer_dir),
        yes=True,
    )

    text = (directory / ".rn-forge" / "kiln" / "config.toml").read_text(
        encoding="utf-8"
    )
    assert "source" not in tomllib.loads(text)
    assert str(tmp_path) not in text


def test_new_pins_kiln(tmp_path: Path, kiln_remote_sha: str) -> None:
    directory = tmp_path / "demo-pinned"
    new_repo(directory, archetype="python-tool", docs="none", yes=True)
    written = tomllib.loads(
        (directory / ".rn-forge" / "kiln" / "config.toml").read_text(encoding="utf-8")
    )
    assert written["kiln"] == {"ref": kiln_remote_sha, "track": archetypes.KILN_REF}


def test_a_config_layer_pin_wins(tmp_path: Path) -> None:
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "config.toml").write_text('[kiln]\nref = "v1.2.3"\n', encoding="utf-8")
    directory = tmp_path / "demo-layer-pin"
    new_repo(
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


def test_new_takes_the_name_from_config(tmp_path: Path) -> None:
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "config.toml").write_text(
        '[repository]\nname = "repo-name"\n', encoding="utf-8"
    )

    directory = tmp_path / "dir-name"
    new_repo(
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


def test_git_config_merges_beneath_flags_and_records_source(
    tmp_path: Path,
) -> None:
    location, sha = _bare_layer_repo(
        tmp_path, '[ci]\nsonar = false\n\n[docs]\nprofile = "mkdocs"\n'
    )

    directory = tmp_path / "demo-git"
    new_repo(
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


def test_unreachable_url_and_missing_ref_name_the_url(
    tmp_path: Path,
) -> None:
    missing = f"git+file://{tmp_path / 'nope.git'}"
    with pytest.raises(AppException) as unreachable:
        new_repo(
            tmp_path / "a",
            archetype="python-tool",
            docs="none",
            config=f"{missing}@main",
        )
    assert missing in str(unreachable.value)

    location, _ = _bare_layer_repo(tmp_path, "[ci]\nsonar = false\n")
    with pytest.raises(AppException) as no_ref:
        new_repo(
            tmp_path / "b",
            archetype="python-tool",
            docs="none",
            config=f"{location}@nope",
        )
    assert location in str(no_ref.value)
    assert not (tmp_path / "a").exists()
    assert not (tmp_path / "b").exists()


def test_new_pins_the_branch_head(tmp_path: Path, kiln_remote_sha: str) -> None:
    directory = tmp_path / "demo-head"
    new_repo(directory, archetype="python-tool", docs="none", yes=True)
    written = tomllib.loads(
        (directory / ".rn-forge" / "kiln" / "config.toml").read_text(encoding="utf-8")
    )
    assert written["kiln"] == {"ref": kiln_remote_sha, "track": archetypes.KILN_REF}
    kiln_yml = (directory / "tasks" / "kiln.yml").read_text(encoding="utf-8")
    assert f"@{kiln_remote_sha}" in kiln_yml
