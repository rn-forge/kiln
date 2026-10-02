"""S4.3.1 — `uv init` + reconcile. S4.3.7 — the scaffold completes `pyproject.toml`.

`uv` is invoked once, into an empty directory, and the reconcile leaves a
`pyproject.toml` that check 8a passes without kiln ever writing the file
kiln apply owns nothing of (kiln ADR-0003, ADR-0005). S4.3.7 adds the
rn-forge dependency lines and the `docs` group so `rn-forge-deps` and
`task setup` pass on a fresh `kiln new` repo too.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from unittest import mock

import pytest
from rn_forge.commons.exceptions import AppException

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.python import scaffold as python_scaffold
from rn_forge.kiln.modules.python.checks import pyproject, rn_forge_deps
from rn_forge.kiln.modules.python.scaffold import (
    SAMPLE_TEST,
    reconcile_backend,
    sample_test,
    scaffold,
    scaffold_backend,
    uv_gitignore,
)

CONFIG = """
schema_version = 1

[repository]
name = "demo-tool"
archetype = "{archetype}"

[docs]
profile = "{docs_profile}"
"""

LIB_CONFIG = """
schema_version = 1

[repository]
name = "demo-lib"
archetype = "python-lib"

[archetype."python-lib"]
packages = ["packages/demo-alpha", "packages/demo-beta"]

[docs]
profile = "{docs_profile}"
"""


def _root(tmp_path: Path, archetype: str, *, docs_profile: str = "mkdocs") -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    template = LIB_CONFIG if archetype == "python-lib" else CONFIG
    text = template.format(archetype=archetype, docs_profile=docs_profile)
    config.write_text(text, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("archetype", ["python-app", "python-tool"])
def test_s4_3_1_1_scaffold_then_reconcile_passes_check_8a(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "demo_tool" / "__init__.py").is_file()
    assert pyproject.check(config, root) == []


def test_s4_3_1_1_scaffold_a_workspace_passes_check_8a_at_root_and_members(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "python-lib")
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert (root / "pyproject.toml").is_file()
    assert (root / "packages" / "demo-alpha" / "pyproject.toml").is_file()
    assert (root / "packages" / "demo-beta" / "pyproject.toml").is_file()
    assert pyproject.check(config, root) == []


def test_s4_3_1_1_scaffold_never_leaves_a_git_tree_or_a_readme(tmp_path: Path) -> None:
    """Scaffolding shells out to `uv init` alone; it never templates its output (D16)."""
    root = _root(tmp_path, "python-app")
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert not (root / ".git").exists()
    assert not (root / "README.md").exists()


@pytest.mark.parametrize("archetype", ["python-app", "python-tool", "python-lib"])
def test_s4_3_7_rn_forge_deps_passes_after_scaffold(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert rn_forge_deps.check(config, root) == []


@pytest.mark.parametrize("archetype", ["python-app", "python-tool"])
def test_s4_3_7_root_dependencies_match_archetype_order(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    config = KilnConfig.load(root)
    scaffold(root, config)
    document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    required = archetypes.for_config(config).dependencies.required
    assert document["project"]["dependencies"] == [
        archetypes.requirement(name) for name in required
    ]


def test_s4_3_7_workspace_members_carry_dependencies_root_does_not(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "python-lib")
    config = KilnConfig.load(root)
    scaffold(root, config)
    required = archetypes.for_config(config).dependencies.required
    expected = [archetypes.requirement(name) for name in required]
    for package in ("demo-alpha", "demo-beta"):
        member = tomllib.loads(
            (root / "packages" / package / "pyproject.toml").read_text(encoding="utf-8")
        )
        assert member["project"]["dependencies"] == expected
    root_document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert root_document["project"]["dependencies"] == []


@pytest.mark.parametrize("docs_profile", ["none", "mkdocs"])
def test_s4_3_7_root_docs_group_reflects_profile(
    tmp_path: Path, docs_profile: str
) -> None:
    root = _root(tmp_path, "python-tool", docs_profile=docs_profile)
    config = KilnConfig.load(root)
    scaffold(root, config)
    document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    docs_group = document["dependency-groups"]["docs"]
    assert "mdformat>=1.0.0" in docs_group
    has_mkdocs_entry = any(entry.startswith("mkdocs-") for entry in docs_group)
    assert has_mkdocs_entry == (docs_profile == "mkdocs")


def test_s4_3_7_check_8a_still_passes(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-tool")
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert pyproject.check(config, root) == []


UV_FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "scaffold" / "uv" / ".gitignore"
)


def test_s5_3_6_1_live_uv_capture_matches_the_fixture() -> None:
    assert uv_gitignore() == UV_FIXTURE.read_text(encoding="utf-8")


@pytest.mark.parametrize("archetype", ["python-tool", "python-lib"])
def test_s5_3_6_1_scaffold_seeds_the_uv_body_once_at_the_root(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    scaffold(root, KilnConfig.load(root))
    assert (root / ".gitignore").read_text(encoding="utf-8") == UV_FIXTURE.read_text(
        encoding="utf-8"
    )
    scaffolded = [
        p.relative_to(root)
        for p in root.rglob("*")
        if ".uv-cache" not in p.relative_to(root).parts  # `task`'s UV_CACHE_DIR
    ]
    assert [p for p in scaffolded if p.name == ".gitignore"] == [Path(".gitignore")]
    assert [p for p in scaffolded if p.name == ".git"] == []


@pytest.mark.parametrize(
    ("archetype", "relative"),
    [
        ("python-tool", "pyproject.toml"),
        ("python-lib", "pyproject.toml"),
        ("python-lib", "packages/demo-alpha/pyproject.toml"),
    ],
)
def test_s5_3_6_4_dependency_lists_are_multiline_and_tables_spaced(
    tmp_path: Path, archetype: str, relative: str
) -> None:
    root = _root(tmp_path, archetype)
    scaffold(root, KilnConfig.load(root))
    text = (root / relative).read_text(encoding="utf-8")
    document = tomllib.loads(text)
    lists = {
        key: value
        for key, value in [
            ("dependencies", document["project"]["dependencies"]),
            *document.get("dependency-groups", {}).items(),
        ]
        if value
    }
    assert lists
    for key, values in lists.items():
        assert f"{key} = [\n" in text, key
        for value in values:
            assert f'    "{value}",\n' in text, value
    assert re.search(r"[^\n]\n\[", text) is None  # every table follows a blank line


def test_s5_3_6_4_readable_toml_round_trips_and_keeps_comments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    root = _root(tmp_path / "config", "python-lib")
    config = KilnConfig.load(root)
    scaffold_backend(raw, config)
    member = raw / "packages" / "demo-alpha" / "pyproject.toml"
    member.write_text("# kept: a repo comment\n" + member.read_text("utf-8"), "utf-8")

    readable = tmp_path / "readable"
    reconcile_backend(raw, readable, config)
    monkeypatch.setattr(python_scaffold, "_multiline_lists", lambda path: None)
    dense = tmp_path / "dense"
    reconcile_backend(raw, dense, config)

    for relative in ("pyproject.toml", "packages/demo-alpha/pyproject.toml"):
        pretty = (readable / relative).read_text(encoding="utf-8")
        plain = (dense / relative).read_text(encoding="utf-8")
        assert pretty != plain
        assert tomllib.loads(pretty) == tomllib.loads(plain)
    member_text = (readable / "packages/demo-alpha/pyproject.toml").read_text("utf-8")
    assert member_text.startswith("# kept: a repo comment\n")


def test_s5_3_6_4_apply_does_not_reformat_repo_owned_toml(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-tool")
    scaffold(root, KilnConfig.load(root))
    pyproject = root / "pyproject.toml"
    dense = pyproject.read_text(encoding="utf-8") + '\n[tool.demo]\nx = ["a", "b"]\n'
    pyproject.write_text(dense, encoding="utf-8")

    cycle.apply(root, home=tmp_path / "home")
    assert pyproject.read_text(encoding="utf-8") == dense


GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "golden"


@pytest.mark.parametrize(
    ("archetype", "packages"),
    [
        ("python-app", {".": "demo-tool"}),
        ("python-tool", {".": "demo-tool"}),
        (
            "python-lib",
            {"packages/demo-alpha": "demo-alpha", "packages/demo-beta": "demo-beta"},
        ),
    ],
)
def test_s4_5_10_scaffold_writes_a_sample_test_into_each_package(
    tmp_path: Path, archetype: str, packages: dict[str, str]
) -> None:
    root = _root(tmp_path, archetype)
    scaffold(root, KilnConfig.load(root))
    written = {
        p.relative_to(root)
        for p in root.rglob("test_*.py")
        if ".uv-cache" not in p.relative_to(root).parts
    }
    assert written == {Path(package) / SAMPLE_TEST for package in packages}
    for package, name in packages.items():
        body = (root / package / SAMPLE_TEST).read_text(encoding="utf-8")
        assert body == sample_test(name)


@pytest.mark.parametrize(
    ("golden", "name"),
    [
        ("python-app", "golden-app"),
        ("python-tool", "golden-tool"),
        ("python-lib/packages/golden-alpha", "golden-alpha"),
        ("python-lib/packages/golden-beta", "golden-beta"),
    ],
)
def test_s4_5_10_each_golden_carries_the_sample_test(golden: str, name: str) -> None:
    on_disk = (GOLDEN / golden / SAMPLE_TEST).read_text(encoding="utf-8")
    assert on_disk == sample_test(name)


def _bare_lib(tmp_path: Path, *, docs_profile: str = "mkdocs") -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        LIB_CONFIG.split("[archetype")[0] + f'[docs]\nprofile = "{docs_profile}"\n',
        encoding="utf-8",
    )
    return tmp_path


def test_s11_2_2_1_a_python_lib_with_no_packages_is_a_bare_workspace(
    tmp_path: Path,
) -> None:
    root = _bare_lib(tmp_path)
    scaffold(root, KilnConfig.load(root))
    document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert document["tool"]["uv"]["workspace"] == {"members": []}
    assert not (root / "packages").exists()


@pytest.mark.parametrize(
    ("archetype", "docs_profile", "expected"),
    [
        ("python-lib", "mkdocs", True),
        ("python-lib", "none", False),
        ("python-tool", "mkdocs", False),
    ],
)
def test_s11_2_2_2_only_python_lib_under_mkdocs_gets_the_monorepo_plugin(
    tmp_path: Path, archetype: str, docs_profile: str, expected: bool
) -> None:
    root = _root(tmp_path, archetype, docs_profile=docs_profile)
    scaffold(root, KilnConfig.load(root))
    document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert ("mkdocs-monorepo-plugin>=1.1" in document["dependency-groups"]["docs"]) == (
        expected
    )


def test_s11_2_2_2_the_python_lib_docs_group_matches_the_golden(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    scaffold(root, KilnConfig.load(root))
    rendered = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    golden = tomllib.loads(
        (GOLDEN / "python-lib" / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert rendered["dependency-groups"]["docs"] == golden["dependency-groups"]["docs"]
