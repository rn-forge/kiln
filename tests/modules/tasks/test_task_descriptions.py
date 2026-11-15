"""Task descriptions by archetype, and what each says runs."""

from __future__ import annotations
import pytest
from pathlib import Path
from rn_forge.kiln.modules.core import cycle
from tests.modules.tasks.support import (
    _load,
    _node_lib_root,
    _node_root,
    _root,
    _web_root,
)


PYTHON_DESCS = {
    "setup": "Install the project and its dev + docs dependency groups.",
    "lint": (
        "Every lint — Python, imports, Markdown, TOML and YAML formatting, kiln's checks "
        "(generated files, task layout, CI, dependencies, docs), workflow security, "
        "dependency vulnerabilities, dependency licences."
    ),
    "format": "Format Python code, TOML, YAML and Markdown prose in place.",
    "typecheck": "Static type-check the package in pyright strict mode.",
    "test": "Run the pytest suite, or pass pytest arguments after --.",
    "test:coverage": (
        "Run the pytest suite with an XML coverage report (used by CI/Sonar)."
    ),
    "build": "Build the wheel and sdist into dist/.",
    "version": "Print the package version from pyproject.toml.",
}


NODE_LIB_DESCS = {
    "setup": "Install the pnpm workspace and the docs tooling.",
    "lint": (
        "Every lint — Nx projects, Prettier formatting, Markdown, TOML and YAML "
        "formatting, kiln's checks, workflow security, dependency vulnerabilities, dependency licences."
    ),
    "format": "Format Prettier-formatted files, TOML, YAML and Markdown prose in place.",
    "typecheck": "Type-check every project through its Angular build.",
    "test": "Run every project's tests with Nx.",
    "test:coverage": "Run every project's tests, writing lcov reports to coverage/.",
    "build": "Build every project with Nx.",
    "version": (
        "Print the publishable projects' version, or bump it, write its "
        "CHANGELOG.md section and format it (pass -- patch|minor|major|x.y.z)."
    ),
}


WEB_APP_DESCS = {
    **PYTHON_DESCS,
    "lint": (
        "Every lint — Python, imports, the frontend's Nx lint, Prettier formatting, "
        "Markdown, TOML and YAML formatting, kiln's checks (generated files, task layout, "
        "CI, dependencies, docs), workflow security, dependency vulnerabilities, "
        "dependency licences."
    ),
    "format": (
        "Format Python code, Prettier-formatted files, TOML, YAML and Markdown prose in "
        "place."
    ),
    "typecheck": (
        "Type-check the API in pyright strict mode and the frontend through its "
        "Angular build."
    ),
    "test": (
        "Run the API's pytest suite and the frontend's tests; pytest arguments "
        "after -- go to the API suite."
    ),
    "test:coverage": ("Run both test suites with coverage reports (used by CI/Sonar)."),
    "build": "Build the API's wheel and sdist, and the frontend.",
}


def _descs(root: Path) -> dict[str, str]:
    tasks = _load(root, "Taskfile.yml")["tasks"]
    return {name: tasks[name]["desc"] for name in NODE_LIB_DESCS}


def test_s9_2_9_4_node_lib_descs_are_the_node_table(tmp_path: Path) -> None:
    root = _node_lib_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    assert _descs(root) == NODE_LIB_DESCS


def test_s9_2_9_4_python_web_app_descs_name_both_halves(tmp_path: Path) -> None:
    root = _node_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    assert _descs(root) == WEB_APP_DESCS


@pytest.mark.parametrize("archetype", ["python-app", "python-tool", "python-web-api"])
def test_s9_2_9_5_other_python_cells_keep_their_descs(
    tmp_path: Path, archetype: str
) -> None:
    root = (
        _root(tmp_path, archetype)
        if archetype != "python-web-api"
        else _web_root(tmp_path, "python-web-api", "fastapi")
    )
    cycle.apply(root, home=tmp_path / "home")
    assert _descs(root) == PYTHON_DESCS


def test_s9_2_9_5_python_lib_keeps_its_descs(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    cycle.apply(root, home=tmp_path / "home")
    expected = {
        **PYTHON_DESCS,
        "build": (
            "Build one package's wheel and sdist into dist/ (pass -- <package>), "
            "or every package's."
        ),
        "version": "Print one package's version (pass -- <package>), or every package's.",
        "typecheck": "Type-check each package in pyright strict mode.",
        "test": (
            "Run each package's pytest suite, or one package's with pytest "
            "arguments (pass -- <package> [args])."
        ),
        "test:coverage": (
            "Run each package's tests with coverage, combined into one XML report "
            "(used by CI/Sonar)."
        ),
    }
    assert _descs(root) == expected


LINT_TAIL = "workflow security, dependency vulnerabilities"


LINT_PYTHON = (
    "Every lint — Python, imports, Markdown, TOML and YAML formatting, kiln's checks "
    "(generated files, task layout, CI, dependencies, docs), " + LINT_TAIL
)


LINT_WEB_APP = (
    "Every lint — Python, imports, the frontend's Nx lint, Prettier formatting, "
    "Markdown, TOML and YAML formatting, kiln's checks (generated files, task layout, "
    "CI, dependencies, docs), " + LINT_TAIL
)


LINT_NODE_LIB = (
    "Every lint — Nx projects, Prettier formatting, Markdown, TOML and YAML "
    "formatting, kiln's checks, " + LINT_TAIL
)


LINT_CELLS = (
    ("python-app", LINT_PYTHON),
    ("python-tool", LINT_PYTHON),
    ("python-lib", LINT_PYTHON),
    ("python-web-api", LINT_PYTHON),
    ("python-web-app", LINT_WEB_APP),
    ("node-lib", LINT_NODE_LIB),
)


def _lint_root(tmp_path: Path, archetype: str, extra: str = "") -> Path:
    if archetype == "python-web-api":
        return _web_root(tmp_path, archetype, "fastapi", extra=extra)
    if archetype == "python-web-app":
        return _web_root(
            tmp_path, archetype, "fastapi", extra=f'frontend = "angular"{extra}'
        )
    return _root(tmp_path, archetype, extra=extra)


@pytest.mark.parametrize(
    ("archetype", "lead"), LINT_CELLS, ids=[a for a, _ in LINT_CELLS]
)
def test_s17_1_4_1_lint(tmp_path: Path, archetype: str, lead: str) -> None:
    root = _lint_root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    assert _load(root, "Taskfile.yml")["tasks"]["lint"]["desc"] == (
        lead + ", dependency licences."
    )


@pytest.mark.parametrize(
    ("archetype", "lead"), LINT_CELLS, ids=[a for a, _ in LINT_CELLS]
)
def test_s17_1_4_2_lint_without_licences(
    tmp_path: Path, archetype: str, lead: str
) -> None:
    root = _lint_root(tmp_path, archetype, extra="\n[ci.checks]\nlicenses = false\n")
    cycle.apply(root, home=tmp_path / "home")
    assert _load(root, "Taskfile.yml")["tasks"]["lint"]["desc"] == lead + "."


def test_s17_1_4_3_workspace_verbs(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    cycle.apply(root, home=tmp_path / "home")
    tasks = _load(root, "Taskfile.yml")["tasks"]
    assert (
        tasks["typecheck"]["desc"] == "Type-check each package in pyright strict mode."
    )
    assert tasks["test"]["desc"] == (
        "Run each package's pytest suite, or one package's with pytest "
        "arguments (pass -- <package> [args])."
    )
    assert tasks["test:coverage"]["desc"] == (
        "Run each package's tests with coverage, combined into one XML report "
        "(used by CI/Sonar)."
    )
