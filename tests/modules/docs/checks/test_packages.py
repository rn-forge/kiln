"""`docs-structure` holds package docs sites to their shape (kiln ADR-0008)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.checks import structure
from rn_forge.kiln.modules.docs.packages import check_packages

GOLDEN = Path(__file__).parents[2].parent / "fixtures" / "golden"
PKG = "packages/alpha"
TABLE = '\n[archetype.python-lib]\npackages = ["packages/alpha"]\n'
MKDOCS = "site_name: alpha\nnav:\n  - Home: index.md\n  - Changelog: changelog.md\n"
URLS = "\n".join(
    f'{key} = "https://example.org/{key}"'
    for key in ("Documentation", "Source", "Changelog", "Issues")
)
GOOD = {
    f"{PKG}/mkdocs.yml": MKDOCS,
    f"{PKG}/docs/index.md": "# Alpha\n",
    f"{PKG}/docs/guides/usage.md": "# Usage\n",
    f"{PKG}/docs/changelog.md": f'--8<-- "{PKG}/CHANGELOG.md"\n',
    f"{PKG}/CHANGELOG.md": (
        "# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-09-26\n"
    ),
    f"{PKG}/pyproject.toml": f"[project]\nname = 'alpha'\n[project.urls]\n{URLS}\n",
    f"{PKG}/README.md": "# alpha\n\n[docs](https://example.org/docs)\n",
    "pyproject.toml": f"[tool.uv.workspace]\nmembers = ['{PKG}']\n",
}


def _lib(repo, **overrides: str | None) -> Path:
    files = {**GOOD, **overrides}
    root = repo(
        archetype="python-lib",
        docs="mkdocs",
        **{k.replace("/", "__"): v for k, v in files.items() if v is not None},
    )
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(config.read_text(encoding="utf-8") + TABLE, encoding="utf-8")
    return root


def _codes(root: Path) -> list[str]:
    return [f.code for f in check_packages(root, KilnConfig.load(root))]


def test_s11_2_3_0_a_well_formed_package_reports_nothing(repo) -> None:
    assert _codes(_lib(repo)) == []


CASES = {
    "docs.package-missing-mkdocs": {f"{PKG}/mkdocs.yml": None},
    "docs.package-missing-index": {f"{PKG}/docs/index.md": None},
    "docs.package-missing-guides": {f"{PKG}/docs/guides/usage.md": None},
    "docs.kebab-case": {f"{PKG}/docs/guides/Bad_Name.md": "# Bad\n"},
    "docs.package-governance-area": {f"{PKG}/docs/adr/index.md": "# ADR\n"},
    "docs.package-changelog": {
        f"{PKG}/CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n\n## 0.1.0\n"
    },
    "docs.package-changelog-page": {f"{PKG}/docs/changelog.md": "# Changelog\n"},
    "docs.package-urls": {
        f"{PKG}/pyproject.toml": "[project]\nname = 'alpha'\n[project.urls]\n"
        + URLS.replace('"https://example.org/Source"', '"http://example.org"')
    },
    "docs.package-readme-relative-link": {
        f"{PKG}/README.md": "# alpha\n\n[docs](docs/index.md)\n"
    },
    "docs.package-unlisted": {
        "pyproject.toml": "[tool.uv.workspace]\nmembers = ['packages/*']\n",
        "packages/stray/pyproject.toml": "[project]\nname = 'stray'\n",
    },
}


@pytest.mark.parametrize("code", CASES)
def test_s11_2_3_1_each_code_has_a_fixture_reporting_only_it(repo, code: str) -> None:
    root = _lib(repo, **CASES[code])
    assert _codes(root) == [code]


def test_s11_2_3_1_docs_structure_runs_the_package_checks(repo) -> None:
    root = _lib(repo, **CASES["docs.package-missing-index"])
    found = [f.code for f in checks.run(root, only=structure.NAME)]
    assert "docs.package-missing-index" in found


def test_s11_2_3_1_changelog_nav_must_name_the_page(repo) -> None:
    root = _lib(
        repo, **{f"{PKG}/mkdocs.yml": "site_name: alpha\nnav:\n  - Home: index.md\n"}
    )
    assert _codes(root) == ["docs.package-changelog-page"]


def test_s11_2_3_1_a_changelog_needs_an_unreleased_heading(repo) -> None:
    root = _lib(
        repo, **{f"{PKG}/CHANGELOG.md": "# Changelog\n\n## [0.1.0] - 2026-09-26\n"}
    )
    assert _codes(root) == ["docs.package-changelog"]


def test_s11_2_3_1_a_generated_reference_is_not_naming_checked(repo) -> None:
    root = _lib(repo, **{f"{PKG}/docs/reference/Odd_Name.md": "# Odd\n"})
    assert _codes(root) == []


def test_s11_2_3_2_the_python_lib_golden_reports_none(repo) -> None:
    root = GOLDEN / "python-lib"
    assert check_packages(root, KilnConfig.load(root)) == []


def test_s11_2_3_3_an_app_package_with_docs_is_not_allowed(repo) -> None:
    root = repo(
        archetype="python-app",
        docs="mkdocs",
        **{
            "pyproject.toml": "[tool.uv.workspace]\nmembers = ['packages/*']\n",
            "packages__core__docs__index.md".replace("__", "/"): "# Core\n",
        },
    )
    findings = check_packages(root, KilnConfig.load(root))
    assert [f.code for f in findings] == ["docs.package-docs-not-allowed"]
    assert findings[0].message == (
        "package docs sites are python-lib only (kiln ADR-0008); "
        "document packages/core in the root site"
    )


def test_s11_2_3_3_an_app_package_without_docs_is_fine(repo) -> None:
    root = repo(
        archetype="python-app",
        docs="mkdocs",
        **{
            "pyproject.toml": "[tool.uv.workspace]\nmembers = ['packages/*']\n",
            "packages/core/pyproject.toml": "[project]\nname = 'core'\n",
        },
    )
    assert check_packages(root, KilnConfig.load(root)) == []
