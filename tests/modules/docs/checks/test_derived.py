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
EPIC = "# E1 — Epic\n\n" + TABLE + "| **State** | New |\n"
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
    assert _codes(root) == [
        "docs.board-stale",
        "docs.scope-stale",
        "docs.features-stale",
        "docs.stories-stale",
    ]
    assert all("task docs:generate" in f.message for f in generate.stale(root))


def test_s13_2_2_generate_writes_the_regions_and_then_nothing_is_stale(repo) -> None:
    root = _specs(repo)
    written, findings = generate.generate(root)
    assert sorted(p.name for p in written) == [
        "F1.1-a.md",
        "index.md",
        "index.md",
        "index.md",
    ]
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


EPICS = "# Epics\n\n<!-- BEGIN derived epics -->\n<!-- END derived epics -->\n"


def test_s14_1_2_3_an_empty_epic_list_fence_is_stale_then_current(repo) -> None:
    root = _specs(repo, **{"docs__specs__epics__index.md": EPICS})
    assert "docs.epics-stale" in _codes(root)
    generate.generate(root)
    assert generate.stale(root) == []
    assert "E1\u2013E10" in (root / "docs/specs/epics/index.md").read_text("utf-8")


def test_s14_1_2_3_a_missing_epics_fence_is_reported_and_left_alone(repo) -> None:
    root = _specs(repo, **{"docs__specs__epics__index.md": "# Epics\n"})
    page = root / "docs" / "specs" / "epics" / "index.md"
    assert "docs.epics-markers" in _codes(root)
    _, findings = generate.generate(root)
    assert "docs.epics-markers" in [f.code for f in findings]
    assert page.read_text("utf-8") == "# Epics\n"
    message = next(f for f in findings if f.code == "docs.epics-markers").message
    assert message == "has no complete derived epics fence"


def test_s14_1_2_4_a_tree_without_an_epic_list_reports_nothing_new(repo) -> None:
    root = _specs(repo)
    assert not any(code.startswith("docs.epics") for code in _codes(root))


STORIES = "<!-- BEGIN derived stories -->\n<!-- END derived stories -->"
STORY = "\n## S1.1.1 \u2014 One\n\n**State:** New\n"


def _feature_page(root: Path) -> Path:
    return root / "docs" / "specs" / "epics" / "E1-x" / "F1.1-a.md"


def test_s14_2_1_3_a_feature_without_a_fence_gets_one_after_its_table(repo) -> None:
    root = _specs(repo, **{"docs__specs__epics__E1-x__F1.1-a.md": FEATURE + STORY})
    assert "docs.stories-stale" in _codes(root)
    generate.generate(root)
    text = _feature_page(root).read_text("utf-8")
    table_end = text.index("| **Predecessors** | none |\n") + len(
        "| **Predecessors** | none |\n"
    )
    assert text[table_end:].startswith("\n" + STORIES.split("\n")[0] + "\n")
    assert "[S1.1.1 \u2014 One](#s111-one)" in text
    assert generate.stale(root) == []
    assert generate.generate(root) == ([], [])


def test_s14_2_1_3_a_moved_fence_is_rewritten_where_it_is(repo) -> None:
    body = FEATURE + "\nProse.\n\n" + STORIES + "\n" + STORY
    root = _specs(repo, **{"docs__specs__epics__E1-x__F1.1-a.md": body})
    generate.generate(root)
    text = _feature_page(root).read_text("utf-8")
    assert text.index("Prose.") < text.index("<!-- BEGIN derived stories -->")
    assert text.count("BEGIN derived stories") == 1


def test_s14_2_1_4_half_a_stories_fence_is_reported_and_left_alone(repo) -> None:
    body = FEATURE + "\n<!-- BEGIN derived stories -->\n" + STORY
    root = _specs(repo, **{"docs__specs__epics__E1-x__F1.1-a.md": body})
    assert "docs.stories-markers" in _codes(root)
    _, findings = generate.generate(root)
    marker = next(f for f in findings if f.code == "docs.stories-markers")
    assert marker.message == "has an incomplete derived stories fence"
    assert _feature_page(root).read_text("utf-8") == body


def test_s14_2_1_a_feature_without_a_metadata_table_gets_no_fence(repo) -> None:
    root = _specs(repo, **{"docs__specs__epics__E1-x__F1.1-a.md": "# F1.1\n" + STORY})
    generate.generate(root)
    assert "derived stories" not in _feature_page(root).read_text("utf-8")
    assert not any("stories" in code for code in _codes(root))


def _epic_page(root: Path) -> Path:
    return root / "docs" / "specs" / "epics" / "E1-x" / "index.md"


def test_s14_2_2_an_epic_with_feature_files_gets_the_features_region(repo) -> None:
    root = _specs(repo)
    assert "docs.features-stale" in _codes(root)
    generate.generate(root)
    text = _epic_page(root).read_text("utf-8")
    assert text.index("| **State** | New |") < text.index("BEGIN derived features")
    assert "| [F1.1 \u2014 A](F1.1-a.md) | New | release-1 | \u2014 |" in text
    assert generate.stale(root) == []
    assert generate.generate(root) == ([], [])


def test_s14_2_2_an_epic_without_feature_files_gets_no_fence(repo) -> None:
    root = repo(
        docs="mkdocs",
        **{
            "docs__specs__index.md": SPECS_INDEX,
            "docs__specs__epics__E1-x__index.md": EPIC,
        },
    )
    generate.generate(root)
    assert "derived features" not in _epic_page(root).read_text("utf-8")


def test_s14_2_2_half_a_features_fence_is_reported_and_left_alone(repo) -> None:
    body = EPIC + "\n<!-- END derived features -->\n"
    root = _specs(repo, **{"docs__specs__epics__E1-x__index.md": body})
    assert "docs.features-markers" in _codes(root)
    _, findings = generate.generate(root)
    marker = next(f for f in findings if f.code == "docs.features-markers")
    assert marker.message == "has an incomplete derived features fence"
    assert _epic_page(root).read_text("utf-8") == body
