"""S4.5.4 — `kiln config update` and `kiln config upgrade`.

Two repo shapes:

- `resolved_repo` — built from a local `--config` source, applied once (`kiln
  new`'s own flow, per `commands.new`), so it has a real `[source]` to
  re-resolve and `state.json` carries real recorded `config_provenance`. It is
  not a full scaffold (no `uv init`), so `--apply`'s post-apply checks are not
  exercised on it.
- `repo` — the `python-tool` golden `tests/test_apply.py` already builds on,
  which passes every check. It carries no recorded provenance of its own (it
  is hand-authored, per `README.md`), so provenance is seeded here the way
  `kiln new` would have left it — every committed key attributed to the flags
  layer — to exercise `--apply` and the schema-upgrade path against a repo
  whose checks actually pass.
"""

from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path
from typing import Any

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import ConfigFormat, DocumentUtils
from rn_forge.commons.lang.collections import DictUtils
from rn_forge.commons.runtime.console import OutputMode, console

from rn_forge.kiln import commands
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.core.config.manager import FLAGS_LAYER, ConfigManager
from rn_forge.kiln.modules.core.config.sources import Source

FLAGS = {"repository": {"name": "demo", "archetype": "python-app"}}
CONFIG_PATH = Path(".rn-forge") / "kiln" / "config.toml"
STATE_PATH = Path(".rn-forge") / "kiln" / "state.json"

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


def _write_layer(path: Path, document: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DocumentUtils.dumps(document, ConfigFormat.TOML), encoding="utf-8")
    return path


@pytest.fixture
def layer(tmp_path: Path) -> Path:
    return _write_layer(
        tmp_path / "profile" / "config.toml",
        {"docs": {"profile": "none"}, "ci": {"sonar": False}},
    )


@pytest.fixture
def resolved_repo(tmp_path: Path, layer: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    resolution = ConfigManager().resolve(
        flags=FLAGS, source=Source(str(layer)), base=root
    )
    (root / CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / CONFIG_PATH).write_text(
        DocumentUtils.dumps(resolution.config.to_document(), ConfigFormat.TOML),
        encoding="utf-8",
    )
    cycle.apply(root, provenance=resolution.provenance_metadata())
    monkeypatch.chdir(root)
    yield root
    console.set_mode(OutputMode.PLAIN)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(GOLDEN, root, ignore=_IGNORE)
    cycle.apply(root)
    _seed_flags_provenance(root)
    monkeypatch.chdir(root)
    yield root
    console.set_mode(OutputMode.PLAIN)


def _seed_flags_provenance(root: Path) -> None:
    """Record every committed key as flags-layer provenance, as `kiln new` would.

    The golden is hand-authored and carries no `state.json` provenance of its
    own; this reconstructs what committing it through `kiln new` would have
    left, so `reresolve` has a baseline to compare the committed file against.
    """
    document = tomllib.loads((root / CONFIG_PATH).read_text(encoding="utf-8"))
    provenance = {
        path: {"layer": FLAGS_LAYER, "value": value}
        for path, value in DictUtils.flatten(document).items()
    }
    state_path = root / STATE_PATH
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.setdefault("metadata", {})["config_provenance"] = provenance
    state_path.write_text(json.dumps(state), encoding="utf-8")


def _last_json(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    out = capsys.readouterr().out.strip().splitlines()
    return json.loads(out[-1])


def _flip_sonar(root: Path) -> None:
    config_path = root / CONFIG_PATH
    text = config_path.read_text(encoding="utf-8")
    assert "sonar = true" in text
    config_path.write_text(
        text.replace("sonar = true", "sonar = false"), encoding="utf-8"
    )


def _stale_schema(root: Path) -> None:
    config_path = root / CONFIG_PATH
    text = config_path.read_text(encoding="utf-8")
    assert "schema_version = 1" in text
    config_path.write_text(
        text.replace("schema_version = 1", "schema_version = 0"), encoding="utf-8"
    )


def test_s4_5_4_update_dry_run_on_a_clean_repo_reports_nothing_and_writes_nothing(
    resolved_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = (resolved_repo / CONFIG_PATH).read_text(encoding="utf-8")

    commands.config_update(dry_run=True, json=True)

    payload = _last_json(capsys)
    assert payload["artifacts"] == []
    assert payload["overrides"] == []
    assert (resolved_repo / CONFIG_PATH).read_text(encoding="utf-8") == before


def test_s4_5_4_update_dry_run_reports_the_artifacts_a_source_change_would_change(
    resolved_repo: Path, layer: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_layer(layer, {"docs": {"profile": "none"}, "ci": {"sonar": True}})

    commands.config_update(dry_run=True, json=True)

    payload = _last_json(capsys)
    assert len(payload["artifacts"]) > 0
    assert payload["overrides"] == []


def test_s4_5_4_a_repo_override_survives_update_and_is_listed(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _flip_sonar(repo)

    commands.config_update(dry_run=True, json=True)

    payload = _last_json(capsys)
    assert payload["overrides"] == ["ci.sonar"]


def test_s4_5_4_a_repo_override_survives_upgrade_and_is_listed(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _flip_sonar(repo)
    _stale_schema(repo)

    commands.config_upgrade(dry_run=True, json=True)

    payload = _last_json(capsys)
    assert payload["overrides"] == ["ci.sonar"]


def test_s4_5_4_apply_writes_the_remerged_config_then_apply_dry_run_is_clean(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _flip_sonar(repo)

    commands.config_update(apply=True, json=True)

    text = (repo / CONFIG_PATH).read_text(encoding="utf-8")
    assert "sonar = false" in text  # the repo override survived the re-merge

    commands.apply(dry_run=True, json=True)
    payload = _last_json(capsys)
    assert all(row["action"] in ("unchanged", "skip") for row in payload["artifacts"])


def test_s4_5_4_update_refuses_a_stale_schema_naming_config_upgrade(
    resolved_repo: Path,
) -> None:
    _stale_schema(resolved_repo)

    with pytest.raises(AppException, match="kiln config-upgrade"):
        commands.config_update(dry_run=True)


def test_s4_5_4_upgrade_migrates_a_config_from_the_previous_schema_version(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _stale_schema(repo)

    commands.config_upgrade(apply=True, json=True)

    text = (repo / CONFIG_PATH).read_text(encoding="utf-8")
    assert "schema_version = 1" in text
    commands.apply(dry_run=True, json=True)
    payload = _last_json(capsys)
    assert all(row["action"] in ("unchanged", "skip") for row in payload["artifacts"])
