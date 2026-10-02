"""`docs-generate` fails when `mkdocs.yml`'s derived nav is stale."""

from __future__ import annotations

from pathlib import Path

from rn_forge.kiln import checks
from rn_forge.kiln.modules.docs import generate
from rn_forge.kiln.modules.docs.checks import derived

MKDOCS = """\
site_name: example
nav:
  # BEGIN derived nav
  - Home: index.md
  # END derived nav
"""


def _site(repo, **extra: str):
    return repo(
        docs="mkdocs",
        **{
            "mkdocs.yml": MKDOCS,
            "docs/index.md": "# Example\n",
            "docs/_areas.yml": "areas:\n  - key: guides\n",
            "docs/guides/index.md": "# Guides\n",
            **extra,
        },
    )


def test_s13_1_1_1_a_stale_nav_is_a_finding(repo) -> None:
    findings = checks.run(_site(repo), only=derived.NAME)
    assert [f.code for f in findings] == ["docs.nav-stale"]
    assert "task docs:generate" in findings[0].message


def test_s13_1_1_1_a_repo_without_an_mkdocs_site_is_not_checked(repo) -> None:
    assert checks.run(repo(docs="none"), only=derived.NAME) == []


TABLE = "|  |  |\n| -- | -- |\n"
BOARD = "<!-- BEGIN derived board -->\n<!-- END derived board -->\n"
SCOPE = "## Scope\n\n<!-- BEGIN derived scope -->\n<!-- END derived scope -->\n"
SPECS_INDEX = f"# Specs\n\n{BOARD}"
EPIC = (
    "# E1 — Epic\n\n" + TABLE + "| **State** | New |\n\n"
    "| ID | State |\n| -- | -- |\n| [F1.1](F1.1-a.md) | New |\n"
)
FEATURE = (
    "# F1.1 — A\n\n" + TABLE + "| **State** | New |\n| **Parent** | E1 |\n"
    "| **Iteration** | [Release 1](../../../releases/release-1/index.md) |\n"
    "| **Predecessors** | none |\n"
)
RELEASE = "# Release 1\n\n" + TABLE + "| **Status** | planned |\n\n" + SCOPE


def _specs(repo, **extra: str):
    return repo(
        docs="mkdocs",
        **{
            "docs__specs__index.md": SPECS_INDEX,
            "docs__specs__epics__E1-x__index.md": EPIC,
            "docs__specs__epics__E1-x__F1.1-a.md": FEATURE,
            "docs__releases__release-1__index.md": RELEASE,
            **extra,
        },
    )


def _codes(root: Path) -> list[str]:
    return [f.code for f in generate.stale(root)]


def test_s13_2_2_an_unwritten_board_and_scope_are_stale(repo) -> None:
    root = _specs(repo)
    assert _codes(root) == ["docs.board-stale", "docs.scope-stale"]
    assert all("task docs:generate" in f.message for f in generate.stale(root))


def test_s13_2_2_generate_writes_the_regions_and_then_nothing_is_stale(repo) -> None:
    root = _specs(repo)
    written, findings = generate.generate(root)
    assert sorted(p.name for p in written) == ["index.md", "index.md"]
    assert findings == []
    assert generate.stale(root) == []
    assert generate.generate(root) == ([], [])


def test_s13_2_2_a_hand_edited_board_row_is_stale(repo) -> None:
    root = _specs(repo)
    generate.generate(root)
    index = root / "docs" / "specs" / "index.md"
    index.write_text(
        index.read_text(encoding="utf-8").replace("planned", "shipped"),
        encoding="utf-8",
    )
    assert _codes(root) == ["docs.board-stale"]
    generate.generate(root)
    assert generate.stale(root) == []


def test_s13_2_2_a_tree_without_the_board_fence_has_no_work_findings(repo) -> None:
    root = _specs(
        repo,
        **{
            "docs__specs__index.md": "# Specs\n",
            "docs__specs__epics__E1-x__index.md": "# Broken\n",
            "docs__releases__release-1__index.md": "# R\n",
        },
    )
    assert generate.stale(root) == []
    assert generate.generate(root) == ([], [])


def test_s13_2_2_a_release_without_a_scope_fence_is_reported_and_left_alone(
    repo,
) -> None:
    release = "# Release 1\n\n" + TABLE + "| **Status** | planned |\n"
    root = _specs(repo, **{"docs__releases__release-1__index.md": release})
    page = root / "docs" / "releases" / "release-1" / "index.md"
    before = page.read_bytes()
    assert "docs.scope-markers" in _codes(root)
    _, findings = generate.generate(root)
    assert [f.code for f in findings] == ["docs.scope-markers"]
    assert page.read_bytes() == before


def test_s13_2_2_one_board_marker_is_reported_and_nothing_is_written(repo) -> None:
    root = _specs(
        repo, **{"docs__specs__index.md": "# Specs\n\n<!-- BEGIN derived board -->\n"}
    )
    index = root / "docs" / "specs" / "index.md"
    before = index.read_bytes()
    assert _codes(root) == ["docs.board-markers"]
    written, findings = generate.generate(root)
    assert written == []
    assert [f.code for f in findings] == ["docs.board-markers"]
    assert index.read_bytes() == before


def test_s13_2_2_metadata_findings_are_reported_alongside_stale_regions(repo) -> None:
    root = _specs(repo, **{"docs__specs__epics__E1-x__index.md": "# E1\n"})
    assert "docs.work-no-metadata" in _codes(root)
    assert generate.generate(root)[1][0].code == "docs.work-no-metadata"


def test_s13_2_2_the_check_reports_the_regions(repo) -> None:
    assert [f.code for f in checks.run(_specs(repo), only=derived.NAME)][:1] == [
        "docs.board-stale"
    ]


def _lib(repo, archetype: str, table: str):
    root = _site(
        repo,
        **{
            "docs/_areas.yml": "areas:\n  - key: packages\n    nav: include\n",
            "mkdocs.yml": MKDOCS,
        },
    )
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'archetype = "python-app"', f'archetype = "{archetype}"'
        )
        + table,
        encoding="utf-8",
    )
    return root


def test_s11_1_1_2_the_nav_check_passes_python_lib_packages(repo) -> None:
    root = _lib(
        repo, "python-lib", '\n[archetype.python-lib]\npackages = ["packages/a"]\n'
    )
    assert generate.generate(root, ("packages/a",))[0] == [root / "mkdocs.yml"]
    assert "!include packages/a/mkdocs.yml" in (root / "mkdocs.yml").read_text()
    assert checks.run(root, only=derived.NAME) == []


def test_s11_1_1_4_a_web_archetypes_api_dir_is_not_a_package_site(repo) -> None:
    root = _lib(repo, "python-web-api", "")
    generate.generate(root)
    assert checks.run(root, only=derived.NAME) == []
    assert "!include" not in (root / "mkdocs.yml").read_text()
