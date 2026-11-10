"""S4.3.2 — the `docs` module's artifacts: the seeded tree.

Also proves the five properties every F4.3 story owes its module
(`docs/specs/epics/E4-generator/F4.3-concern-modules.md`).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.commons.fs.hashing import ContentHash
from rn_forge.commons.generation import Action, ArtifactKind

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.core.checks import generated
from rn_forge.kiln.modules.core.derived import managed_digest
from rn_forge.kiln.modules.docs import DOCS, generate
from rn_forge.kiln.modules.docs.artifacts import SEEDS
from rn_forge.kiln.modules.docs.nav import NAV_BLOCK, build_nav
from rn_forge.kiln.modules.tasks import TASKS
from rn_forge.kiln.modules.instructions.scaffold import (
    scaffold as instructions_scaffold,
)

ARCHETYPES = ("python-app", "python-tool", "python-lib")

CONFIG = """
schema_version = 1

[repository]
name = "demo"
owner = "rn-forge"
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


def _seeds(archetype: str) -> tuple[str, ...]:
    """The seeds *archetype* carries.

    `python-lib` has no `docs/reference/`; only it has the adding-a-package runbook.
    """
    if archetype == "python-lib":
        return tuple(p for p in SEEDS if not p.startswith("docs/reference/"))
    return tuple(p for p in SEEDS if p != "docs/runbooks/adding-a-package.md")


def _kind(path: str) -> ArtifactKind:
    managed = path.endswith("/_structure.md")
    return ArtifactKind.MANAGED if managed else ArtifactKind.SEEDED


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


def _origin(root: Path, url: str) -> None:
    """Make *root* a Git worktree whose `origin` is *url*."""
    for args in (["init", "-q"], ["remote", "add", "origin", url]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _new(tmp_path: Path, archetype: str = "python-tool", origin: str = "") -> Path:
    """Scaffold and apply into an empty directory, as `kiln new` will."""
    root = _root(tmp_path, archetype)
    if origin:
        _origin(root, origin)
    config = KilnConfig.load(root)
    instructions_scaffold(root, config)
    cycle.apply(root, home=tmp_path / "home")
    generate.generate(root, config.packages if archetype == "python-lib" else ())
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
        ("mkdocs.yml", ArtifactKind.MANAGED),
        *((path, _kind(path)) for path in _seeds(archetype)),
    ]


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_2_property2_into_an_empty_directory_only_creates(
    tmp_path: Path, archetype: str
) -> None:
    actions = _actions(_root(tmp_path, archetype), tmp_path)
    assert set(actions.values()) <= {Action.CREATE, Action.INSERT, Action.SKIP}
    assert all(
        actions[path] is Action.CREATE for path in _seeds(archetype)
    )  # managed too


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_2_property3_a_second_apply_changes_nothing(
    tmp_path: Path, archetype: str
) -> None:
    """Seeds report `SKIP` once present — the engine never inspects them."""
    root = _new(tmp_path, archetype)
    actions = _actions(root, tmp_path)
    expected = {
        path: Action.UNCHANGED if _kind(path) is ArtifactKind.MANAGED else Action.SKIP
        for path in _seeds(archetype)
    }
    assert {path: actions[path] for path in _seeds(archetype)} == expected
    assert {a for k, a in actions.items() if k not in SEEDS} <= {
        Action.UNCHANGED,
        Action.SKIP,
    }


def _normalized(text: str) -> str:
    """Drop the two identity lines a repo writes for itself."""
    text = re.sub(r"^site_name: .*$", "site_name: X", text, count=1, flags=re.M)
    return re.sub(
        r"^site_description: .*$", "site_description: X", text, count=1, flags=re.M
    )


def _provenance(text: str) -> str:
    """Drop the provenance line's kiln version, the only line that never matches."""
    return re.sub(
        r"^<!-- Generated by kiln .*? from",
        "<!-- Generated by kiln X from",
        text,
        count=1,
        flags=re.M,
    )


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    remaining = iter(haystack)
    return all(line in remaining for line in needle)


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
    cycle.apply(root, home=tmp_path / "home")
    assert not (root / "mkdocs.yml").exists()


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_2_1_mkdocs_build_strict_passes_on_the_rendered_tree(
    tmp_path: Path, archetype: str
) -> None:
    from mkdocs.commands.build import build
    from mkdocs.config import load_config

    root = _new(tmp_path / "repo", archetype)
    if archetype != "python-lib":
        # `python-api.md` documents the product's module, which `_new` leaves out.
        (root / "src" / "demo").mkdir(parents=True)
        (root / "src" / "demo" / "__init__.py").write_text(
            '"""Demo."""\n', encoding="utf-8"
        )
    if archetype == "python-lib":
        # The `monorepo` plugin is a docs-group dependency of the generated
        # repo, not of kiln; its own gate builds the real site.
        mkdocs = root / "mkdocs.yml"
        # Without it the packages' `!include` entries do not resolve either.
        lines = mkdocs.read_text(encoding="utf-8").replace("  - monorepo\n", "")
        mkdocs.write_text(
            "".join(
                line
                for line in lines.splitlines(keepends=True)
                if "!include" not in line and "Packages:" not in line
            ),
            encoding="utf-8",
        )
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

    assert {
        k: a
        for k, a in _actions(root, tmp_path).items()
        if a not in (Action.UNCHANGED, Action.SKIP)
    } == {"mkdocs.yml": Action.UPDATE}

    assert generate.generate(root) == ([mkdocs], [])
    after = mkdocs.read_text(encoding="utf-8")
    assert "guides/setup.md" in (NAV_BLOCK.extract(after) or "")
    assert NAV_BLOCK.remove(after) == NAV_BLOCK.remove(before)
    assert _codes(root) == []


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s13_1_1_2_no_docs_artifact_is_a_block(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype)
    kinds = {a.kind for a in DOCS.artifacts(KilnConfig.load(root), root)}
    assert ArtifactKind.BLOCK not in kinds


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s11_4_2_structure_files_are_managed_and_indexes_and_areas_are_seeded(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    kinds = {a.key: a.kind for a in DOCS.artifacts(KilnConfig.load(root), root)}
    seeds = _seeds(archetype)
    structures = [path for path in seeds if path.endswith("/_structure.md")]
    assert len(structures) == (7 if archetype == "python-lib" else 8)
    assert all(kinds[path] is ArtifactKind.MANAGED for path in structures)
    others = [path for path in seeds if path not in structures]
    assert "docs/_areas.yml" in others
    assert all(kinds[path] is ArtifactKind.SEEDED for path in others)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s11_4_2_structure_files_carry_kiln_s_provenance_header(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    for artifact in DOCS.artifacts(KilnConfig.load(root), root):
        first = artifact.content.splitlines()[0]
        if artifact.key == "mkdocs.yml":
            assert re.fullmatch(
                r"# Generated by kiln \S+ from \.rn-forge/kiln/config\.toml"
                r" — do not edit; run 'kiln apply'",
                first,
            )
        elif artifact.kind is ArtifactKind.MANAGED:
            assert re.fullmatch(
                r"<!-- Generated by kiln \S+ from \.rn-forge/kiln/config\.toml"
                r" — do not edit; run 'kiln apply' -->",
                first,
            ), artifact.key
        else:
            assert "Generated by kiln" not in first, artifact.key


def test_s11_4_2_an_edited_structure_file_is_drift_and_an_edited_index_is_not(
    tmp_path: Path,
) -> None:
    root = _new(tmp_path)
    structure = root / "docs" / "specs" / "_structure.md"
    index = root / "docs" / "specs" / "index.md"
    original = structure.read_text(encoding="utf-8")
    structure.write_text(original.replace("belongs", "belonged", 1), encoding="utf-8")
    index.write_text(index.read_text(encoding="utf-8") + "\nNote.\n", encoding="utf-8")

    actions = _actions(root, tmp_path)
    assert actions["docs/specs/_structure.md"] is Action.DRIFT
    assert actions["docs/specs/index.md"] is Action.SKIP


def _config_root(tmp_path: Path, archetype: str, extra: str = "") -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    text = CONFIG.format(archetype=archetype, profile="mkdocs") + extra
    config.write_text(text, encoding="utf-8")
    return tmp_path


def _rendered_mkdocs(root: Path) -> str:
    artifacts = {a.key: a for a in DOCS.artifacts(KilnConfig.load(root), root)}
    return artifacts["mkdocs.yml"].content


def test_s11_2_2_2_a_python_lib_root_body_has_monorepo_glob_paths_and_snippets(
    tmp_path: Path,
) -> None:
    body = _rendered_mkdocs(_config_root(tmp_path, "python-lib"))
    assert "  - search\n  - monorepo\n  - mkdocstrings:" in body
    assert "paths: [packages/*/src]" in body
    assert "  - pymdownx.snippets:\n      check_paths: true\n" in body


@pytest.mark.parametrize(
    ("archetype", "extra", "paths"),
    [
        ("python-app", "", "[src]"),
        ("python-tool", "", "[src]"),
        (
            "python-app",
            '\n[archetype."python-app"]\npackages = ["packages/core"]\n',
            "[src, packages/core/src]",
        ),
    ],
)
def test_s11_2_2_3_other_archetypes_list_src_and_each_package_src(
    tmp_path: Path, archetype: str, extra: str, paths: str
) -> None:
    body = _rendered_mkdocs(_config_root(tmp_path, archetype, extra))
    assert f"paths: {paths}\n" in body
    assert "monorepo" not in body
    assert "snippets" not in body


def test_s11_2_2_4_python_lib_adds_the_packages_area_and_the_package_docs_section(
    tmp_path: Path,
) -> None:
    def rendered(archetype: str) -> dict[str, str]:
        root = _config_root(tmp_path / archetype, archetype)
        return {a.key: a.content for a in DOCS.artifacts(KilnConfig.load(root), root)}

    lib, tool = rendered("python-lib"), rendered("python-tool")
    assert "key: packages" not in lib["docs/_areas.yml"]
    assert "## Package docs" in lib["docs/_structure.md"]
    assert "packages" not in tool["docs/_areas.yml"]
    assert "## Package docs" not in tool["docs/_structure.md"]


def test_s16_10_4_5_structure_names_the_instruction_files_by_audience(
    tmp_path: Path,
) -> None:
    root = _config_root(tmp_path, "python-lib")
    rendered = {a.key: a.content for a in DOCS.artifacts(KilnConfig.load(root), root)}
    text = " ".join(rendered["docs/_structure.md"].split())
    assert (
        "`README.md` is for people and links to the specs board and the ADR log" in text
    )
    assert "`AGENTS.md` is for agents: it carries kiln's block" in text
    assert "`CLAUDE.md` imports `AGENTS.md` with `@AGENTS.md`" in text
    assert "one instruction file links this file and `docs/index.md`" in text
    assert "`CLAUDE.md` links to the specs board" not in text


def test_s11_2_2_5_python_lib_seeds_no_reference_area_and_the_others_keep_it(
    tmp_path: Path,
) -> None:
    def keys(archetype: str) -> set[str]:
        root = _config_root(tmp_path / archetype, archetype)
        return {a.key for a in DOCS.artifacts(KilnConfig.load(root), root)}

    assert not {k for k in keys("python-lib") if k.startswith("docs/reference/")}
    assert {"docs/reference/index.md", "docs/reference/_structure.md"} <= keys(
        "python-app"
    )


DEV = "docs/guides/development.md"
DRIFT = "docs/runbooks/recovering-from-drift.md"
PY_API = "docs/reference/python-api.md"


def _seed_root(tmp_path: Path, archetype: str) -> Path:
    extra = (
        '\n[archetype."python-web-api"]\nbackend = "fastapi"\n'
        if archetype == "python-web-api"
        else ""
    )
    return _config_root(tmp_path, archetype, extra)


def _rendered(tmp_path: Path, archetype: str) -> dict[str, str]:
    root = _seed_root(tmp_path / archetype, archetype)
    return {a.key: a.content for a in DOCS.artifacts(KilnConfig.load(root), root)}


@pytest.mark.parametrize("archetype", ["python-app", "python-tool"])
def test_s4_4_7_1_app_and_tool_seed_the_three_pages(
    tmp_path: Path, archetype: str
) -> None:
    root = _seed_root(tmp_path, archetype)
    artifacts = {a.key: a for a in DOCS.artifacts(KilnConfig.load(root), root)}
    for path in (DEV, DRIFT, PY_API):
        assert artifacts[path].kind is ArtifactKind.SEEDED, path
    assert artifacts[PY_API].content == "# Python API\n\n::: demo\n"


def test_s4_4_7_1_the_module_is_the_name_with_underscores(tmp_path: Path) -> None:
    root = tmp_path
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        CONFIG.format(archetype="python-tool", profile="mkdocs").replace(
            "demo", "my-demo-tool"
        ),
        encoding="utf-8",
    )
    artifacts = {a.key: a for a in DOCS.artifacts(KilnConfig.load(root), root)}
    assert artifacts[PY_API].content == "# Python API\n\n::: my_demo_tool\n"


@pytest.mark.parametrize("archetype", ["python-lib", "python-web-api"])
def test_s4_4_7_2_lib_and_web_seed_two_pages(tmp_path: Path, archetype: str) -> None:
    root = _seed_root(tmp_path, archetype)
    artifacts = {a.key: a for a in DOCS.artifacts(KilnConfig.load(root), root)}
    for path in (DEV, DRIFT):
        assert artifacts[path].kind is ArtifactKind.SEEDED, path
    assert PY_API not in artifacts
    has = "task build -- <package>" in artifacts[DEV].content
    assert has is (archetype == "python-lib")


@pytest.mark.parametrize("archetype", [*ARCHETYPES, "python-web-api"])
def test_s4_4_7_3_indexes_link_the_pages(tmp_path: Path, archetype: str) -> None:
    pages = _rendered(tmp_path, archetype)
    lib = archetype == "python-lib"
    assert "[Development](development.md)" in pages["docs/guides/index.md"]
    runbooks = pages["docs/runbooks/index.md"]
    assert "[Recovering From Drift](recovering-from-drift.md)" in runbooks
    assert ("[Adding A Package](adding-a-package.md)" in runbooks) is lib
    if lib:
        assert runbooks.index("adding-a-package.md") < runbooks.index(
            "recovering-from-drift.md"
        )
    reference = "- [Reference](reference/python-api.md) — the generated Python API.\n"
    assert (reference in pages["docs/index.md"]) is (
        archetype in ("python-app", "python-tool")
    )


IDEAS_INDEX = """\
# Ideas

Ideas not yet agreed as this repository's work. An entry takes no ID and no
state, and does not authorize starting anything. An idea that needs more than
its row has a page in this folder, named after the row and linked from its
**Idea** cell. Promoting one moves its page, or its row's summary, into a new
epic or feature and deletes both; a dropped idea's row and page are deleted too.

[Back to the specs](../index.md)

| Idea | Summary | Source |
| -- | -- | -- |
"""


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s13_4_1_5_seeds_the_ideas_index_not_ideas_md(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    kinds = {a.key: a.kind for a in DOCS.artifacts(KilnConfig.load(root), root)}
    assert kinds["docs/specs/ideas/index.md"] is ArtifactKind.SEEDED
    assert "docs/specs/ideas.md" not in kinds


def test_s13_4_1_5_seeded_ideas_index_is_the_template(tmp_path: Path) -> None:
    rendered = _rendered(tmp_path, "python-tool")
    assert rendered["docs/specs/ideas/index.md"] == IDEAS_INDEX


# S16.2.2 — `mkdocs.yml` is a managed artifact rendered from the config.

STATE = Path(".rn-forge/kiln/state.json")


def _entry(root: Path, key: str) -> dict[str, object]:
    return json.loads((root / STATE).read_text(encoding="utf-8"))["entries"][key]


def _generated(root: Path) -> list[str]:
    return [f.code for f in generated.check(KilnConfig.load(root), root)]


def _new_with(tmp_path: Path, docs_extra: str, archetype: str = "python-tool") -> Path:
    root = _config_root(tmp_path, archetype, "")
    config = root / ".rn-forge" / "kiln" / "config.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text.replace('profile = "mkdocs"\n', 'profile = "mkdocs"\n' + docs_extra),
        encoding="utf-8",
    )
    cycle.apply(root, home=tmp_path / "home")
    generate.generate(root)
    return root


def _mkdocs_text(root: Path) -> str:
    return (root / "mkdocs.yml").read_text(encoding="utf-8")


def _with_nav_body(text: str, body: str) -> str:
    return NAV_BLOCK.render(text, body)


def test_s16_2_2_1_provenance_header(tmp_path: Path) -> None:
    root = _new(tmp_path)
    text = _mkdocs_text(root)

    assert re.match(
        r"# Generated by kiln \S+ from \.rn-forge/kiln/config\.toml"
        r" — do not edit; run 'kiln apply'\n",
        text,
    )
    entry = _entry(root, "mkdocs.yml")
    assert set(entry) == set(_entry(root, "docs/specs/_structure.md"))
    assert entry["kind"] == "managed"
    assert entry["begin_marker"] is None
    assert entry["content_hash"] == managed_digest("mkdocs.yml", text)
    assert entry["content_hash"] != ContentHash.of(text)
    assert _generated(root) == []

    (root / "mkdocs.yml").write_text(
        text.replace("strict: true", "strict: false"), encoding="utf-8"
    )
    assert _generated(root) == ["artifact.drift"]


def test_s16_2_2_1b_nav_edit_is_not_drift(tmp_path: Path) -> None:
    root = _new(tmp_path)
    text = _mkdocs_text(root)

    (root / "mkdocs.yml").write_text(
        _with_nav_body(text, "    - Elsewhere: elsewhere.md\n"), encoding="utf-8"
    )
    assert _generated(root) == []

    for broken in (
        text.replace(NAV_BLOCK.begin + "\n", ""),
        text.replace(NAV_BLOCK.end + "\n", ""),
        text.replace(NAV_BLOCK.begin + "\n", "").replace(NAV_BLOCK.end + "\n", ""),
    ):
        (root / "mkdocs.yml").write_text(broken, encoding="utf-8")
        assert _generated(root) == ["artifact.drift"]


def test_s16_2_2_2_site_dir(tmp_path: Path) -> None:
    root = _new_with(tmp_path / "set", 'site_dir = ".docs-site"\n')
    assert "\nsite_dir: .docs-site\n" in _mkdocs_text(root)

    root = _new_with(tmp_path / "unset", 'site_dir = ""\n')
    assert "site_dir" not in _mkdocs_text(root)


def test_s16_2_2_3_docs_mkdocs_table(tmp_path: Path) -> None:
    root = _new_with(
        tmp_path,
        "\n[docs.mkdocs]\n"
        'plugins = ["glightbox"]\n'
        'markdown_extensions = ["toc"]\n'
        'extra_css = ["a.css"]\n'
        'site_description = "A description: with, punctuation."\n'
        'theme = { logo = "x.png" }\n'
        'extra = { k = "v" }\n',
    )
    document = YamlUtils.load(_mkdocs_text(root).replace("!!python/name:", ""))

    assert document["plugins"][-1] == "glightbox"
    assert document["plugins"][0] == "search"
    assert document["markdown_extensions"][-1] == "toc"
    assert document["markdown_extensions"][0] == "admonition"
    assert document["extra_css"] == ["a.css"]
    assert document["extra"] == {"k": "v"}
    assert document["theme"]["logo"] == "x.png"
    assert document["theme"]["name"] == "material"
    assert document["site_description"] == "A description: with, punctuation."
    assert _mkdocs_text(root).count("site_description") == 1
    assert _generated(root) == []


def test_s16_2_2_4_unknown_key(tmp_path: Path) -> None:
    for key in ("nav = []", 'repo_url = "x"', "theme = { palette = [] }"):
        root = _config_root(
            tmp_path / key[:3], "python-tool", f"\n[docs.mkdocs]\n{key}\n"
        )
        with pytest.raises(AppException):
            KilnConfig.load(root)

    allowed = (
        'plugins = ["a"]\nmarkdown_extensions = ["b"]\ntheme = { c = "d" }\n'
        'extra = { e = "f" }\nextra_css = ["g"]\nextra_javascript = ["h"]\n'
        'site_description = "i"\n'
    )
    root = _config_root(tmp_path / "ok", "python-tool", f"\n[docs.mkdocs]\n{allowed}")
    KilnConfig.load(root)


def test_s16_2_2_5_site_dir_only_when_given(tmp_path: Path) -> None:
    root = _config_root(tmp_path, "python-lib", PACKAGES)
    rendered = {a.key: a.content for a in TASKS.artifacts(KilnConfig.load(root), root)}
    docs = rendered["tasks/docs.yml"]

    assert (
        "mkdocs build --strict{{if .CLI_ARGS}} --site-dir "
        '"{{.CLI_ARGS}}"{{end}}\n' in docs
    )
    assert "MKDOCS_SITE_DIR" not in docs
    assert docs.count('--site-dir "$site"') == 2


def test_s16_2_2_6_nav_still_derived(tmp_path: Path) -> None:
    root = _new(tmp_path)
    (root / "docs" / "guides" / "setup.md").write_text("# Setup\n", encoding="utf-8")

    rendered = {a.key: a.content for a in DOCS.artifacts(KilnConfig.load(root), root)}
    assert "guides/setup.md" in (NAV_BLOCK.extract(rendered["mkdocs.yml"]) or "")
    assert "docs.nav-stale" in _codes(root)

    generate.generate(root)
    assert _codes(root) == []
    assert NAV_BLOCK.extract(_mkdocs_text(root)) == NAV_BLOCK.extract(
        {a.key: a.content for a in DOCS.artifacts(KilnConfig.load(root), root)}[
            "mkdocs.yml"
        ]
    )


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s16_2_2_7_add_page_cycle(tmp_path: Path, archetype: str) -> None:
    root = _new(tmp_path, archetype)
    (root / "docs" / "guides" / "new.md").write_text("# New\n", encoding="utf-8")
    index = root / "docs" / "guides" / "index.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "\n- [New](new.md)\n", encoding="utf-8"
    )

    packages = KilnConfig.load(root).packages if archetype == "python-lib" else ()
    generate.generate(root, packages)
    assert _generated(root) == []
    assert generate.stale(root, packages) == []
    state = (root / STATE).read_bytes()
    mkdocs = (root / "mkdocs.yml").read_bytes()

    for _ in range(2):
        assert {
            k: a
            for k, a in _actions(root, tmp_path).items()
            if a not in (Action.UNCHANGED, Action.SKIP)
        } == {}
        cycle.apply(root, home=tmp_path / "home")
        assert (root / STATE).read_bytes() == state
        assert (root / "mkdocs.yml").read_bytes() == mkdocs


# S16.6.7 — the rendered `mkdocs.yml` carries what pykit's hand-written one needed.

GITHUB = "https://github.com/rn-forge/pykit.git"


def _mkdocs_origin(tmp_path: Path, origin: str, archetype: str = "python-tool") -> str:
    root = _config_root(tmp_path, archetype, "")
    if origin:
        _origin(root, origin)
    cycle.apply(root, home=tmp_path / "home")
    return _mkdocs_text(root)


# S16.6.8 revised S16.6.7: the URLs come from `[repository] owner` and `name`,
# never from git.


@pytest.mark.parametrize(
    "origin", ["", GITHUB, "git@github.com:other/pykit.git", "https://gitlab.com/x/y"]
)
def test_s16_6_8_7_mkdocs_urls_come_from_config(tmp_path: Path, origin: str) -> None:
    text = _mkdocs_origin(tmp_path, origin)

    assert "\nsite_url: https://rn-forge.github.io/demo/\n" in text
    assert "\nrepo_url: https://github.com/rn-forge/demo\n" in text


def test_s16_6_8_8_mkdocs_urls_need_no_git(tmp_path: Path) -> None:
    root = _config_root(tmp_path, "python-tool", "")
    assert not (root / ".git").exists()

    cycle.apply(root, home=tmp_path / "home")

    assert "site_url: https://rn-forge.github.io/demo/\n" in _mkdocs_text(root)


def test_s16_6_8_9_owner_is_the_configured_one(tmp_path: Path) -> None:
    root = _config_root(tmp_path, "python-tool", "")
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("rn-forge", "some-owner"),
        encoding="utf-8",
    )

    cycle.apply(root, home=tmp_path / "home")

    text = _mkdocs_text(root)
    assert "site_url: https://some-owner.github.io/demo/\n" in text
    assert "repo_url: https://github.com/some-owner/demo\n" in text


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s16_6_7_4_mermaid_fence(tmp_path: Path, archetype: str) -> None:
    text = _mkdocs_origin(tmp_path, "", archetype)

    assert text.count("- pymdownx.superfences") == 1
    assert (
        "  - pymdownx.superfences:\n"
        "      custom_fences:\n"
        "        - name: mermaid\n"
        "          class: mermaid\n"
        "          format: !!python/name:pymdownx.superfences.fence_code_format\n"
    ) in text


def test_s16_6_7_5_builds(tmp_path: Path) -> None:
    from mkdocs.commands.build import build
    from mkdocs.config import load_config

    root = _new(tmp_path / "repo", "python-tool", origin=GITHUB)
    (root / "src" / "demo").mkdir(parents=True)
    (root / "src" / "demo" / "__init__.py").write_text(
        '"""Demo."""\n', encoding="utf-8"
    )
    assert "site_url" in _mkdocs_text(root)

    build(
        load_config(
            str(root / "mkdocs.yml"), strict=True, site_dir=str(tmp_path / "site")
        )
    )
    assert (tmp_path / "site" / "index.html").is_file()


MKDOCSTRINGS_OPTIONS = {
    "docstring_style": "auto",
    "heading_level": 2,
    "inherited_members": True,
    "merge_init_into_class": True,
    "show_source": False,
    "show_root_heading": True,
    "show_symbol_type_heading": True,
    "show_symbol_type_toc": True,
}


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s16_6_7_6_mkdocstrings_options(tmp_path: Path, archetype: str) -> None:
    text = _mkdocs_origin(tmp_path, "", archetype)

    # The safe loader has no `!!python/name` constructor; the fence is not under test here.
    document = YamlUtils.load(text.replace("!!python/name:", ""))
    (handlers,) = [
        plugin["mkdocstrings"]
        for plugin in document["plugins"]
        if isinstance(plugin, dict) and "mkdocstrings" in plugin
    ]
    assert handlers["handlers"]["python"]["options"] == MKDOCSTRINGS_OPTIONS
