"""S15.1.2 — `[ci.checks]` is validated from the registry."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from rn_forge.kiln.modules.cicd.config import CiConfig, LicensePolicy


def _load(checks: dict[str, Any]) -> CiConfig:
    return CiConfig(checks=checks)


def test_s15_1_2_1_bool_switches() -> None:
    assert _load({"secret-scan": False}).checks == {"secret-scan": False}
    assert _load({"licenses": True}).checks == {"licenses": True}


def test_s15_1_2_2_unknown_name() -> None:
    with pytest.raises(
        ValidationError, match="ci.checks.nope is not a configurable check"
    ):
        _load({"nope": True})


@pytest.mark.parametrize(
    ("name", "kind"), [("internal-ranges", "derived"), ("pnpm-audit", "standard")]
)
def test_s15_1_2_3_switchless_check(name: str, kind: str) -> None:
    with pytest.raises(
        ValidationError, match=f"ci.checks.{name} is {kind} and has no switch"
    ):
        _load({name: True})


def test_s15_1_2_4_policy_table() -> None:
    ci = _load({"licenses": {"deny": ["GPL-*"], "ignore": ["x"]}})
    assert ci.licenses_policy() == LicensePolicy(deny=["GPL-*"], ignore=["x"])
    default = CiConfig().licenses_policy()
    assert default.deny == ["GPL", "GPL-*", "AGPL", "AGPL-*", "UNKNOWN"]
    assert default.ignore == []


def test_s15_1_2_5_table_for_a_check_without_policy() -> None:
    with pytest.raises(ValidationError, match="ci.checks.scorecard takes no policy"):
        _load({"scorecard": {"x": 1}})


def test_s15_1_2_6_unknown_policy_key() -> None:
    with pytest.raises(ValidationError):
        _load({"licenses": {"allow": []}})


@pytest.mark.parametrize("value", [False, True])
def test_s17_2_4_1_table_only(value: bool) -> None:
    with pytest.raises(
        ValidationError,
        match="ci.checks.pip-audit is always on; set a table with ignore",
    ):
        _load({"pip-audit": value})
