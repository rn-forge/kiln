"""S4.3.1 — `uv init` + reconcile. S4.3.7 — the scaffold completes `pyproject.toml`.

`uv` is invoked once, into an empty directory, and the reconcile leaves a
`pyproject.toml` with the settings the scaffold fixes, without kiln ever writing the file
kiln apply owns nothing of (kiln ADR-0003, ADR-0005). S4.3.7 adds the
rn-forge dependency lines and the `docs` group so `rn-forge-deps` and
`task setup` pass on a fresh `kiln new` repo too.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from rn_forge.commons.exceptions import AppException

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import CORE, cycle
from rn_forge.kiln.modules.python import scaffold as python_scaffold
from rn_forge.kiln.modules.python.checks import rn_forge_deps
from rn_forge.kiln.modules.python.scaffold import (
    SAMPLE_TEST,
    add_package,
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

TAPLO = Path(sys.executable).parent / "taplo"

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


def _mismatches(config: KilnConfig, root: Path) -> list[str]:
    """Each scaffold-fixed pyproject setting that a `pyproject.toml` lacks."""
    found: list[str] = []
    for relative in archetypes.pyproject_paths(config):
        path = root / relative
        if not path.exists():
            continue
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        tool = document.get("tool", {})
        for key, expected in python_scaffold.PYRIGHT_EXPECTED.items():
            if tool.get("pyright", {}).get(key) != expected:
                found.append(f"{relative}: tool.pyright.{key}")
        addopts = tool.get("pytest", {}).get("ini_options", {}).get("addopts")
        if addopts != python_scaffold.PYTEST_ADDOPTS:
            found.append(f"{relative}: tool.pytest.ini_options.addopts")
    return found


@pytest.mark.parametrize("archetype", ["python-app", "python-tool"])
def test_s4_3_1_1_scaffold_then_reconcile_passes_check_8a(
    tmp_path: Path, archetype: str
) -> None:
    root = _root(tmp_path, archetype)
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "demo_tool" / "__init__.py").is_file()
    assert _mismatches(config, root) == []


def test_s4_3_1_1_scaffold_a_workspace_passes_check_8a_at_root_and_members(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "python-lib")
    config = KilnConfig.load(root)
    scaffold(root, config)
    assert (root / "pyproject.toml").is_file()
    assert (root / "packages" / "demo-alpha" / "pyproject.toml").is_file()
    assert (root / "packages" / "demo-beta" / "pyproject.toml").is_file()
    assert _mismatches(config, root) == []


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


@pytest.mark.parametrize(
    "archetype", ["python-tool", "python-app", "python-web-api", "python-web-app"]
)
def test_s7_3_6_3_root_declares_the_index(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype)
    if archetype.startswith("python-web"):
        config = root / ".rn-forge" / "kiln" / "config.toml"
        config.write_text(
            config.read_text(encoding="utf-8")
            + f'\n[archetype."{archetype}"]\nbackend = "fastapi"\n',
            encoding="utf-8",
        )
    config = KilnConfig.load(root)
    scaffold(root, config)
    document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert document["tool"]["uv"]["index"] == [
        {"name": "rn-forge", "url": archetypes.PYKIT_INDEX}
    ]


def test_s7_3_6_4_pykit_shaped_root_declares_no_index(tmp_path: Path) -> None:
    """The shipped python-lib requires commons, so the empty set is patched in."""
    root = _root(tmp_path, "python-lib")
    config = KilnConfig.load(root)
    shipped = archetypes.for_config(config)
    empty = shipped.model_copy(
        update={
            "dependencies": shipped.dependencies.model_copy(update={"required": []})
        }
    )
    with mock.patch.object(archetypes, "for_config", return_value=empty):
        scaffold(root, config)
    document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert "index" not in document.get("tool", {}).get("uv", {})


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
    assert _mismatches(config, root) == []


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
    assert (root / ".gitignore").read_text(encoding="utf-8") == (
        "## uv ##\n" + UV_FIXTURE.read_text(encoding="utf-8")
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


_TAPLO_CELLS = [
    ("python-tool", "pyproject.toml"),
    ("python-lib", "pyproject.toml"),
    ("python-lib", "packages/demo-alpha/pyproject.toml"),
]


@pytest.mark.parametrize(("archetype", "relative"), _TAPLO_CELLS)
def test_s4_10_1_4_dev_group_has_taplo(
    tmp_path: Path, archetype: str, relative: str
) -> None:
    root = _root(tmp_path, archetype)
    scaffold(root, KilnConfig.load(root))
    groups = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "dependency-groups"
    ]
    assert "taplo" in groups["dev"]


@pytest.mark.parametrize(("archetype", "relative"), _TAPLO_CELLS)
def test_s4_11_3_9_dev_group_has_zizmor_and_actionlint(
    tmp_path: Path, archetype: str, relative: str
) -> None:
    root = _root(tmp_path, archetype)
    scaffold(root, KilnConfig.load(root))
    groups = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "dependency-groups"
    ]
    assert "zizmor" in groups["dev"]
    assert "actionlint-py" in groups["dev"]


@pytest.mark.parametrize(("archetype", "relative"), _TAPLO_CELLS)
def test_s4_11_5_10_dev_group_has_pip_audit(
    tmp_path: Path, archetype: str, relative: str
) -> None:
    root = _root(tmp_path, archetype)
    scaffold(root, KilnConfig.load(root))
    groups = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "dependency-groups"
    ]
    assert "pip-audit" in groups["dev"]


@pytest.mark.parametrize(("archetype", "relative"), _TAPLO_CELLS)
def test_s7_4_2_1_no_kiln_in_dev_group(
    tmp_path: Path, archetype: str, relative: str
) -> None:
    root = _root(tmp_path, archetype)
    scaffold(root, KilnConfig.load(root))
    groups = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "dependency-groups"
    ]
    assert not [r for g in groups.values() for r in g if "rn-forge-kiln" in r]


@pytest.mark.parametrize(("archetype", "relative"), _TAPLO_CELLS)
def test_s4_10_1_5_reconciled_pyproject_is_taplo_clean(
    tmp_path: Path, archetype: str, relative: str
) -> None:
    root = _root(tmp_path, archetype)
    config = KilnConfig.load(root)
    scaffold(root, config)
    (taplo,) = (a for a in CORE.artifacts(config, root) if a.path == ".taplo.toml")
    (root / ".taplo.toml").write_text(taplo.content, encoding="utf-8")
    result = subprocess.run(
        [str(TAPLO), "fmt", "--check", "--diff", relative],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


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


def test_s4_4_4_1_sample_test_fits_at_a_long_name() -> None:
    name = "-".join(["abcdefgh"] * 6) + "xyz"
    assert len(name) == 56
    module = name.replace("-", "_")
    body = sample_test(name)
    assert max(len(line) for line in body.splitlines()) <= 88
    assert body == (
        f"import {module}\n\n\n"
        "def test_package_imports():\n"
        f"    assert {module}.__spec__ is not None\n"
    )


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


def test_s11_2_2_2_the_python_lib_docs_group_is_pinned(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    scaffold(root, KilnConfig.load(root))
    rendered = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert rendered["dependency-groups"]["docs"] == [
        "mdformat>=1.0.0",
        "mdformat-gfm>=0.4",
        "mdformat-front-matters>=2.0.0",
        "mdformat-mkdocs>=5.3.0",
        "mkdocs-material>=9.6",
        "mkdocs-monorepo-plugin>=1.1",
        "mkdocstrings[python]>=0.30",
    ]


@pytest.mark.parametrize(
    ("archetype", "scripts"),
    [
        ("python-tool", {"demo-tool": "demo_tool.main:app"}),
        ("python-app", {"demo-tool": "demo_tool.main:app"}),
        ("python-lib", None),
    ],
)
def test_s4_9_1_7_scaffold_points_project_scripts_at_the_app(
    tmp_path: Path, archetype: str, scripts: dict[str, str] | None
) -> None:
    root = _root(tmp_path, archetype)
    scaffold(root, KilnConfig.load(root))
    document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert document["project"].get("scripts") == scripts


WEB_API_CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "python-web-api"

[archetype."python-web-api"]
backend = "fastapi"
"""


def _web_api(tmp_path: Path) -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(WEB_API_CONFIG, encoding="utf-8")
    return tmp_path


def _toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _scaffolded(tmp_path: Path, archetype: str) -> tuple[Path, KilnConfig]:
    root = (
        _web_api(tmp_path)
        if archetype == "python-web-api"
        else _root(tmp_path, archetype)
    )
    config = KilnConfig.load(root)
    scaffold(root, config)
    return root, config


def _add_package(root: Path, config: KilnConfig, name: str) -> Path:
    add_package(root, config, name, "https://github.com/acme/demo-lib")
    return root / "packages" / name


def test_s4_4_8_5_readme_is_set_where_a_readme_is_seeded(tmp_path: Path) -> None:
    app, _ = _scaffolded(tmp_path / "app", "python-app")
    lib, _ = _scaffolded(tmp_path / "lib", "python-lib")
    api, _ = _scaffolded(tmp_path / "api", "python-web-api")

    assert _toml(app / "pyproject.toml")["project"]["readme"] == "README.md"
    for member in ("demo-alpha", "demo-beta"):
        document = _toml(lib / "packages" / member / "pyproject.toml")
        assert document["project"]["readme"] == "README.md"
    assert "readme" not in _toml(lib / "pyproject.toml")["project"]
    (member_pyproject,) = (api / "pyproject.toml").parent.glob("*/*/pyproject.toml")
    assert "readme" not in _toml(member_pyproject)["project"]


def test_s4_4_8_6_every_package_is_typed(tmp_path: Path) -> None:
    app, _ = _scaffolded(tmp_path / "app", "python-app")
    lib, _ = _scaffolded(tmp_path / "lib", "python-lib")
    api, api_config = _scaffolded(tmp_path / "api", "python-web-api")

    assert (app / "src" / "demo_tool" / "py.typed").is_file()
    assert (
        lib / "packages" / "demo-alpha" / "src" / "demo_alpha" / "py.typed"
    ).is_file()
    (api_dir,) = api_config.packages
    assert (api / api_dir / "src" / "demo_api" / "py.typed").is_file()


def test_s4_4_8_7_lib_members_are_libraries(tmp_path: Path) -> None:
    root, config = _scaffolded(tmp_path, "python-lib")
    added = _add_package(root, config, "demo-gamma")

    for member, module in (
        (root / "packages" / "demo-alpha", "demo_alpha"),
        (added, "demo_gamma"),
    ):
        assert "scripts" not in _toml(member / "pyproject.toml")["project"]
        init = (member / "src" / module / "__init__.py").read_text(encoding="utf-8")
        assert "def main" not in init


def test_s4_4_8_8_python_version_sits_at_the_workspace_root(tmp_path: Path) -> None:
    app, _ = _scaffolded(tmp_path / "app", "python-app")
    lib, lib_config = _scaffolded(tmp_path / "lib", "python-lib")
    api, _ = _scaffolded(tmp_path / "api", "python-web-api")
    added = _add_package(lib, lib_config, "demo-gamma")

    assert (app / ".python-version").is_file()
    assert (lib / ".python-version").is_file()
    assert (api / ".python-version").is_file()
    assert sorted(p.relative_to(lib) for p in lib.rglob(".python-version")) == [
        Path(".python-version")
    ]
    assert not (added / ".python-version").exists()
    assert sorted(p.relative_to(api) for p in api.rglob(".python-version")) == [
        Path(".python-version")
    ]


def test_s4_4_8_9_lib_root_points_tools_at_packages(tmp_path: Path) -> None:
    lib, _ = _scaffolded(tmp_path / "lib", "python-lib")
    app, _ = _scaffolded(tmp_path / "app", "python-app")

    document = _toml(lib / "pyproject.toml")
    assert document["tool"]["pyright"]["include"] == ["packages"]
    assert document["tool"]["pytest"]["ini_options"]["testpaths"] == ["packages"]
    assert "coverage[toml]>=7.6" in document["dependency-groups"]["dev"]

    other = _toml(app / "pyproject.toml")
    assert "include" not in other["tool"]["pyright"]
    assert "testpaths" not in other["tool"]["pytest"]["ini_options"]
    assert "coverage[toml]>=7.6" not in other["dependency-groups"]["dev"]


def _uv(path: Path) -> dict[str, Any]:
    return _toml(path).get("tool", {}).get("uv", {})


def _scaffolded_app_with_lifecycle(tmp_path: Path) -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        CONFIG.format(archetype="python-app", docs_profile="mkdocs").replace(
            'archetype = "python-app"', 'archetype = "python-app"\nlifecycle = true'
        ),
        encoding="utf-8",
    )
    scaffold(tmp_path, KilnConfig.load(tmp_path))
    return tmp_path


@pytest.mark.parametrize("kind", ["python-app", "lifecycle", "python-web-api"])
def test_s7_1_2_1_application_roots_ignore_sources(tmp_path: Path, kind: str) -> None:
    if kind == "lifecycle":
        root = _scaffolded_app_with_lifecycle(tmp_path)
    else:
        root, _ = _scaffolded(tmp_path, kind)

    assert _uv(root / "pyproject.toml")["no-sources"] is True


def test_s7_1_2_1_members_do_not_set_it(tmp_path: Path) -> None:
    root, config = _scaffolded(tmp_path, "python-web-api")

    (member,) = config.packages
    assert "no-sources" not in _uv(root / member / "pyproject.toml")


def test_s7_1_2_2_python_lib_keeps_sources(tmp_path: Path) -> None:
    root, _ = _scaffolded(tmp_path, "python-lib")

    for path in root.rglob("pyproject.toml"):
        assert "no-sources" not in _uv(path)


def test_s7_1_2_1_build_backend_survives(tmp_path: Path) -> None:
    root, _ = _scaffolded(tmp_path, "python-app")

    uv = _uv(root / "pyproject.toml")
    assert "build-backend" in uv
    assert uv["no-sources"] is True
