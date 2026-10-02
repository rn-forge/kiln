"""`docs-structure` holds a repo's docs tree to kiln's policy.

The mechanism is covered in `tests/modules/docs/test_docs.py`; this proves the
check reaches it, and that kiln's own docs pass the policy kiln ships.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.checks import structure
from rn_forge.kiln.modules.docs.policy import POLICY
from rn_forge.kiln.modules.docs.structure import check_structure

ROOT = Path(__file__).resolve().parents[4]


def test_kiln_docs_pass_the_policy() -> None:
    assert [str(f) for f in checks.run(ROOT, only=structure.NAME)] == []


def test_a_repo_without_an_mkdocs_site_is_not_checked(repo) -> None:
    root = repo(docs="none")
    assert structure.check(KilnConfig.load(root), root) == []


def test_s11_1_1_3_an_include_area_needs_no_directory(tmp_path: Path) -> None:
    from rn_forge.kiln.modules.docs.areas import Area
    from rn_forge.kiln.modules.docs.structure import _check_areas

    areas = [Area(key="packages", title="Packages", nav="include")]
    assert _check_areas(areas, tmp_path) == []


_STRUCTURE_PAGE = "# Root\n\n[x]({link})\n"


def _packages_repo(repo, link: str) -> Path:
    root = repo(
        archetype="python-lib",
        docs="mkdocs",
        **{
            "docs/_areas.yml": "areas:\n  - key: packages\n    nav: include\n",
            "docs/index.md": _STRUCTURE_PAGE.format(link=link),
            "packages/alpha/mkdocs.yml": "site_name: alpha\n",
            "packages/alpha/docs/index.md": "# Alpha\n\n## Usage\n",
            "packages/beta/mkdocs.yml": "site_name: beta\n",
            "packages/beta/docs/index.md": "# Beta\n",
        },
    )
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + '\n[archetype.python-lib]\npackages = ["packages/alpha", "packages/beta"]\n',
        encoding="utf-8",
    )
    return root


def _link_codes(root: Path) -> list[str]:
    return [
        f.code
        for f in checks.run(root, only=structure.NAME)
        if f.code in {"docs.broken-link", "docs.broken-anchor"}
    ]


def test_s11_1_2_1_a_root_link_into_a_package_page_resolves(repo) -> None:
    assert _link_codes(_packages_repo(repo, "alpha/index.md#usage")) == []


def test_s11_1_2_2_a_root_link_to_a_missing_package_page_is_broken(repo) -> None:
    assert _link_codes(_packages_repo(repo, "alpha/missing.md")) == ["docs.broken-link"]


def test_s11_1_2_2_a_root_link_to_a_missing_package_anchor_is_broken(repo) -> None:
    assert _link_codes(_packages_repo(repo, "alpha/index.md#nope")) == [
        "docs.broken-anchor"
    ]


def test_s11_1_2_5_without_packages_a_package_name_is_not_a_mount(repo) -> None:
    root = _packages_repo(repo, "alpha/index.md")
    findings = check_structure(root, root / "docs", POLICY)
    assert [f.code for f in findings if f.code.endswith("link")] == ["docs.broken-link"]


def _excluding_repo(repo, old: str = "", new: str = "", underscore: str = "") -> Path:
    return repo(
        archetype="python-app",
        docs="mkdocs",
        **{
            "mkdocs.yml": "site_name: root\nexclude_docs: |\n  _*\n  plans/archive/\n",
            "docs/_areas.yml": "areas:\n  - key: packages\n    nav: include\n",
            "docs/index.md": "# Root\n",
            "docs/plans/new.md": f"# New\n\n{new}",
            "docs/plans/archive/old.md": f"# Old\n\n{old}",
            "docs/plans/archive/other.md": f"# Other\n\n{underscore}",
        },
    )


def _structure_codes(root: Path) -> list[str]:
    return [
        f.code
        for f in checks.run(root, only=structure.NAME)
        if f.code.startswith("docs.broken") or f.code == "docs.underscore-referenced"
    ]


def test_s11_1_3_1_a_broken_link_in_an_excluded_page_is_not_reported(repo) -> None:
    assert _structure_codes(_excluding_repo(repo, old="[x](gone.md)\n")) == []


def test_s11_1_3_1_the_same_link_in_a_shipping_page_is_broken(repo) -> None:
    root = _excluding_repo(repo, new="[x](gone.md)\n")
    assert _structure_codes(root) == ["docs.broken-link"]


def test_s11_1_3_an_excluded_page_may_link_an_underscore_page(repo) -> None:
    root = _excluding_repo(repo, underscore="[x](_inc.md)\n")
    assert _structure_codes(root) == []
    (root / "docs/plans/new.md").write_text("[x](_inc.md)\n", encoding="utf-8")
    (root / "docs/plans/_inc.md").write_text("# Inc\n", encoding="utf-8")
    assert _structure_codes(root) == ["docs.underscore-referenced"]
