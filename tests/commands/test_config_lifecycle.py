"""`kiln config update` and `kiln config upgrade`.

Two repo shapes:

- `resolved_repo` — built from a local layer with a hand-written `[source]`, applied once (`kiln
  new`'s own flow, per `commands.new`), so it has a real `[source]` to
  re-resolve and `state.json` carries real recorded `config_provenance`. It is
  not a full scaffold (no `uv init`), so `--apply`'s post-apply checks are not
  exercised on it.
- `repo` — a copy of the rendered `python-tool` repo `tests/commands/test_apply.py` builds on,
  which passes every check. Its recorded provenance is replaced here with
  what a flags-only `kiln new` leaves — every committed key attributed to the flags
  layer — to exercise `--apply` and the schema-upgrade path against a repo
  whose checks actually pass.
"""

from __future__ import annotations

import json
from collections.abc import Callable
import shutil
import tomllib
from pathlib import Path
from typing import Any

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import ConfigFormat, DocumentUtils
from rn_forge.commons.lang.collections import DictUtils
from rn_forge.commons.runtime.console import OutputMode, console

from tests.conftest import snapshot

from rn_forge.kiln import commands
from rn_forge.kiln.commands import output
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.core.config.manager import FLAGS_LAYER, ConfigManager
from rn_forge.kiln.modules.core.config.sources import Source
from rn_forge.kiln.modules.docs import generate as docs_generator
from rn_forge.kiln.modules.docs.work import BOARD_BLOCK

FLAGS = {"repository": {"name": "demo", "owner": "rn-forge", "archetype": "python-app"}}
CONFIG_PATH = Path(".rn-forge") / "kiln" / "config.toml"
STATE_PATH = Path(".rn-forge") / "kiln" / "state.json"


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
    document = resolution.config.to_document()
    document["source"] = {"location": str(layer)}
    (root / CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / CONFIG_PATH).write_text(
        DocumentUtils.dumps(document, ConfigFormat.TOML),
        encoding="utf-8",
    )
    cycle.apply(root, provenance=resolution.provenance_metadata())
    monkeypatch.chdir(root)
    yield root
    console.set_mode(OutputMode.PLAIN)


@pytest.fixture
def repo(
    monkeypatch: pytest.MonkeyPatch,
    rendered_copy: Callable[..., Path],
) -> Path:
    root = rendered_copy("python-tool")
    cycle.apply(root)
    _seed_flags_provenance(root)
    monkeypatch.chdir(root)
    yield root
    console.set_mode(OutputMode.PLAIN)


def _seed_flags_provenance(root: Path) -> None:
    """Record every committed key as flags-layer provenance, as `kiln new` would.

    Replaces the `state.json` provenance with what a flags-only `kiln new`
    leaves, so `reresolve` has a baseline to compare the committed file against.
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


def test_update_dry_run_on_a_clean_repo_reports_nothing_and_writes_nothing(
    resolved_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = (resolved_repo / CONFIG_PATH).read_text(encoding="utf-8")

    commands.config_update(dry_run=True, json=True)

    payload = _last_json(capsys)
    assert payload["artifacts"] == []
    assert payload["overrides"] == []
    assert (resolved_repo / CONFIG_PATH).read_text(encoding="utf-8") == before


def test_update_dry_run_reports_the_artifacts_a_source_change_would_change(
    resolved_repo: Path, layer: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_layer(layer, {"docs": {"profile": "none"}, "ci": {"sonar": True}})

    commands.config_update(dry_run=True, json=True)

    payload = _last_json(capsys)
    assert len(payload["artifacts"]) > 0
    assert payload["overrides"] == []


def test_a_repo_override_survives_update_and_is_listed(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _flip_sonar(repo)

    commands.config_update(dry_run=True, json=True)

    payload = _last_json(capsys)
    assert payload["overrides"] == ["ci.sonar"]


def test_a_repo_override_survives_upgrade_and_is_listed(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _flip_sonar(repo)
    _stale_schema(repo)

    commands.config_upgrade(dry_run=True, json=True)

    payload = _last_json(capsys)
    assert payload["overrides"] == ["ci.sonar"]


def test_apply_writes_the_remerged_config_then_apply_dry_run_is_clean(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _flip_sonar(repo)

    commands.config_update(apply=True, json=True)

    text = (repo / CONFIG_PATH).read_text(encoding="utf-8")
    assert "sonar = false" in text  # the repo override survived the re-merge

    commands.apply(dry_run=True, json=True)
    payload = _last_json(capsys)
    assert all(row["action"] in ("unchanged", "skip") for row in payload["artifacts"])


def _delete_source(root: Path) -> None:
    document = tomllib.loads((root / CONFIG_PATH).read_text(encoding="utf-8"))
    del document["source"]
    (root / CONFIG_PATH).write_text(
        DocumentUtils.dumps(document, ConfigFormat.TOML), encoding="utf-8"
    )


def test_deleting_source_keeps_its_values(
    resolved_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _delete_source(resolved_repo)

    commands.config_update(apply=True, json=True)

    kept = tomllib.loads((resolved_repo / CONFIG_PATH).read_text(encoding="utf-8"))
    assert kept["docs"]["profile"] == "none"
    assert kept["ci"]["sonar"] is False

    commands.config_update(dry_run=True, json=True)
    assert _last_json(capsys)["artifacts"] == []


def test_deleted_source_values_become_overrides(
    resolved_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _delete_source(resolved_repo)

    commands.config_update(dry_run=True, json=True)

    overrides = _last_json(capsys)["overrides"]
    assert "docs.profile" in overrides
    assert "ci.sonar" in overrides


def test_a_missing_source_file_still_refuses(resolved_repo: Path, layer: Path) -> None:
    layer.unlink()

    with pytest.raises(AppException):
        commands.config_update(dry_run=True)


def test_update_refuses_a_stale_schema_naming_config_upgrade(
    resolved_repo: Path,
) -> None:
    _stale_schema(resolved_repo)

    with pytest.raises(AppException, match="kiln config-upgrade"):
        commands.config_update(dry_run=True)


def test_upgrade_migrates_a_config_from_the_previous_schema_version(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _stale_schema(repo)

    commands.config_upgrade(apply=True, json=True)

    text = (repo / CONFIG_PATH).read_text(encoding="utf-8")
    assert "schema_version = 1" in text
    commands.apply(dry_run=True, json=True)
    payload = _last_json(capsys)
    assert all(row["action"] in ("unchanged", "skip") for row in payload["artifacts"])


def test_config_update_writes_the_commented_form(repo: Path) -> None:
    commands.config_update(apply=True, json=True)

    text = (repo / CONFIG_PATH).read_text(encoding="utf-8")
    assert '# One of: "default-branch", "every-run".' in text


def test_config_upgrade_writes_the_commented_form(repo: Path) -> None:
    _stale_schema(repo)

    commands.config_upgrade(apply=True, json=True)

    text = (repo / CONFIG_PATH).read_text(encoding="utf-8")
    assert '# One of: "default-branch", "every-run".' in text


@pytest.mark.parametrize("upgrade", [False, True])
def test_config_preview_and_dry_run_match_apply_with_a_missing_starter(
    repo: Path, capsys: pytest.CaptureFixture[str], upgrade: bool
) -> None:
    starter = next(repo.glob("src/*/product.py"))
    relative = starter.relative_to(repo).as_posix()
    starter.unlink()
    _flip_sonar(repo)
    if upgrade:
        _stale_schema(repo)
    command = commands.config_upgrade if upgrade else commands.config_update
    before = snapshot(repo)
    capsys.readouterr()

    command(json=True)
    preview = _last_json(capsys)["artifacts"]
    assert snapshot(repo) == before
    command(dry_run=True, apply=True, json=True)
    assert _last_json(capsys)["artifacts"] == preview
    assert snapshot(repo) == before

    command(apply=True, json=True)

    applied = _last_json(capsys)["artifacts"]
    assert preview == [
        row for row in applied if row["action"] not in ("unchanged", "skip")
    ]
    assert [row["action"] for row in applied if row["path"] == relative] == ["forget"]
    assert not starter.exists()


@pytest.mark.parametrize("failure", ["docs", "ownership"])
def test_config_apply_restores_its_footprint_after_finalization_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    _stale_schema(repo)
    _flip_sonar(repo)
    config = repo / CONFIG_PATH
    managed = repo / "Taskfile.yml"
    state = repo / STATE_PATH
    board = repo / "docs/specs/index.md"
    board.write_text(
        BOARD_BLOCK.render(board.read_text(encoding="utf-8"), "\nStale board.\n\n"),
        encoding="utf-8",
    )
    created = repo / "docs/guides/partial.md"
    before = {path: path.read_bytes() for path in (config, managed, board, state)}
    generate = docs_generator.generate
    check_ownership = output.fail_on_errors

    def assert_candidate_applied() -> None:
        assert b"schema_version = 1" in config.read_bytes()
        assert managed.read_bytes() != before[managed]
        assert board.read_bytes() != before[board]

    def fail_generation(*args: Any, **kwargs: Any) -> None:
        generate(*args, **kwargs)
        assert_candidate_applied()
        created.write_bytes(b"partial docs")
        raise AppException("injected docs failure")

    def fail_ownership(root: Path) -> None:
        assert state.read_bytes() != before[state]
        check_ownership(root)
        raise AppException("injected ownership failure")

    if failure == "docs":
        monkeypatch.setattr(docs_generator, "generate", fail_generation)
    else:
        monkeypatch.setattr(output, "fail_on_errors", fail_ownership)

    with pytest.raises(AppException, match=f"injected {failure} failure"):
        commands.config_upgrade(apply=True)

    assert {path: path.read_bytes() for path in before} == before
    assert not created.exists()
