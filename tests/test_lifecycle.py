"""S4.5.5 — Lifecycle wiring.

`[cli.lifecycle]` mounts `install`/`upgrade`/`uninstall`/`cleanup`/`status`
flat, from kiln's own real `.rn-forge/kiln/config.toml` — the same
declaration `src/rn_forge/kiln/cli.toml` ships (`tests/test_cli_surface.py`
keeps the two equal). `doctor` is excluded from that mount: `kiln doctor`
already means inspecting a generated repository, so the install-health check
is `kiln self-doctor` instead (S4.5.5's open question, answered).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from rn_forge.cli import CliApp, CliSurface
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import commands
from rn_forge.kiln.modules.core import cycle

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).resolve().parent / "fixtures" / "golden" / "python-tool"
_IGNORE = shutil.ignore_patterns(
    ".venv",
    ".uv-cache",
    ".ruff_cache",
    ".import_linter_cache",
    ".pytest_cache",
    ".docs-site",
    ".git",
    "__pycache__",
)


@pytest.fixture(autouse=True)
def isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("RNF_HOME", str(tmp_path / "home"))
    yield
    console.set_mode(OutputMode.PLAIN)


@pytest.fixture
def kiln_cli() -> CliApp:
    """kiln's own declared CLI, built the way an installed kiln's is."""
    return CliApp.from_surface(
        CliSurface.load(ROOT / "src" / "rn_forge" / "kiln" / "cli.toml")
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(GOLDEN, root, ignore=_IGNORE)
    cycle.apply(root)
    monkeypatch.chdir(root)
    yield root


def test_s4_5_5_help_lists_every_declared_lifecycle_verb(
    kiln_cli: CliApp, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kiln_cli.run(["--help"]) == 0
    out = capsys.readouterr().out
    for verb in ("install", "upgrade", "uninstall", "cleanup", "status"):
        assert verb in out


def test_s4_5_5_status_json_has_a_version(
    kiln_cli: CliApp, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kiln_cli.run(["--json", "status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"]


def test_s4_5_5_doctor_and_self_doctor_are_distinct_and_both_reachable(
    kiln_cli: CliApp,
) -> None:
    names = {
        command.name
        for command in CliSurface.load(
            ROOT / "src" / "rn_forge" / "kiln" / "cli.toml"
        ).commands
    }
    assert {"doctor", "self-doctor"} <= names
    # `doctor` is not one of the mounted lifecycle verbs, so no name collides.
    lifecycle_verbs = CliSurface.load(
        ROOT / "src" / "rn_forge" / "kiln" / "cli.toml"
    ).lifecycle.verbs
    assert "doctor" not in lifecycle_verbs


def test_s4_5_5_self_doctor_on_a_dev_checkout_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    commands.self_doctor()
    assert "kiln.home" in capsys.readouterr().out


def test_s4_5_5_load_warns_on_a_stale_but_still_valid_schema(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _set_schema_version(repo, 0)

    commands.doctor(repo)

    assert "kiln config-upgrade" in capsys.readouterr().err


def test_s4_5_5_load_errors_on_a_stale_schema_that_no_longer_validates(
    repo: Path,
) -> None:
    _set_schema_version(repo, 0)
    _corrupt_ci_provider(repo)

    with pytest.raises(AppException, match="kiln config-upgrade"):
        commands.doctor(repo)


def _set_schema_version(root: Path, version: int) -> None:
    config_path = root / ".rn-forge" / "kiln" / "config.toml"
    text = config_path.read_text(encoding="utf-8")
    assert "schema_version = 1" in text
    config_path.write_text(
        text.replace("schema_version = 1", f"schema_version = {version}"),
        encoding="utf-8",
    )


def _corrupt_ci_provider(root: Path) -> None:
    config_path = root / ".rn-forge" / "kiln" / "config.toml"
    text = config_path.read_text(encoding="utf-8")
    assert 'provider = "github"' in text
    config_path.write_text(
        text.replace('provider = "github"', 'provider = "bogus"'),
        encoding="utf-8",
    )
