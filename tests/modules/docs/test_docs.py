"""Tests for rn_forge.kiln.modules.docs."""

from __future__ import annotations

import dataclasses
import re

import pytest

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.text.markdown import MarkdownUtils

from rn_forge.kiln.modules.docs.areas import Area, load_areas
from rn_forge.kiln.modules.docs.nav import (
    NAV_BLOCK,
    build_nav,
    page_title,
    update_nav,
)
from rn_forge.kiln.modules.docs.policy import (
    DocsPolicy,
    NestedArea,
    NumberedArea,
    SequenceArea,
)
from rn_forge.kiln.modules.docs.site import check_site
from rn_forge.kiln.modules.docs.structure import check_structure

AREAS = """\
areas:
  - key: adr
    title: Decisions
    nav: children
  - key: guides
    title: Guides
  - key: api
    title: API Reference
    nav: index-only
    generated: true
"""

MKDOCS = """\
site_name: demo
nav:
  # BEGIN derived nav
  # END derived nav
"""


# The rn-forge policy, as a test fixture. It lives here rather than in the
# library on purpose: `docs/structure.py` must not know what an ADR is.
POLICY = DocsPolicy(
    instruction_files=("CLAUDE.md", "AGENTS.md"),
    numbered=NumberedArea(
        path="adr",
        filename=re.compile(r"^(\d{4})-[a-z0-9-]+\.md$"),
        statuses=re.compile(r"^(proposed|accepted|deprecated|superseded by adr-\d{4})"),
        label="ADR",
        shape="<nnnn>-<slug>.md",
    ),
    sequences=(
        SequenceArea(
            path="releases",
            dirname=re.compile(r"^release-(\d+)$"),
            shape="release-<n>/",
        ),
    ),
    nested=(
        NestedArea(
            path="specs/epics",
            dirname=re.compile(r"^E(\d+)-[a-z0-9-]+$"),
            dir_shape="E<n>-<slug>/",
            page_glob="F*.md",
            page_name=re.compile(r"^F(\d+)\.(\d+)-[a-z0-9-]+\.md$"),
            page_shape="F<n>.<m>-<slug>.md",
        ),
    ),
    ideas="specs/ideas",
)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path):
    """A minimal but valid repo: two areas, an instruction file, a nav fence."""
    docs = tmp_path / "docs"
    write(docs / "_areas.yml", AREAS)
    write(docs / "_structure.md", "# Structure\n")
    write(docs / "index.md", "# Docs\n\n- [Guides](guides/index.md)\n")
    write(docs / "adr/_structure.md", "# ADR structure\n")
    write(docs / "adr/index.md", "# Decisions\n\n- [First](0001-first.md)\n")
    write(docs / "adr/0001-first.md", "# First\n\n**Status:** accepted\n")
    write(docs / "guides/_structure.md", "# Guide structure\n")
    write(docs / "guides/index.md", "# Guides\n\n- [Setup](setup.md)\n")
    write(docs / "guides/setup.md", "# Setup\n")
    write(
        tmp_path / "CLAUDE.md",
        "# Repo\n\n- [rules](docs/_structure.md)\n- [docs](docs/index.md)\n",
    )
    write(tmp_path / "AGENTS.md", "See [CLAUDE.md](CLAUDE.md).\n")
    write(tmp_path / "mkdocs.yml", MKDOCS)
    return tmp_path


def codes(findings):
    return sorted(finding.code for finding in findings)


class TestAreas:
    def test_loads_declared_areas(self, repo):
        areas = load_areas(repo / "docs")
        assert [area.key for area in areas] == ["adr", "guides", "api"]
        assert areas[2].generated is True
        assert areas[2].nav == "index-only"

    def test_missing_manifest_raises(self, tmp_path):
        with pytest.raises(AppException):
            load_areas(tmp_path)

    def test_unknown_nav_value_raises(self, tmp_path):
        write(tmp_path / "_areas.yml", "areas:\n  - key: guides\n    nav: sideways\n")
        with pytest.raises(AppException):
            load_areas(tmp_path)

    def test_s11_1_1_1_an_include_area_loads(self, tmp_path):
        write(tmp_path / "_areas.yml", "areas:\n  - key: packages\n    nav: include\n")
        (area,) = load_areas(tmp_path)
        assert (area.key, area.nav, area.title) == ("packages", "include", "Packages")

    def test_s14_1_3_3_a_work_area_loads(self, tmp_path):
        write(tmp_path / "_areas.yml", "areas:\n  - key: specs\n    nav: work\n")
        (area,) = load_areas(tmp_path)
        assert (area.key, area.nav, area.title) == ("specs", "work", "Specs")

    def test_area_round_trips_through_dict(self, repo):
        for area in load_areas(repo / "docs"):
            assert Area.from_dict(area.as_dict()) == area

    def test_a_mistyped_field_names_the_manifest_and_the_field(self, tmp_path):
        write(
            tmp_path / "_areas.yml",
            "areas:\n  - key: guides\n    optional: sometimes\n",
        )
        with pytest.raises(AppException) as error:
            load_areas(tmp_path)
        assert "_areas.yml" in str(error.value)
        assert "optional" in str(error.value)

    def test_a_missing_key_is_rejected(self, tmp_path):
        write(tmp_path / "_areas.yml", "areas:\n  - title: Guides\n")
        with pytest.raises(AppException):
            load_areas(tmp_path)


class TestCheckStructure:
    def test_a_valid_tree_has_no_findings(self, repo):
        assert check_structure(repo, repo / "docs", POLICY) == []

    def test_missing_area_is_reported(self, repo):
        for path in (repo / "docs/guides").iterdir():
            path.unlink()
        (repo / "docs/guides").rmdir()
        assert "docs.missing-area" in codes(
            check_structure(repo, repo / "docs", POLICY)
        )

    def test_generated_area_need_not_exist(self, repo):
        assert not any(
            "api" in (finding.path or "")
            for finding in check_structure(repo, repo / "docs", POLICY)
        )

    def test_missing_structure_md_is_reported(self, repo):
        (repo / "docs/guides/_structure.md").unlink()
        assert "docs.missing-structure-md" in codes(
            check_structure(repo, repo / "docs", POLICY)
        )

    def test_non_kebab_page_is_reported(self, repo):
        write(repo / "docs/guides/Not_Kebab.md", "# x\n")
        assert "docs.kebab-case" in codes(check_structure(repo, repo / "docs", POLICY))

    def test_adr_pages_are_exempt_from_the_kebab_rule(self, repo):
        assert "docs.kebab-case" not in codes(
            check_structure(repo, repo / "docs", POLICY)
        )

    def test_adr_number_gap_is_reported(self, repo):
        write(repo / "docs/adr/0003-third.md", "# Third\n\n**Status:** accepted\n")
        assert "docs.number-gap" in codes(check_structure(repo, repo / "docs", POLICY))

    def test_adr_naming_is_reported(self, repo):
        write(repo / "docs/adr/first-decision.md", "**Status:** accepted\n")
        assert "docs.naming" in codes(check_structure(repo, repo / "docs", POLICY))

    def test_missing_adr_status_is_reported(self, repo):
        write(repo / "docs/adr/0001-first.md", "# First\n")
        assert "docs.status" in codes(check_structure(repo, repo / "docs", POLICY))

    def test_superseded_status_is_allowed(self, repo):
        write(
            repo / "docs/adr/0001-first.md",
            "# First\n\n**Status:** superseded by ADR-0002 \\\n",
        )
        assert "docs.status" not in codes(check_structure(repo, repo / "docs", POLICY))

    def test_broken_link_is_reported(self, repo):
        write(repo / "docs/guides/setup.md", "# Setup\n\n[gone](missing.md)\n")
        assert "docs.broken-link" in codes(check_structure(repo, repo / "docs", POLICY))

    def test_broken_anchor_is_reported(self, repo):
        write(repo / "docs/guides/setup.md", "# Setup\n\n[x](index.md#nope)\n")
        assert "docs.broken-anchor" in codes(
            check_structure(repo, repo / "docs", POLICY)
        )

    def test_underscore_page_reference_is_reported(self, repo):
        write(repo / "docs/guides/setup.md", "# Setup\n\n[s](_structure.md)\n")
        assert "docs.underscore-referenced" in codes(
            check_structure(repo, repo / "docs", POLICY)
        )

    def test_release_and_epic_naming(self, repo):
        write(repo / "docs/releases/rel1/index.md", "# r\n")
        write(repo / "docs/specs/epics/E1-thing/F1.a-bad.md", "# f\n")
        found = codes(check_structure(repo, repo / "docs", POLICY))
        assert found.count("docs.naming") == 2

    def test_missing_areas_manifest_is_one_finding(self, repo):
        (repo / "docs/_areas.yml").unlink()
        assert codes(check_structure(repo, repo / "docs", POLICY)) == [
            "docs.areas-manifest"
        ]

    def test_instruction_pointer_must_reach_the_rules(self, repo):
        write(repo / "AGENTS.md", "# Agents\n\nNothing useful here.\n")
        assert "docs.missing-docs-pointer" in codes(
            check_structure(repo, repo / "docs", POLICY)
        )

    def test_no_instruction_file_is_reported(self, repo):
        (repo / "CLAUDE.md").unlink()
        (repo / "AGENTS.md").unlink()
        assert codes(check_structure(repo, repo / "docs", POLICY)) == [
            "docs.missing-instruction-file"
        ]

    def test_s13_4_1_2_an_ideas_md_is_reported(self, repo):
        write(repo / "docs/specs/ideas.md", "# Ideas\n")
        found = [
            f
            for f in check_structure(repo, repo / "docs", POLICY)
            if f.code == "docs.ideas-moved"
        ]
        assert len(found) == 1
        assert (found[0].path or "").endswith("specs/ideas.md")
        assert found[0].message == "move it to specs/ideas/index.md"

    def test_s13_4_1_3_an_unlisted_idea_page_is_reported(self, repo):
        write(repo / "docs/specs/ideas/index.md", "# Ideas\n\n- [A](alpha.md)\n")
        write(repo / "docs/specs/ideas/alpha.md", "# Alpha\n")
        write(repo / "docs/specs/ideas/beta.md", "# Beta\n")
        found = [
            f
            for f in check_structure(repo, repo / "docs", POLICY)
            if f.code == "docs.idea-unlisted"
        ]
        assert len(found) == 1
        assert (found[0].path or "").endswith("ideas/beta.md")
        assert found[0].message == "is not linked from specs/ideas/index.md"

    def test_s13_4_1_3_listed_idea_pages_pass(self, repo):
        write(
            repo / "docs/specs/ideas/index.md",
            "# Ideas\n\n- [A](alpha.md)\n- [B](beta.md)\n",
        )
        write(repo / "docs/specs/ideas/alpha.md", "# Alpha\n")
        write(repo / "docs/specs/ideas/beta.md", "# Beta\n")
        got = codes(check_structure(repo, repo / "docs", POLICY))
        assert not {"docs.idea-unlisted", "docs.ideas-moved", "docs.kebab-case"} & set(
            got
        )

    def test_s13_4_1_3_an_ideas_folder_without_an_index_reports_every_page(self, repo):
        write(repo / "docs/specs/ideas/alpha.md", "# Alpha\n")
        got = codes(check_structure(repo, repo / "docs", POLICY))
        assert got.count("docs.idea-unlisted") == 1

    def test_s13_4_1_4_an_idea_page_is_kebab_case(self, repo):
        write(repo / "docs/specs/ideas/index.md", "# Ideas\n\n- [B](Big_Idea.md)\n")
        write(repo / "docs/specs/ideas/Big_Idea.md", "# Big\n")
        found = [
            f
            for f in check_structure(repo, repo / "docs", POLICY)
            if f.code == "docs.kebab-case"
        ]
        assert len(found) == 1
        assert (found[0].path or "").endswith("ideas/Big_Idea.md")

    def test_s13_4_1_4_a_policy_without_ideas_checks_nothing(self, repo):
        write(repo / "docs/specs/ideas.md", "# Ideas\n")
        write(repo / "docs/specs/ideas/alpha.md", "# Alpha\n")
        policy = dataclasses.replace(POLICY, ideas=None)
        got = codes(check_structure(repo, repo / "docs", policy))
        assert not {"docs.ideas-moved", "docs.idea-unlisted"} & set(got)


class TestNav:
    def test_index_link_order_wins_over_alphabetical(self, repo):
        write(repo / "docs/guides/alpha.md", "# Alpha\n")
        write(
            repo / "docs/guides/index.md",
            "# Guides\n\n- [Setup](setup.md)\n- [Alpha](alpha.md)\n",
        )
        body = build_nav(repo / "docs")
        assert body.index("guides/setup.md") < body.index("guides/alpha.md")

    def test_s11_1_1_2_include_area_renders_one_include_per_package(self, repo):
        write(
            repo / "docs/_areas.yml",
            AREAS + "  - key: packages\n    title: Packages\n    nav: include\n",
        )
        body = build_nav(repo / "docs", ("packages/a", "packages/b"))
        assert body.index("a: '!include packages/a/mkdocs.yml'") < body.index(
            "b: '!include packages/b/mkdocs.yml'"
        )
        assert "  - Packages:\n" in body

    def test_s11_1_1_3_include_area_without_packages_renders_nothing(self, repo):
        write(
            repo / "docs/_areas.yml",
            AREAS + "  - key: packages\n    title: Packages\n    nav: include\n",
        )
        assert "Packages" not in build_nav(repo / "docs")
        assert "Packages" not in build_nav(repo / "docs", ())

    def test_generated_area_is_skipped_when_absent(self, repo):
        assert "api/index.md" not in build_nav(repo / "docs")

    def test_index_only_area_lists_only_its_index(self, repo):
        write(repo / "docs/api/index.md", "# API\n")
        write(repo / "docs/api/module.md", "# Module\n")
        body = build_nav(repo / "docs")
        assert "  - API Reference: api/index.md\n" in body
        assert "api/module.md" not in body

    def test_titles_use_acronyms(self, repo):
        write(repo / "docs/guides/cli-api.md", "no heading here\n")
        assert "CLI API: guides/cli-api.md" in build_nav(repo / "docs")

    def test_s13_1_1_3_page_title_is_the_h1_or_the_filename_title(self, repo):
        write(repo / "docs/guides/with-h1.md", "intro\n#  Choosing packages  \n")
        write(repo / "docs/guides/no-h1.md", "## Only a subheading\n")
        assert page_title(repo / "docs/guides/with-h1.md") == "Choosing packages"
        assert page_title(repo / "docs/guides/no-h1.md") == "No H1"

    def test_s13_1_1_3_nav_titles_come_from_h1s(self, repo):
        write(repo / "docs/guides/choosing-packages.md", "# Choosing packages\n")
        body = build_nav(repo / "docs")
        assert "Choosing packages: guides/choosing-packages.md" in body
        assert "  - adr/index.md\n" in body

    def test_s14_1_1_1_an_area_index_is_the_first_untitled_item(self, repo):
        write(repo / "docs/guides/a.md", "# A\n")
        body = build_nav(repo / "docs")
        assert "Overview:" not in body
        assert "  - Guides:\n    - guides/index.md\n" in body
        assert body.index("guides/index.md") < body.index("A: guides/a.md")

    @staticmethod
    def _specs(repo, *, epics=True):
        write(repo / "docs/_areas.yml", "areas:\n  - key: specs\n    nav: work\n")
        write(repo / "docs/specs/index.md", "# Specs\n")
        write(repo / "docs/specs/_structure.md", "# S\n")
        write(repo / "docs/specs/ideas/index.md", "# Ideas\n")
        if epics:
            write(repo / "docs/specs/epics/index.md", "# Epics\n")
            write(repo / "docs/specs/epics/E1-one/index.md", "# E1 \u2014 One\n")
            write(repo / "docs/specs/epics/E3-three/index.md", "# E3 \u2014 Three\n")
            write(repo / "docs/specs/epics/E3-three/F3.1-a.md", "# F3.1 \u2014 A\n")
            write(repo / "docs/specs/epics/E3-three/F3.10-b.md", "# F3.10 \u2014 B\n")
            write(repo / "docs/specs/epics/E3-three/F3.2-c.md", "# F3.2 \u2014 C\n")
            write(repo / "docs/specs/epics/E3-three/design.md", "# Design\n")
            write(repo / "docs/specs/epics/E3-three/_hidden.md", "# H\n")
            write(
                repo / "docs/specs/epics/E12-twelve/index.md", "# E12 \u2014 Twelve\n"
            )

    def test_s14_1_3_1_work_area_lists_epics_in_ranges(self, repo):
        self._specs(repo)
        body = build_nav(repo / "docs")
        e = "specs/epics"
        assert body.split("  - Specs:\n", 1)[1] == (
            "    - specs/index.md\n"
            "    - Epics: specs/epics/index.md\n"
            "    - E1\u2013E10:\n"
            "      - E1 \u2014 One:\n"
            f"        - {e}/E1-one/index.md\n"
            "      - E3 \u2014 Three:\n"
            f"        - {e}/E3-three/index.md\n"
            f"        - F3.1 \u2014 A: {e}/E3-three/F3.1-a.md\n"
            f"        - F3.2 \u2014 C: {e}/E3-three/F3.2-c.md\n"
            f"        - F3.10 \u2014 B: {e}/E3-three/F3.10-b.md\n"
            f"        - Design: {e}/E3-three/design.md\n"
            "    - E11\u2013E20:\n"
            "      - E12 \u2014 Twelve:\n"
            f"        - {e}/E12-twelve/index.md\n"
            "    - Ideas:\n      - specs/ideas/index.md\n"
        )

    def test_s14_1_3_2_a_work_area_without_epics_lists_index_and_root_pages(self, repo):
        self._specs(repo, epics=False)
        body = build_nav(repo / "docs")
        assert body.split("  - Specs:\n", 1)[1] == (
            "    - specs/index.md\n    - Ideas:\n      - specs/ideas/index.md\n"
        )

    def test_s13_4_1_1_ideas_folder_is_a_nav_section(self, repo):
        self._specs(repo)
        write(repo / "docs/specs/ideas/beta.md", "# Beta\n")
        write(repo / "docs/specs/ideas/alpha.md", "# Alpha\n")
        write(repo / "docs/specs/ideas/_draft.md", "# D\n")
        body = build_nav(repo / "docs")
        assert body.endswith(
            "    - Ideas:\n"
            "      - specs/ideas/index.md\n"
            "      - Alpha: specs/ideas/alpha.md\n"
            "      - Beta: specs/ideas/beta.md\n"
        )
        assert "_draft.md" not in body

    def test_s13_4_1_1_a_root_ideas_md_is_still_listed(self, repo):
        self._specs(repo, epics=False)
        (repo / "docs/specs/ideas/index.md").unlink()
        (repo / "docs/specs/ideas").rmdir()
        write(repo / "docs/specs/ideas.md", "# Ideas\n")
        body = build_nav(repo / "docs")
        assert body.endswith("    - Ideas: specs/ideas.md\n")
        assert "ideas/" not in body

    def test_update_nav_reports_staleness_without_writing(self, repo):
        before = (repo / "mkdocs.yml").read_text()
        updated, changed = update_nav(repo / "mkdocs.yml", repo / "docs")
        assert changed
        assert (repo / "mkdocs.yml").read_text() == before
        assert NAV_BLOCK.extract(updated) == build_nav(repo / "docs")

    def test_update_nav_is_idempotent(self, repo):
        updated, _ = update_nav(repo / "mkdocs.yml", repo / "docs")
        (repo / "mkdocs.yml").write_text(updated)
        assert update_nav(repo / "mkdocs.yml", repo / "docs")[1] is False

    def test_content_outside_the_block_is_preserved(self, repo):
        updated, _ = update_nav(repo / "mkdocs.yml", repo / "docs")
        assert updated.startswith("site_name: demo\nnav:\n")

    def test_missing_markers_raise(self, repo):
        write(repo / "mkdocs.yml", "site_name: demo\nnav: []\n")
        with pytest.raises(AppException):
            update_nav(repo / "mkdocs.yml", repo / "docs")


class TestCheckSite:
    @pytest.fixture
    def navved(self, repo):
        updated, _ = update_nav(repo / "mkdocs.yml", repo / "docs")
        (repo / "mkdocs.yml").write_text(updated)
        return repo

    def test_a_navigated_tree_has_no_findings(self, navved):
        assert check_site(navved) == []

    def test_orphan_page_is_reported(self, navved):
        write(navved / "docs/guides/orphan.md", "# Orphan\n")
        assert "docs.orphan-page" in codes(check_site(navved))

    def test_nav_target_that_does_not_exist_is_reported(self, navved):
        (navved / "docs/guides/setup.md").unlink()
        assert "docs.nav-missing-page" in codes(check_site(navved))

    def test_broken_link_is_reported(self, navved):
        write(navved / "docs/guides/setup.md", "# Setup\n\n[gone](missing.md)\n")
        assert "docs.broken-link" in codes(check_site(navved))

    def test_s7_3_5_1_link_in_inline_code_is_not_checked(self, navved):
        write(
            navved / "docs/guides/setup.md",
            "# Setup\n\nWrite `[gone](missing.md)` to link.\n",
        )
        assert "docs.broken-link" not in codes(check_site(navved))

    def test_s7_3_5_2_link_text_with_brackets_is_checked(self, navved):
        write(
            navved / "docs/guides/setup.md",
            "# Setup\n\n[No deleted `[cli]` keys](missing.md)\n",
        )
        assert "docs.broken-link" in codes(check_site(navved))

    def test_gitignored_generated_subtree_is_skipped(self, navved):
        write(navved / ".gitignore", "docs/api/\n")
        write(navved / "docs/guides/setup.md", "# Setup\n\n[api](../api/index.md)\n")
        assert check_site(navved) == []

    def test_underscore_pages_do_not_need_navigating(self, navved):
        assert "docs.orphan-page" not in codes(check_site(navved))


class TestMarkdownAgreesWithTheRenderer:
    def test_non_ascii_heading_slug_matches_the_renderer(self):
        assert MarkdownUtils.slugify("Résumé") == "resume"
        assert MarkdownUtils.anchors("# Résumé\n") == {"resume"}

    def test_repeated_headings_get_the_renderer_suffixes(self):
        text = "## Consequences\n\n## Consequences\n\n## Consequences\n"
        assert MarkdownUtils.anchors(text) == {
            "consequences",
            "consequences_1",
            "consequences_2",
        }

    def test_headings_inside_fenced_code_are_not_headings(self):
        text = "# Real\n\n```bash\n# not a heading\n```\n"
        assert MarkdownUtils.anchors(text) == {"real"}

    def test_trailing_hashes_are_not_part_of_the_slug(self):
        assert MarkdownUtils.anchors("## Closed ##\n") == {"closed"}

    def test_reference_links_resolve_through_their_definition(self):
        text = "See [the guide][g] and [setup][].\n\n[g]: guides/index.md\n[setup]: setup.md\n"
        assert MarkdownUtils.links(text) == ["guides/index.md", "setup.md"]

    def test_a_reference_with_no_definition_is_not_a_link(self):
        assert MarkdownUtils.links("See [nothing][missing].\n") == []

    def test_tilde_fences_are_stripped_too(self):
        assert MarkdownUtils.links("~~~\n[x](inside.md)\n~~~\n\n[y](outside.md)\n") == [
            "outside.md"
        ]


class TestGenerate:
    def test_s13_1_1_5_generate_writes_a_stale_nav_once(self, repo):
        from rn_forge.kiln.modules.docs import generate

        assert generate.generate(repo) == ([repo / "mkdocs.yml"], [])
        assert generate.generate(repo) == ([], [])
        assert generate.stale(repo) == []

    def test_s13_1_1_5_stale_reports_the_finding_without_writing(self, repo):
        from rn_forge.kiln.modules.docs import generate

        before = (repo / "mkdocs.yml").read_text()
        assert codes(generate.stale(repo)) == ["docs.nav-stale"]
        assert (repo / "mkdocs.yml").read_text() == before

    def test_s13_1_1_5_nothing_happens_without_mkdocs_yml(self, tmp_path):
        from rn_forge.kiln.modules.docs import generate

        assert generate.generate(tmp_path) == ([], [])
        assert generate.stale(tmp_path) == []
