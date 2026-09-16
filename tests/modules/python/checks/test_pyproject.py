"""`pyproject-tool-config` — doctor check 8a.

A lint that never rejects anything is untested; a warning-severity check that
ever errors defeats the point of it being one.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rn_forge.commons.findings import Severity

from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.python.checks import pyproject

GOLDEN = Path(__file__).resolve().parents[3] / "fixtures" / "golden"

COMPLIANT = """
[project]
name = "example"
version = "0.1.0"
requires-python = ">=3.14"

[tool.pyright]
typeCheckingMode = "strict"
reportMissingTypeStubs = false

[tool.pytest.ini_options]
addopts = "-ra --import-mode=importlib"

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101", "D", "ANN", "PLR2004"]

[dependency-groups]
dev = ["import-linter", "pyright>=1.1.411", "pytest", "ruff", "rn-forge-kiln"]
"""


def run(root: Path) -> list[str]:
    return [str(f) for f in checks.run(root, only=pyproject.NAME)]


def test_a_compliant_pyproject_passes(repo) -> None:
    assert run(repo(**{"pyproject.toml": COMPLIANT})) == []


def test_s4_3_1_2_a_wrong_project_name_warns_and_does_not_error(repo) -> None:
    bad = COMPLIANT.replace('name = "example"', 'name = "wrong-name"')
    findings = checks.run(repo(**{"pyproject.toml": bad}), only=pyproject.NAME)
    assert findings, "the rule accepted its own violation"
    assert all(f.severity is Severity.WARNING for f in findings)
    assert any("project.name" in f.message for f in findings)


def test_s4_3_1_2_a_wrong_ruff_value_warns_and_does_not_error(repo) -> None:
    bad = COMPLIANT.replace(
        '"tests/*" = ["S101", "D", "ANN", "PLR2004"]', '"tests/*" = ["S101"]'
    )
    findings = checks.run(repo(**{"pyproject.toml": bad}), only=pyproject.NAME)
    assert findings, "the rule accepted its own violation"
    assert all(f.severity is Severity.WARNING for f in findings)
    assert any("ruff" in f.message for f in findings)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (
            lambda text: text.replace(
                'typeCheckingMode = "strict"', 'typeCheckingMode = "basic"'
            ),
            "tool.pyright.typeCheckingMode",
        ),
        (
            lambda text: text.replace(
                'addopts = "-ra --import-mode=importlib"', 'addopts = "-ra"'
            ),
            "tool.pytest.ini_options.addopts",
        ),
        (
            lambda text: text.replace('"rn-forge-kiln"]', "]"),
            "dependency-groups.dev",
        ),
    ],
    ids=["pyright", "pytest", "dependency-groups"],
)
def test_s4_3_1_property5_each_rule_warns_on_its_violation(
    repo, mutation, expected
) -> None:
    findings = checks.run(
        repo(**{"pyproject.toml": mutation(COMPLIANT)}), only=pyproject.NAME
    )
    assert findings, "the rule accepted its own violation"
    assert all(f.severity is Severity.WARNING for f in findings)
    assert any(expected in f.message for f in findings)


@pytest.mark.parametrize("archetype", ["python-app", "python-tool"])
def test_s4_3_1_property5_passes_on_the_golden_rendered_output(archetype: str) -> None:
    root = GOLDEN / archetype
    assert pyproject.check(KilnConfig.load(root), root) == []


def test_s4_3_1_property5_passes_on_the_golden_lib_workspace() -> None:
    root = GOLDEN / "python-lib"
    assert pyproject.check(KilnConfig.load(root), root) == []
