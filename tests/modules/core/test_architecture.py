"""The architecture records' catalogue."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.conftest import LIB_PACKAGES, write_config

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.architecture import RECORDS, records_for


def _ids(
    tmp_path: Path,
    archetype: str,
    backend: str | None = None,
    frontend: str | None = None,
) -> list[str]:
    root = write_config(
        tmp_path,
        archetype,
        docs="mkdocs",
        backend=backend,
        frontend=frontend,
        packages=LIB_PACKAGES if archetype == "python-lib" else None,
    )
    return [record.id for record in records_for(KilnConfig.load(root))]


@pytest.mark.parametrize(
    ("archetype", "expected"),
    [
        ("python-app", ["ARCH-0001", "ARCH-0002"]),
        ("python-tool", ["ARCH-0001", "ARCH-0002"]),
        ("python-lib", ["ARCH-0003"]),
        ("node-lib", []),
    ],
)
def test_each_cell_gets_its_records(
    tmp_path: Path, archetype: str, expected: list[str]
) -> None:
    assert _ids(tmp_path, archetype) == expected


@pytest.mark.parametrize(
    ("archetype", "backend", "frontend", "expected"),
    [
        ("python-web-api", "fastapi", None, ["ARCH-0001", "ARCH-0002", "ARCH-0004"]),
        (
            "python-web-app",
            "fastapi",
            "angular",
            ["ARCH-0001", "ARCH-0002", "ARCH-0004"],
        ),
        ("python-web-api", "django", None, ["ARCH-0001", "ARCH-0002"]),
    ],
)
def test_each_web_cell_gets_its_records(
    tmp_path: Path,
    archetype: str,
    backend: str,
    frontend: str | None,
    expected: list[str],
) -> None:
    assert _ids(tmp_path, archetype, backend, frontend) == expected


def test_record_ids_are_unique_and_in_order() -> None:
    ids = [record.id for record in RECORDS]
    assert ids == sorted(set(ids))
    assert ids == ["ARCH-0001", "ARCH-0002", "ARCH-0003", "ARCH-0004"]
