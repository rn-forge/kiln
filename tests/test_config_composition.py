"""`KilnConfig` composes what one module needs from another."""

from __future__ import annotations

import configparser
from pathlib import Path

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd import registry
from tests.conftest import write_config

REPO = Path(__file__).resolve().parents[1]
COMPOSITION = [
    "rn_forge.kiln.config -> rn_forge.kiln.modules.**",
    "rn_forge.kiln.modules.registry -> rn_forge.kiln.modules.**",
]


def test_the_independence_contract_ignores_only_composition() -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(REPO / ".importlinter", encoding="utf-8")
    section = parser["importlinter:contract:concern-modules-are-independent"]
    ignored = [
        line.strip() for line in section["ignore_imports"].splitlines() if line.strip()
    ]
    assert ignored == COMPOSITION


def test_config_composes_the_ci_facts(tmp_path: Path) -> None:
    config = KilnConfig.load(write_config(tmp_path, "python-lib"))
    assert config.ci_checks == registry.enabled_names(
        config.ci, config.archetype, len(config.packages)
    )
    assert config.ci_matrix() == registry.render_matrix("python-lib")
    assert config.ci_matrix(every_archetype=True) == registry.render_matrix(None)
