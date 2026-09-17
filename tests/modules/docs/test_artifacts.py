"""S4.3.2 — the `docs` module's artifacts: the seeded tree and the nav block.

Also proves the five properties every F4.3 story owes its module
(`docs/specs/epics/E4-generator/F4.3-concern-modules.md`).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from rn_forge.tooling.generation import Action, ArtifactKind

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.docs import DOCS
from rn_forge.kiln.modules.docs.artifacts import SEEDS
from rn_forge.kiln.modules.docs.nav import NAV_BLOCK
from rn_forge.kiln.modules.docs.scaffold import scaffold
from rn_forge.kiln.modules.instructions.scaffold import (
    scaffold as instructions_scaffold,
)

GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "golden"
ARCHETYPES = ("python-app", "python-tool", "python-lib")
NAV_KEY = "mkdocs.yml#generated nav"

CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "{archetype}"

[docs]
profile = "{profile}"
"""

PACKAGES = """
[archetype."python-lib"]
packages = ["packages/alpha", "packages/beta"]
"""

GROWN = {
    "docs/index.md",
    "docs/architecture/index.md",
    "docs/guides/index.md",
    "docs/runbooks/index.md",
    "docs/adr/index.md",
}
"""Seeded pages the goldens have since added their own entries to."""


def _root(
    tmp_path: Path, archetype: str = "python-tool", profile: str = "mkdocs"
) -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    text = CONFIG.format(archetype=archetype, profile=profile)
    if archetype == "python-lib":
        text += PACKAGES
    config.write_text(text, encoding="utf-8")
    return tmp_path


def _new(tmp_path: Path, archetype: str = "python-tool") -> Path:
    """Scaffold and apply into an empty directory, as `kiln new` will."""
    root = _root(tmp_path, archetype)
    config = KilnConfig.load(root)
    scaffold(root, config)
    instructions_scaffold(root, config)
    cycle.apply(root, home=tmp_path / "home")
    return root


def _actions(root: Path, tmp_path: Path) -> dict[str, Action]:
    return {
        change.key: change.action
        for change in cycle.plan(root, home=tmp_path / "home").changes
    }


def _codes(root: Path) -> list[str]:
    return sorted(f.code for f in DOCS.checks(KilnConfig.load(root), root))


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_2_property1_renders_exactly_the_module_s_template_inventory_row(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    artifacts = DOCS.artifacts(KilnConfig.load(root), root)
    assert [(a.key, a.kind) for a in artifacts] == [
        *((path, ArtifactKind.SEEDED) for path in SEEDS),
        (NAV_KEY, ArtifactKind.BLOCK),
    ]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_2_property2_into_an_empty_directory_only_creates(
    tmp_path: Path, archetype: str
) -> None:
    actions = _actions(_root(tmp_path, archetype), tmp_path)
    assert set(actions.values()) <= {Action.CREATE, Action.INSERT, Action.SKIP}
    assert all(actions[path] is Action.CREATE for path in SEEDS)
    assert actions[NAV_KEY] is Action.INSERT


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_2_property3_a_second_apply_changes_nothing(
    tmp_path: Path, archetype: str
) -> None:
    """Seeds report `SKIP` once present — the engine never inspects them."""
    root = _new(tmp_path, archetype)
    actions = _actions(root, tmp_path)
    assert all(actions[path] is Action.SKIP for path in SEEDS)
    assert {a for k, a in actions.items() if k not in SEEDS} == {Action.UNCHANGED}


def _normalized(text: str) -> str:
    """Drop the two identity lines a repo writes for itself."""
    text = re.sub(r"^site_name: .*$", "site_name: X", text, count=1, flags=re.M)
    return re.sub(
        r"^site_description: .*$", "site_description: X", text, count=1, flags=re.M
    )


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    remaining = iter(haystack)
    return all(line in remaining for line in needle)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_2_property4_matches_its_golden(tmp_path: Path, archetype: str) -> None:
    """Grown index pages must still contain every seeded line, in order."""
    golden = GOLDEN / archetype
    config = KilnConfig.load(golden)
    rendered = {a.key: a.content for a in DOCS.artifacts(config, golden)}

    mkdocs = (golden / "mkdocs.yml").read_text(encoding="utf-8")
    assert rendered[NAV_KEY] == NAV_BLOCK.extract(mkdocs)
    scaffold(tmp_path, config)
    body = (tmp_path / "mkdocs.yml").read_text(encoding="utf-8")
    assert _normalized(NAV_BLOCK.render(body, rendered[NAV_KEY])) == _normalized(mkdocs)

    for path in SEEDS:
        on_disk = (golden / path).read_text(encoding="utf-8")
        if path in GROWN:
            assert _is_subsequence(rendered[path].splitlines(), on_disk.splitlines()), (
                path
            )
        else:
            assert rendered[path] == on_disk, path


def test_s4_3_2_property5_checks_pass_on_the_rendered_output(tmp_path: Path) -> None:
    assert _codes(_new(tmp_path)) == []


def test_s4_3_2_property5_structure_fails_on_a_missing_area(tmp_path: Path) -> None:
    root = _new(tmp_path)
    for page in (root / "docs" / "guides").iterdir():
        page.unlink()
    (root / "docs" / "guides").rmdir()
    assert "docs.missing-area" in _codes(root)


def test_s4_3_2_property5_nav_fails_on_an_unnavigated_page(tmp_path: Path) -> None:
    root = _new(tmp_path)
    (root / "docs" / "guides" / "setup.md").write_text("# Setup\n", encoding="utf-8")
    assert "docs.nav-stale" in _codes(root)


def test_s4_3_2_property5_site_fails_on_a_broken_link(tmp_path: Path) -> None:
    root = _new(tmp_path)
    (root / "docs" / "guides" / "index.md").write_text(
        "# Guides\n\n- [Gone](gone.md)\n", encoding="utf-8"
    )
    assert "docs.broken-link" in _codes(root)


@pytest.mark.parametrize("profile", ["none", "external"])
def test_s4_3_2_1_non_mkdocs_profiles_render_no_docs_artifacts(
    tmp_path: Path, profile: str
) -> None:
    root = _root(tmp_path, profile=profile)
    config = KilnConfig.load(root)
    assert DOCS.artifacts(config, root) == []
    scaffold(root, config)
    assert not (root / "mkdocs.yml").exists()


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_2_1_mkdocs_build_strict_passes_on_the_rendered_tree(
    tmp_path: Path, archetype: str
) -> None:
    from mkdocs.commands.build import build
    from mkdocs.config import load_config

    root = _new(tmp_path / "repo", archetype)
    build(
        load_config(
            str(root / "mkdocs.yml"), strict=True, site_dir=str(tmp_path / "site")
        )
    )
    assert (tmp_path / "site" / "index.html").is_file()


def test_s4_3_2_2_an_edited_areas_yml_survives_and_is_what_the_check_reads(
    tmp_path: Path,
) -> None:
    root = _new(tmp_path)
    areas = root / "docs" / "_areas.yml"
    edited = areas.read_text(encoding="utf-8") + "  - key: notes\n    title: Notes\n"
    areas.write_text(edited, encoding="utf-8")

    assert _actions(root, tmp_path)["docs/_areas.yml"] is Action.SKIP
    cycle.apply(root, home=tmp_path / "home")
    assert areas.read_text(encoding="utf-8") == edited
    findings = DOCS.checks(KilnConfig.load(root), root)
    assert any(
        f.code == "docs.missing-area" and Path(f.path or "").name == "notes"
        for f in findings
    )


def test_s4_3_2_3_a_new_page_updates_only_the_nav_block(tmp_path: Path) -> None:
    root = _new(tmp_path)
    mkdocs = root / "mkdocs.yml"
    before = mkdocs.read_text(encoding="utf-8")
    (root / "docs" / "guides" / "setup.md").write_text("# Setup\n", encoding="utf-8")

    actions = _actions(root, tmp_path)
    assert {
        k for k, a in actions.items() if a not in (Action.UNCHANGED, Action.SKIP)
    } == {NAV_KEY}
    assert actions[NAV_KEY] is Action.UPDATE

    cycle.apply(root, home=tmp_path / "home")
    after = mkdocs.read_text(encoding="utf-8")
    assert "guides/setup.md" in (NAV_BLOCK.extract(after) or "")
    assert NAV_BLOCK.remove(after) == NAV_BLOCK.remove(before)
    assert _codes(root) == []
