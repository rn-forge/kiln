"""`pyproject-tool-config` — doctor check 8a.

`pyproject.toml` is repo-owned; kiln never writes it (kiln ADR-0001). This
check only verifies that a defined subset of `[project]` identity fields,
`[tool.ruff*]`, `[tool.pyright]`, `[tool.pytest.ini_options]` and
`[dependency-groups]` match what the archetype expects (kiln ADR-0005), and
reports every mismatch at warning severity — a repo that disagrees is worth a
look, never a failed gate.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln import archetypes, documents
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.python.checks.rn_forge_deps import distribution

__all__ = ["CODE", "NAME", "check"]

NAME = "pyproject-tool-config"
CODE = "pyproject"

REQUIRES_PYTHON = ">=3.14"
PYTEST_ADDOPTS = "-ra --import-mode=importlib"
PYRIGHT_EXPECTED = {"typeCheckingMode": "strict", "reportMissingTypeStubs": False}
RUFF_TEST_IGNORES = {"S101", "D", "ANN", "PLR2004"}
DEV_GROUP_TOOLS = ("import-linter", "pyright", "pytest", "ruff", "rn-forge-kiln")


def _mismatch(label: str, field: str, expected: object, actual: object) -> Finding:
    return Finding(
        f"{CODE}.tool-config",
        Severity.WARNING,
        f"[{field}] is {actual!r}, expected {expected!r}",
        path=label,
    )


def _check_identity(
    label: str, document: dict[str, object], config: KilnConfig
) -> list[Finding]:
    project = documents.table(document, "project")
    findings: list[Finding] = []
    expected_name = config.name
    actual_name = project.get("name")
    if actual_name != expected_name:
        findings.append(_mismatch(label, "project.name", expected_name, actual_name))
    actual_requires = project.get("requires-python")
    if actual_requires != REQUIRES_PYTHON:
        findings.append(
            _mismatch(
                label, "project.requires-python", REQUIRES_PYTHON, actual_requires
            )
        )
    return findings


def _check_pyright(label: str, document: dict[str, object]) -> list[Finding]:
    pyright = documents.table(document, "tool", "pyright")
    findings: list[Finding] = []
    for key, expected in PYRIGHT_EXPECTED.items():
        actual = pyright.get(key)
        if actual != expected:
            findings.append(_mismatch(label, f"tool.pyright.{key}", expected, actual))
    return findings


def _check_pytest(label: str, document: dict[str, object]) -> list[Finding]:
    options = documents.table(document, "tool", "pytest", "ini_options")
    actual = options.get("addopts")
    if actual != PYTEST_ADDOPTS:
        return [
            _mismatch(label, "tool.pytest.ini_options.addopts", PYTEST_ADDOPTS, actual)
        ]
    return []


def _check_ruff(label: str, document: dict[str, object]) -> list[Finding]:
    ignores = documents.table(document, "tool", "ruff", "lint", "per-file-ignores")
    for key, rules in ignores.items():
        if key.endswith("tests/*") and RUFF_TEST_IGNORES <= set(
            documents.strings(rules)
        ):
            return []
    return [
        _mismatch(
            label,
            "tool.ruff.lint.per-file-ignores",
            sorted(RUFF_TEST_IGNORES),
            sorted(
                {
                    rule
                    for rules in ignores.values()
                    for rule in documents.strings(rules)
                }
            ),
        )
    ]


def _check_dependency_groups(label: str, document: dict[str, object]) -> list[Finding]:
    dev = documents.strings(documents.table(document, "dependency-groups").get("dev"))
    declared = {distribution(requirement) for requirement in dev}
    missing = [name for name in DEV_GROUP_TOOLS if name not in declared]
    if missing:
        return [
            _mismatch(
                label,
                "dependency-groups.dev",
                sorted(DEV_GROUP_TOOLS),
                sorted(declared),
            )
        ]
    return []


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Compare every `pyproject.toml` in the repo against the archetype's expected values."""
    findings: list[Finding] = []
    for index, relative in enumerate(archetypes.pyproject_paths(config)):
        label = relative.as_posix()
        path = root / relative
        if not path.exists():
            continue
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        findings.extend(_check_pyright(label, document))
        findings.extend(_check_pytest(label, document))
        findings.extend(_check_ruff(label, document))
        if index == 0:
            findings.extend(_check_identity(label, document, config))
            findings.extend(_check_dependency_groups(label, document))
    return findings
