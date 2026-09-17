"""`kiln doctor` runs every render-free check, and refuses what it cannot understand."""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.commons.exceptions import AppException

from rn_forge.kiln import checks

GOLDEN = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "golden"


def test_every_check_is_named_by_its_module() -> None:
    assert checks.names() == (
        "generated",
        "rn-forge-deps",
        "pyproject-tool-config",
        "task-layout",
        "ci-entrypoint",
        "ci-pins",
        "docs-structure",
        "docs-nav",
        "docs-site",
        "root-hygiene",
    )


def test_an_unknown_check_name_is_refused(repo) -> None:
    with pytest.raises(AppException, match="Unknown check"):
        checks.run(repo(), only="conjured")


def test_a_repo_with_no_config_is_not_a_kiln_repo(tmp_path: Path) -> None:
    with pytest.raises(AppException, match="not a kiln repo"):
        checks.run(tmp_path)


def test_an_unknown_config_schema_version_is_refused(repo) -> None:
    root = repo()
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "schema_version = 1", "schema_version = 99"
        ),
        encoding="utf-8",
    )
    with pytest.raises(AppException, match="99"):
        checks.run(root)


def test_an_unknown_archetype_is_refused(repo) -> None:
    with pytest.raises(AppException, match="Unknown archetype"):
        checks.run(repo(archetype="python-hovercraft"), only="rn-forge-deps")


@pytest.mark.parametrize("golden", ["python-app", "python-tool", "python-lib"])
def test_every_golden_passes_every_check(golden: str) -> None:
    """The goldens are the oracle: a check that fails one of them is wrong."""
    assert [str(f) for f in checks.run(GOLDEN / golden)] == []


def test_running_one_check_is_a_subset_of_running_all(repo) -> None:
    root = repo(**{"pyproject.toml": "[project]\nname = 'x'\n"})
    only = [str(f) for f in checks.run(root, only="rn-forge-deps")]
    every = [str(f) for f in checks.run(root)]
    assert only
    assert set(only).issubset(set(every))
