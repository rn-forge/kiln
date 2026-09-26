"""S4.5.5 — Lifecycle wiring.

`[lifecycle]` in kiln's own declaration (`src/rn_forge/kiln/cli.toml`, held
equal to `.rn-forge/kiln/config.toml` by `tests/test_cli_surface.py`) names
`PRODUCT`; `rn-forge-tooling`'s `build_tool_app` mounts all six verbs under
`kiln self`, so `kiln self doctor` checks the install and `kiln doctor` stays
the repository check.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from rn_forge.cli import CliApp, ExitCode
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.tooling.cli.lifecycle import build_tool_app

from rn_forge.kiln import commands
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.core.config.schema import RootConfig

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
    return build_tool_app(ROOT / "src" / "rn_forge" / "kiln" / "cli.toml")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(GOLDEN, root, ignore=_IGNORE)
    cycle.apply(root)
    monkeypatch.chdir(root)
    yield root


_VERBS = ("install", "upgrade", "uninstall", "cleanup", "status", "doctor")


def test_s4_5_5_1_help_lists_self(
    kiln_cli: CliApp, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kiln_cli.run(["--help"]) == 0
    assert "self" in capsys.readouterr().out


def test_s4_5_5_1_self_help_lists_every_verb(
    kiln_cli: CliApp, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kiln_cli.run(["self", "--help"]) == 0
    out = capsys.readouterr().out
    for verb in _VERBS:
        assert verb in out


def test_s4_5_5_1_bare_verbs_are_not_root_commands(kiln_cli: CliApp) -> None:
    for verb in ("install", "upgrade", "uninstall", "cleanup", "status"):
        assert kiln_cli.run([verb]) == ExitCode.USAGE


def test_s4_5_5_2_self_status_json_has_a_version(
    kiln_cli: CliApp, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kiln_cli.run(["--json", "self", "status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"]


def test_s4_5_5_4_self_doctor_checks_the_install(
    kiln_cli: CliApp, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kiln_cli.run(["self", "doctor"]) == 0
    assert "kiln.home" in capsys.readouterr().out


def test_s4_5_5_4_doctor_checks_the_repository(
    kiln_cli: CliApp, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kiln_cli.run(["doctor", str(repo)]) == 0
    captured = capsys.readouterr()
    assert "kiln.home" not in captured.out + captured.err


def test_s4_5_5_root_config_carries_the_lifecycle_table() -> None:
    config = RootConfig.model_validate(
        {
            "schema_version": 1,
            "repository": {"name": "x", "archetype": "python-tool"},
            "lifecycle": {"product": "a:B", "namespace": "self"},
        }
    )
    assert config.lifecycle == {"product": "a:B", "namespace": "self"}


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
