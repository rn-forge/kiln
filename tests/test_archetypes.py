"""S4.2.1 — the archetype manifests."""

from __future__ import annotations

import pytest

from rn_forge.commons.exceptions import AppException

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.registry import builtin

PYTHON_ARCHETYPES = [
    "python-app",
    "python-lib",
    "python-tool",
    "python-web-api",
    "python-web-app",
]
WEB_ARCHETYPES = ["python-web-api", "python-web-app"]


def _web_root(
    tmp_path, archetype: str, backend: str, frontend: str | None = None
) -> object:
    lines = [
        "schema_version = 1",
        "",
        "[repository]",
        'name = "demo"',
        f'archetype = "{archetype}"',
        "",
        f'[archetype."{archetype}"]',
        f'backend = "{backend}"',
    ]
    if frontend is not None:
        lines.append(f'frontend = "{frontend}"')
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def test_s4_2_1_every_python_archetype_is_shipped() -> None:
    assert list(archetypes.shipped()) == PYTHON_ARCHETYPES


@pytest.mark.parametrize("name", PYTHON_ARCHETYPES)
def test_s4_2_1_every_python_archetype_manifest_loads(name: str) -> None:
    archetype = archetypes.load(name)
    assert archetype.name == name
    expected = ["core", "python"]
    if name == "python-web-app":
        expected.append("frontend")
    assert archetype.modules == [*expected, "docs", "tasks", "cicd", "instructions"]
    assert "rn-forge-commons" in archetype.dependencies.required
    assert set(archetype.dependencies.required) <= set(archetype.dependencies.allowed)
    assert "kiln" in archetype.forbidden_tools
    assert "quality:lint:generated" in archetype.required_validate
    assert len(builtin().for_archetype(archetype)) == len(archetype.modules)


def test_s4_2_1_a_manifest_naming_an_unregistered_module_is_refused_by_name() -> None:
    archetype = archetypes.load("python-app").model_copy(
        update={"modules": ["core", "conjured"]}
    )
    with pytest.raises(AppException, match="conjured"):
        builtin().for_archetype(archetype)


def test_an_unknown_archetype_is_refused_naming_what_ships() -> None:
    with pytest.raises(AppException, match="Unknown archetype 'python-hovercraft'"):
        archetypes.load("python-hovercraft")


def test_lifecycle_and_mkdocs_adjust_the_manifest(repo) -> None:
    archetype = archetypes.for_config(
        KilnConfig.load(repo(archetype="python-app", lifecycle=True, docs="mkdocs"))
    )
    assert "rn-forge-tooling" in archetype.dependencies.required
    assert "docs:build" in archetype.required_validate


def test_s4_4_6_1_python_tool_implies_lifecycle(repo) -> None:
    tool = KilnConfig.load(repo(archetype="python-tool", lifecycle=False))
    assert tool.lifecycle is True
    assert "rn-forge-tooling" in archetypes.for_config(tool).dependencies.required


def test_s4_4_6_1_python_app_without_lifecycle_stays_false(repo) -> None:
    assert KilnConfig.load(repo(archetype="python-app")).lifecycle is False


@pytest.mark.parametrize(
    ("archetype", "backend", "frontend"),
    [
        ("python-web-api", "fastapi", None),
        ("python-web-api", "django", None),
        ("python-web-app", "fastapi", "angular"),
        ("python-web-app", "django", "angular"),
    ],
)
def test_s5_1_1_1_for_config_required_is_commons_cli_web_then_framework(
    tmp_path, archetype: str, backend: str, frontend: str | None
) -> None:
    """for_config's required set is commons, cli, web, framework, in order;
    allowed equals it."""
    config = KilnConfig.load(_web_root(tmp_path, archetype, backend, frontend))
    resolved = archetypes.for_config(config)
    assert resolved.dependencies.required == [
        "rn-forge-commons",
        "rn-forge-cli",
        "rn-forge-web",
        f"rn-forge-{backend}",
    ]
    assert resolved.dependencies.allowed == resolved.dependencies.required


def test_s5_1_1_1_a_web_archetype_without_lifecycle_carries_no_tooling(
    tmp_path,
) -> None:
    config = KilnConfig.load(_web_root(tmp_path, "python-web-api", "fastapi"))
    resolved = archetypes.for_config(config)
    assert "rn-forge-tooling" not in resolved.dependencies.required
    assert "rn-forge-tooling" not in resolved.dependencies.allowed


@pytest.mark.parametrize("archetype", WEB_ARCHETYPES)
def test_s5_1_1_5_an_unsupported_backend_is_rejected_naming_the_key(
    tmp_path, archetype: str
) -> None:
    from rn_forge.commons.lang.models import ModelValidationError

    root = _web_root(tmp_path, archetype, "flask")
    with pytest.raises(ModelValidationError, match=r"archetype\..*\.backend"):
        KilnConfig.load(root)


def test_s5_1_1_5_an_unsupported_frontend_is_rejected_naming_the_key(tmp_path) -> None:
    from rn_forge.commons.lang.models import ModelValidationError

    root = _web_root(tmp_path, "python-web-app", "django", "vue")
    with pytest.raises(ModelValidationError, match=r"archetype\..*\.frontend"):
        KilnConfig.load(root)


def test_s5_1_1_5_an_old_framework_config_key_is_rejected(tmp_path) -> None:
    from rn_forge.commons.lang.models import ModelValidationError

    root = tmp_path
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "schema_version = 1\n\n"
        "[repository]\n"
        'name = "demo"\n'
        'archetype = "python-web-api"\n\n'
        '[archetype."python-web-api"]\n'
        'framework = "fastapi"\n',
        encoding="utf-8",
    )
    with pytest.raises(ModelValidationError, match="framework"):
        KilnConfig.load(root)


def test_s5_1_1_5_a_web_app_table_under_a_python_app_config_is_rejected(
    tmp_path,
) -> None:
    root = tmp_path
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "schema_version = 1\n\n"
        "[repository]\n"
        'name = "demo"\n'
        'archetype = "python-app"\n\n'
        '[archetype."python-web-app"]\n'
        'backend = "django"\n',
        encoding="utf-8",
    )
    with pytest.raises(AppException, match=r"python-web-app.*python-app"):
        KilnConfig.load(root)


def test_s7_1_1_1_requirement_names_the_release_tag() -> None:
    assert archetypes.requirement("rn-forge-cli") == (
        "rn-forge-cli @ git+https://github.com/rn-forge/pykit"
        "@rn-forge-cli-v0.1.0#subdirectory=packages/rn-forge-cli"
    )


def test_s7_1_1_1_every_tag_is_pinned() -> None:
    import re

    assert set(archetypes.RN_FORGE_TAGS) == {
        "rn-forge-commons",
        "rn-forge-cli",
        "rn-forge-tooling",
        "rn-forge-web",
        "rn-forge-django",
        "rn-forge-fastapi",
        "rn-forge-sqlalchemy",
        "rn-forge-devops",
    }
    for key, tag in archetypes.RN_FORGE_TAGS.items():
        assert re.fullmatch(rf"{key}-v\d+\.\d+\.\d+", tag)


def test_s7_1_1_1_an_unpinned_distribution_is_refused() -> None:
    with pytest.raises(KeyError):
        archetypes.requirement("rn-forge-nope")


def test_s7_1_1_2_kiln_takes_pykit_by_tag() -> None:
    import tomllib
    from pathlib import Path

    text = (Path(__file__).parent.parent / "pyproject.toml").read_text("utf-8")
    assert "pykit@main" not in text
    dependencies = tomllib.loads(text)["project"]["dependencies"]
    ours = [d for d in dependencies if d.startswith("rn-forge-")]
    assert ours == [
        archetypes.requirement("rn-forge-commons").replace(
            "rn-forge-commons @", "rn-forge-commons[pydantic] @", 1
        ),
        archetypes.requirement("rn-forge-cli"),
        archetypes.requirement("rn-forge-tooling"),
    ]


def test_s6_4_2_8_devops_is_pinned_and_in_no_archetype() -> None:
    assert archetypes.RN_FORGE_TAGS["rn-forge-devops"] == "rn-forge-devops-v0.2.0"
    for name in archetypes.shipped():
        dependencies = archetypes.load(name).dependencies
        assert "rn-forge-devops" not in (*dependencies.required, *dependencies.allowed)


@pytest.mark.parametrize("name", PYTHON_ARCHETYPES)
def test_s4_12_1_6_required_validate_names_the_docs_tasks(tmp_path, name: str) -> None:
    lines = [
        "schema_version = 1",
        "",
        "[repository]",
        'name = "demo"',
        f'archetype = "{name}"',
        "",
        "[docs]",
        'profile = "mkdocs"',
    ]
    if name in WEB_ARCHETYPES:
        lines += ["", f'[archetype."{name}"]', 'backend = "fastapi"']
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    required = archetypes.for_config(KilnConfig.load(tmp_path)).required_validate
    for task in (
        "docs:lint:site",
        "docs:lint:structure",
        "docs:lint:generate",
        "docs:build",
    ):
        assert task in required
    assert not [t for t in required if t.startswith("quality:lint:docs")]
