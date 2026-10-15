"""`kiln doctor` runs every render-free check, and refuses what it cannot understand."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from rn_forge.commons.exceptions import AppException

from rn_forge.kiln import checks


def test_every_check_is_named_by_its_module() -> None:
    assert checks.names() == (
        "generated",
        "rn-forge-deps",
        "task-layout",
        "ci-entrypoint",
        "ci-pins",
        "docs-structure",
        "docs-generate",
        "docs-site",
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


@pytest.mark.parametrize("archetype", ["python-app", "python-tool", "python-lib"])
def test_every_rendered_archetype_passes_every_check(
    archetype: str, rendered: Callable[[str], Path]
) -> None:
    """A check that fails a freshly rendered archetype is wrong."""
    assert [str(f) for f in checks.run(rendered(archetype))] == []


def test_running_one_check_is_a_subset_of_running_all(repo) -> None:
    root = repo(**{"pyproject.toml": "[project]\nname = 'x'\n"})
    only = [str(f) for f in checks.run(root, only="generated")]
    every = [str(f) for f in checks.run(root)]
    assert only
    assert set(only).issubset(set(every))


def test_quality_checks_run_only_when_named(repo) -> None:
    root = repo(**{"pyproject.toml": "[project]\nname = 'x'\n"})
    assert [c.name for c in checks.CHECKS if c.scope == "quality"] == [
        "rn-forge-deps",
        "docs-structure",
        "docs-site",
    ]
    assert checks.run(root, only="rn-forge-deps")
    assert not [f for f in checks.run(root) if f.code.startswith("deps.")]
