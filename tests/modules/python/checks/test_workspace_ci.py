"""S16.6.12 — doctor reports a legacy or incomplete `[tool.workspace-ci]` table."""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.commons.findings import Finding

from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.devops import uv
from rn_forge.kiln.modules.python.checks import workspace_ci

CONFIG = """
schema_version = 1

[repository]
name = "demo"
owner = "rn-forge"
archetype = "{archetype}"
{extra}
"""

LIB_EXTRA = '\n[archetype."python-lib"]\npackages = ["packages/auth"]\n'


def _repo(tmp_path: Path, table: str, archetype: str = "python-lib") -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    extra = LIB_EXTRA if archetype == "python-lib" else ""
    config.write_text(CONFIG.format(archetype=archetype, extra=extra), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "1"\n\n'
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n',
        encoding="utf-8",
    )
    member = tmp_path / "packages/auth"
    member.mkdir(parents=True)
    (member / "pyproject.toml").write_text(
        '[project]\nname = "auth"\nversion = "1"\n\n' + table, encoding="utf-8"
    )
    return tmp_path


def _findings(root: Path) -> list[Finding]:
    return workspace_ci.check(KilnConfig.load(root), root)


def test_s16_6_12_1_legacy_table_is_an_error(tmp_path: Path) -> None:
    root = _repo(tmp_path, '[tool.workspace-ci.redis]\nimage = "redis:7"\n')
    (finding,) = _findings(root)
    assert finding.code == "workspace-ci.legacy-service"
    assert finding.path == "packages/auth/pyproject.toml"
    assert "[tool.workspace-ci.integration.redis]" in finding.message


def test_s16_6_12_2_postgres_too(tmp_path: Path) -> None:
    root = _repo(tmp_path, '[tool.workspace-ci.postgres]\nimage = "postgres:17"\n')
    (finding,) = _findings(root)
    assert finding.code == "workspace-ci.legacy-service"
    assert "[tool.workspace-ci.integration.postgres]" in finding.message


def test_s16_6_12_3_missing_image_and_bad_health_wait(tmp_path: Path) -> None:
    table = (
        '[tool.workspace-ci.integration.a]\nports = ["1:1"]\n\n'
        '[tool.workspace-ci.integration.b]\nimage = "x"\nhealth-wait = 0\n'
    )
    found = _findings(_repo(tmp_path, table))
    assert sorted(f.code for f in found) == [
        "workspace-ci.bad-health-wait",
        "workspace-ci.missing-image",
    ]


def test_s16_6_12_4_clean_integration_tables_pass(tmp_path: Path) -> None:
    table = (
        "[tool.workspace-ci.integration.keycloak]\n"
        'image = "quay.io/keycloak/keycloak:26.4.7"\n'
        'command = ["start-dev", "--import-realm"]\n'
        'ports = ["127.0.0.1:8080:8080"]\n'
        'pytest-args = ["-m", "broker"]\n'
        "health-wait = 300\n"
    )
    assert _findings(_repo(tmp_path, table)) == []


@pytest.mark.parametrize(
    "table",
    [
        '[tool.workspace-ci.redis]\nimage = "redis:7"\n',
        '[tool.workspace-ci.integration.a]\nports = ["1:1"]\n',
        '[tool.workspace-ci.integration.b]\nimage = "x"\nhealth-wait = 0\n',
    ],
)
def test_s16_6_12_5_parity_with_the_loader(tmp_path: Path, table: str) -> None:
    root = _repo(tmp_path, table)
    with pytest.raises(ValueError) as raised:
        uv.load_workspace(root)
    (finding,) = _findings(root)
    assert finding.message == str(raised.value).removeprefix("auth: ")


def test_s16_6_12_6_registry() -> None:
    names = checks.names()
    assert names[names.index("rn-forge-deps") + 1] == "workspace-ci"


def test_s16_6_12_7_other_archetypes_are_not_read(tmp_path: Path) -> None:
    root = _repo(tmp_path, '[tool.workspace-ci.redis]\nimage = "r"\n', "python-app")
    assert _findings(root) == []
