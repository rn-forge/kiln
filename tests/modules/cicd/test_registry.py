"""S15.1.1 — the check registry."""

from __future__ import annotations

from typing import Any

from rn_forge.kiln.modules.cicd import registry
from rn_forge.kiln.modules.cicd.config import CiConfig
from rn_forge.kiln.modules.cicd.registry import Switch

COLUMNS = ("lib", "tool", "app", "web-api", "web-app", "node-lib")
ALL = (
    "python-lib",
    "python-tool",
    "python-app",
    "python-web-api",
    "python-web-app",
    "node-lib",
)


def _check(name: str) -> registry.CiCheck:
    return next(c for c in registry.CHECKS if c.name == name)


def _ci(checks: dict[str, Any]) -> CiConfig:
    return CiConfig(checks=checks)


def test_s15_1_1_1_names_are_unique() -> None:
    names = [c.name for c in registry.CHECKS]
    assert len(names) == len(set(names))


def test_s15_1_1_2_switch_and_default() -> None:
    for name in ("licenses", "secret-scan"):
        assert (_check(name).switch, _check(name).default) == (Switch.CONFIGURED, True)
    for name in ("umbrella-release", "scorecard"):
        assert (_check(name).switch, _check(name).default) == (Switch.CONFIGURED, False)
    assert _check("internal-ranges").switch is Switch.DERIVED
    special = {
        "licenses",
        "secret-scan",
        "umbrella-release",
        "scorecard",
        "internal-ranges",
    }
    for c in registry.CHECKS:
        if c.name not in special:
            assert c.switch is Switch.STANDARD


def test_s15_1_1_3_configured_rows_have_keys() -> None:
    assert registry.configured_names() == {
        "licenses",
        "secret-scan",
        "umbrella-release",
        "scorecard",
    }
    assert all(
        (c.name in registry.configured_names()) == (c.switch is Switch.CONFIGURED)
        for c in registry.CHECKS
    )


def test_s15_1_1_4_enabled() -> None:
    pip_audit = _check("pip-audit")
    assert registry.enabled(pip_audit, _ci({}), "node-lib", 1) is False
    assert registry.enabled(pip_audit, _ci({}), "python-lib", 1) is True

    licenses = _check("licenses")
    assert registry.enabled(licenses, _ci({}), "python-lib", 1) is True
    assert (
        registry.enabled(licenses, _ci({"licenses": False}), "python-lib", 1) is False
    )
    assert registry.enabled(licenses, _ci({"licenses": {"deny": []}}), "python-lib", 1)
    scorecard = _check("scorecard")
    assert registry.enabled(scorecard, _ci({}), "python-app", 1) is False
    assert (
        registry.enabled(scorecard, _ci({"scorecard": True}), "python-app", 1) is True
    )

    ranges = _check("internal-ranges")
    assert registry.enabled(ranges, _ci({}), "python-lib", 2) is True
    assert registry.enabled(ranges, _ci({}), "python-lib", 1) is False
    assert registry.enabled(ranges, _ci({}), "node-lib", 0) is True
    assert registry.enabled(ranges, _ci({}), "python-app", 5) is False


def test_s15_1_1_5_matrix_rows_match_the_page() -> None:
    lines = registry.render_matrix(None).splitlines()
    assert lines[0] == (
        "| Check | Verb | lib | tool | app | web-api | web-app | node-lib "
        "| Switch and key |"
    )
    assert len(lines) == 2 + len(registry.CHECKS)
    for line in lines[2:]:
        assert line.count("|") == 10


def test_s15_1_1_6_matrix_for_one_archetype() -> None:
    table = registry.render_matrix("node-lib")
    lines = table.splitlines()
    assert lines[0] == "| Check | Verb | Switch and key |"
    expected = [c for c in registry.CHECKS if "node-lib" in c.archetypes]
    assert len(lines) == 2 + len(expected)
    assert "pip-audit" not in table
    assert "`task node:lint:licenses`" in table
    assert "lib |" not in lines[0]
    assert registry.for_archetype("node-lib") == expected
    assert all(a in ALL for c in registry.CHECKS for a in c.archetypes)


def test_s15_2_4_3_registry_row() -> None:
    row = _check("pnpm-audit")
    assert row.switch is Switch.STANDARD
    assert row.archetypes == frozenset({"python-web-app", "node-lib"})
    assert row.verb == "`task node:lint:audit`"
    assert "pnpm-audit" not in registry.configured_names()
    assert registry.configured_names() == {
        "licenses",
        "secret-scan",
        "umbrella-release",
        "scorecard",
    }


def test_s16_7_6_3_the_registry() -> None:
    assert _check("pnpm-audit").archetypes == frozenset({"python-web-app", "node-lib"})


def _verb_of_row(name: str) -> str:
    cell = registry._name_cell(name)  # pyright: ignore[reportPrivateUsage]
    for line in registry.render_matrix(None).splitlines()[2:]:
        cols = [p.strip() for p in line.strip("|").split(" | ")]
        if cols[0] == cell:
            return cols[1]
    raise AssertionError(name)


def test_s17_1_1_1_node_only_row_uses_node() -> None:
    assert _verb_of_row("pnpm-audit") == "`task node:lint:audit`"


def test_s17_1_1_2_both_stacks_name_both() -> None:
    assert _verb_of_row("licenses") == (
        "`task python:lint:licenses`; `node-lib`: `task node:lint:licenses`"
    )


def test_s17_1_1_3_plain_verbs_unchanged() -> None:
    plain = [c for c in registry.CHECKS if c.verb is None or "{stack}" not in c.verb]
    assert plain
    for c in plain:
        assert _verb_of_row(c.name) == registry._verb_cell(  # pyright: ignore[reportPrivateUsage]
            c.verb, "python"
        )


def test_s17_2_3_1_enabled_names() -> None:
    switchable = registry.configured_names()
    settings = (
        {},
        dict.fromkeys(switchable, True),
        dict.fromkeys(switchable, False),
    )
    for checks in settings:
        ci = _ci(checks)
        for archetype in ALL:
            for members in (1, 2):
                assert registry.enabled_names(ci, archetype, members) == {
                    c.name
                    for c in registry.CHECKS
                    if registry.enabled(c, ci, archetype, members)
                }
