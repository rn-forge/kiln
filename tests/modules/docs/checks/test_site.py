"""`docs-site` follows links into package sites and holds package sites to themselves."""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.kiln import checks
from rn_forge.kiln.modules.docs.checks import site
from rn_forge.kiln.modules.docs.site import check_site

PACKAGES = ("packages/alpha", "packages/beta")
TABLE = '\n[archetype.python-lib]\npackages = ["packages/alpha", "packages/beta"]\n'


def _repo(repo, root_page: str = "# Root\n", alpha_page: str = "", **extra: str):
    root = repo(
        archetype="python-lib",
        docs="mkdocs",
        **{
            "mkdocs.yml": "site_name: root\nnav:\n  - Home: index.md\n",
            "docs/index.md": root_page,
            "packages/alpha/mkdocs.yml": (
                "site_name: alpha\nnav:\n  - Home: index.md\n"
            ),
            "packages/alpha/docs/index.md": f"# Alpha\n\n## Usage\n\n{alpha_page}",
            "packages/beta/mkdocs.yml": "site_name: beta\nnav:\n  - Home: index.md\n",
            "packages/beta/docs/index.md": "# Beta\n",
            **extra,
        },
    )
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(config.read_text(encoding="utf-8") + TABLE, encoding="utf-8")
    return root


def _codes(root: Path) -> list[str]:
    return [f.code for f in check_site(root, packages=PACKAGES)]


def test_s11_1_2_1_a_root_link_into_a_package_page_resolves(repo) -> None:
    root = _repo(repo, "# Root\n\n[usage](alpha/index.md#usage)\n")
    assert check_site(root, packages=PACKAGES) == []
    assert checks.run(root, only=site.NAME) == []


def test_s11_1_2_2_a_root_link_to_a_missing_package_page_is_broken(repo) -> None:
    root = _repo(repo, "# Root\n\n[x](alpha/missing.md)\n")
    assert _codes(root) == ["docs.broken-link"]
    assert [f.code for f in checks.run(root, only=site.NAME)] == ["docs.broken-link"]


def test_s11_1_2_2_a_root_link_to_a_missing_package_anchor_is_broken(repo) -> None:
    root = _repo(repo, "# Root\n\n[x](alpha/index.md#nope)\n")
    assert _codes(root) == ["docs.broken-anchor"]
    assert [f.code for f in checks.run(root, only=site.NAME)] == ["docs.broken-anchor"]


@pytest.mark.parametrize("link", ["../../beta/docs/index.md", "../../../docs/index.md"])
def test_s11_1_2_3_a_package_link_that_escapes_is_an_error(repo, link: str) -> None:
    root = _repo(repo, alpha_page=f"[out]({link})\n")
    assert (root / "packages/alpha/docs" / link).resolve().exists()
    findings = check_site(root, packages=PACKAGES)
    assert [f.code for f in findings] == ["docs.package-link-escapes"]
    assert findings[0].message == f"links outside packages/alpha/docs: {link}"


def test_s11_1_2_4_an_unreachable_package_page_is_an_orphan(repo) -> None:
    root = _repo(repo, **{"packages/alpha/docs/lonely.md": "# Lonely\n"})
    findings = check_site(root, packages=PACKAGES)
    assert [f.code for f in findings] == ["docs.orphan-page"]
    assert "packages/alpha/docs/lonely.md" in str(findings[0].path)


def test_s11_1_2_4_a_package_nav_naming_a_missing_page_is_reported(repo) -> None:
    root = _repo(
        repo,
        **{
            "packages/beta/mkdocs.yml": (
                "site_name: beta\nnav:\n  - Home: index.md\n  - Gone: gone.md\n"
            )
        },
    )
    assert _codes(root) == ["docs.nav-missing-page"]


def test_s11_1_2_5_without_packages_a_package_name_is_not_a_mount(repo) -> None:
    root = _repo(repo, "# Root\n\n[x](alpha/index.md)\n")
    assert [f.code for f in check_site(root)] == ["docs.broken-link"]


def test_s11_1_2_5_only_a_python_lib_has_package_sites(repo) -> None:
    root = _repo(repo, "# Root\n\n[x](alpha/index.md)\n")
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("python-lib", "python-app"),
        encoding="utf-8",
    )
    assert [f.code for f in checks.run(root, only=site.NAME)] == ["docs.broken-link"]
