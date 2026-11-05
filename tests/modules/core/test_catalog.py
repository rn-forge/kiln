"""S16.4.7 — `config.toml` explains every option."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from rn_forge.kiln import archetypes, commands
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.config import catalog
from rn_forge.kiln.modules.core.config.manager import ConfigManager

CONFIG = Path(".rn-forge") / "kiln" / "config.toml"


def _config(name: str = "python-tool", **sections: dict[str, object]) -> KilnConfig:
    flags: dict[str, object] = {
        "repository": {"name": "demo", "archetype": name},
        **sections,
    }
    return ConfigManager().resolve(flags=flags).config


def _written(tmp_path: Path, config: KilnConfig) -> str:
    commands._write_config(tmp_path, config)  # noqa: SLF001
    return (tmp_path / CONFIG).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", archetypes.shipped())
def test_s16_4_7_1_every_field_described(name: str) -> None:
    specs = catalog.for_archetype(name)

    assert specs
    assert [spec.path for spec in specs if not spec.description.strip()] == []


def test_s16_4_7_2_choices_and_defaults() -> None:
    index = {spec.path: spec for spec in catalog.for_archetype("python-tool")}

    doctor_full = index["ci.doctor_full"]
    assert doctor_full.choices == ("default-branch", "every-run")
    assert doctor_full.default == "default-branch"
    assert doctor_full.module == "cicd"
    release = index["ci.release"]
    assert release.default is None
    assert release.default_note
    assert index["docs.profile"].module == "docs"
    assert index["repository.name"].module == "core"
    assert "cli" in index
    assert "lifecycle" in index


def test_s16_4_7_3_commented_render(tmp_path: Path) -> None:
    text = _written(tmp_path, _config())

    spec = {s.path: s for s in catalog.for_archetype("python-tool")}["ci.doctor_full"]
    expected = [f"# {line}" for line in spec.description.splitlines()]
    expected += [
        '# One of: "default-branch", "every-run".',
        '# Default: "default-branch".',
        'doctor_full = "default-branch"',
    ]
    lines = text.splitlines()
    at = lines.index('doctor_full = "default-branch"')
    assert lines[at - len(expected) + 1 : at + 1] == expected


def test_s16_4_7_4_none_default_commented(tmp_path: Path) -> None:
    text = _written(tmp_path, _config())

    assert '# release = "tag-exists"' in text.splitlines()
    assert not [line for line in text.splitlines() if line.startswith("release =")]

    pinned = _written(tmp_path / "pinned", _config(ci={"release": "pypi"}))
    assert 'release = "pypi"' in pinned.splitlines()


def test_s16_4_7_5_round_trip(tmp_path: Path) -> None:
    config = _config(
        "python-lib",
        ci={
            "jobs": [{"name": "extra", "uses": "./.github/workflows/extra.yml"}],
            "hooks": {"setup": ["./.github/actions/setup-node"]},
        },
        docs={"profile": "mkdocs", "mkdocs": {"theme": {"font": {"text": "x"}}}},
        tasks={"includes": [{"namespace": "self", "taskfile": "tasks/self.yml"}]},
        archetype={"python-lib": {"packages": ["packages/a"]}},
    )
    first = _written(tmp_path, config)

    loaded = KilnConfig.load(tmp_path)

    assert tomllib.loads(first) == loaded.to_document()
    # Model equality also compares which fields were set; the file sets them all.
    assert loaded.document.model_dump() == config.document.model_dump()
    again = tmp_path / "again"
    assert _written(again, loaded) == first
