"""The `python` module's artifacts: `.importlinter`.

Also proves the five properties every concern module owes.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest
from tests.conftest import LIB_PACKAGES, write_config
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.generation import Action, Artifact, ArtifactKind

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.python import PYTHON

ARCHETYPES = ("python-app", "python-tool", "python-lib")


def _importlinter(config: KilnConfig, root: Path) -> list[Artifact]:
    """The module's `.importlinter` alone; the seeded starter files belong to the starter tests."""
    return [a for a in PYTHON.artifacts(config, root) if a.path == ".importlinter"]


def _root(tmp_path: Path, archetype: str) -> Path:
    return write_config(
        tmp_path,
        archetype,
        name="demo",
        packages=LIB_PACKAGES if archetype == "python-lib" else None,
    )


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_renders_exactly_the_module_s_template_inventory_row(
    tmp_path: Path, archetype: str
) -> None:
    """The template inventory lists `.importlinter`, and `cli.toml` for a lifecycle repo."""
    config = KilnConfig.load(_root(tmp_path, archetype))
    artifacts = PYTHON.artifacts(config, tmp_path)
    expected = [".importlinter"]
    if archetype == "python-tool":
        expected.append("src/demo/cli.toml")
    assert [a.path for a in artifacts] == expected
    assert artifacts[0].kind is ArtifactKind.BLOCK


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_into_an_empty_directory_only_creates(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype)
    home = tmp_path / "home"
    actions = {
        change.key: change.action for change in cycle.plan(root, home=home).changes
    }
    assert set(actions.values()) <= {Action.CREATE, Action.INSERT, Action.SKIP}
    assert actions[".importlinter#rn-forge kiln"] is Action.INSERT


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_a_second_apply_is_unchanged(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype)
    home = tmp_path / "home"
    cycle.apply(root, home=home)
    actions = {
        change.key: change.action for change in cycle.plan(root, home=home).changes
    }
    assert set(actions.values()) <= {Action.UNCHANGED, Action.SKIP}


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_lint_imports_passes_on_the_rendered_importlinter(
    tmp_path: Path,
    archetype: str,
    monkeypatch: pytest.MonkeyPatch,
    rendered: Callable[[str], Path],
) -> None:
    """`lint-imports` passes on the rendered `.importlinter` in each archetype."""
    from importlinter import cli as importlinter_cli

    source = rendered(archetype)
    config = KilnConfig.load(source)
    [artifact] = _importlinter(config, source)
    assert artifact.block is not None
    (tmp_path / ".importlinter").write_text(
        artifact.block.render("", artifact.content), encoding="utf-8"
    )

    src_dirs = (
        [str(source / "src")]
        if archetype != "python-lib"
        else [
            str(source / "packages" / "lib-alpha" / "src"),
            str(source / "packages" / "lib-beta" / "src"),
        ]
    )
    monkeypatch.chdir(tmp_path)
    for src_dir in src_dirs:
        monkeypatch.syspath_prepend(src_dir)
    assert (
        importlinter_cli.lint_imports(config_filename=str(tmp_path / ".importlinter"))
        == importlinter_cli.EXIT_STATUS_SUCCESS
    )


WEB_CONFIG = """
schema_version = 1

[repository]
name = "demo"
owner = "rn-forge"
archetype = "{archetype}"

[archetype."{archetype}"]
backend = "{backend}"
{extra}
"""


def _web_root(tmp_path: Path, archetype: str, backend: str, extra: str = "") -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        WEB_CONFIG.format(archetype=archetype, backend=backend, extra=extra),
        encoding="utf-8",
    )
    return tmp_path


def test_python_web_api_root_package_is_the_api_member(tmp_path: Path) -> None:
    root = _web_root(tmp_path, "python-web-api", "fastapi")
    config = KilnConfig.load(root)
    [artifact] = PYTHON.artifacts(config, root)
    assert "root_package = demo_api" in artifact.content


def test_python_web_api_fastapi_forbids_django_not_fastapi(
    tmp_path: Path,
) -> None:
    root = _web_root(tmp_path, "python-web-api", "fastapi")
    config = KilnConfig.load(root)
    [artifact] = PYTHON.artifacts(config, root)
    forbidden = artifact.content.split("forbidden_modules =")[1].split(
        "allow_indirect"
    )[0]
    assert "django" in forbidden
    assert "fastapi" not in forbidden
    assert "typer" in forbidden
    assert "jinja2" in forbidden
    assert "click" in forbidden


def test_python_web_app_django_forbids_fastapi_not_django(
    tmp_path: Path,
) -> None:
    root = _web_root(tmp_path, "python-web-app", "django", extra='frontend = "angular"')
    config = KilnConfig.load(root)
    [artifact] = PYTHON.artifacts(config, root)
    forbidden = artifact.content.split("forbidden_modules =")[1].split(
        "allow_indirect"
    )[0]
    assert "fastapi" in forbidden
    assert "django" not in forbidden


def test_backend_flag_only_changes_the_importlinter_forbidden_list(
    tmp_path: Path,
) -> None:
    """`backend` never changes topology — only .importlinter's forbidden list."""
    django_root = _web_root(
        tmp_path / "django", "python-web-app", "django", extra='frontend = "angular"'
    )
    fastapi_root = _web_root(
        tmp_path / "fastapi", "python-web-app", "fastapi", extra='frontend = "angular"'
    )
    [django_artifact] = PYTHON.artifacts(KilnConfig.load(django_root), django_root)
    [fastapi_artifact] = PYTHON.artifacts(KilnConfig.load(fastapi_root), fastapi_root)
    django_lines = django_artifact.content.splitlines()
    fastapi_lines = (
        fastapi_artifact.content.split("; kiln's architecture baseline, ARCH-0004")[0]
        .rstrip()
        .splitlines()
    )
    assert len(django_lines) == len(fastapi_lines)
    diffs = [(a, b) for a, b in zip(django_lines, fastapi_lines, strict=True) if a != b]
    assert diffs == [("    fastapi", "    django")]


MODULE_TAIL = 'modules = { "packages/alpha" = "rn_forge.alpha" }\n'


def _lib(
    tmp_path: Path, tail: str = "", packages: list[str] = LIB_PACKAGES
) -> KilnConfig:
    write_config(tmp_path, "python-lib", name="demo", packages=packages, tail=tail)
    return KilnConfig.load(tmp_path)


def test_module_defaults_from_the_path(tmp_path: Path) -> None:
    config = KilnConfig.load(_root(tmp_path, "python-lib"))
    assert config.module_for("packages/alpha") == "alpha"
    assert config.module_for("packages/rn-forge-cli") == "rn_forge_cli"


def test_lib_module_is_read_from_config(tmp_path: Path) -> None:
    config = _lib(
        tmp_path,
        'modules = { "packages/rn-forge-cli" = "rn_forge.cli" }\n',
        ["packages/rn-forge-cli", "packages/beta"],
    )
    assert config.module_for("packages/rn-forge-cli") == "rn_forge.cli"
    assert config.module_for("packages/beta") == "beta"


def test_a_modules_key_outside_packages_is_a_config_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(AppException, match="packages/gamma"):
        _lib(tmp_path, 'modules = { "packages/gamma" = "gamma" }\n')


def test_an_invalid_module_value_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(AppException):
        _lib(tmp_path, 'modules = { "packages/alpha" = "Rn-Forge" }\n')


def test_importlinter_names_each_declared_lib_module(tmp_path: Path) -> None:
    [artifact] = _importlinter(_lib(tmp_path, MODULE_TAIL), tmp_path)
    roots = [line.strip() for line in artifact.content.splitlines()]
    assert "rn_forge.alpha" in roots
    assert "beta" in roots
    assert "alpha" not in roots


OWN_TAIL = 'import_contracts = "own"\n'


def _load(tmp_path: Path, text: str) -> KilnConfig:
    """Load a config whose `[repository]` table `_single` extends by hand."""
    (tmp_path / ".rn-forge" / "kiln").mkdir(parents=True)
    (tmp_path / ".rn-forge" / "kiln" / "config.toml").write_text(text, encoding="utf-8")
    return KilnConfig.load(tmp_path)


def test_default_keeps_kiln_contracts(tmp_path: Path) -> None:
    config = _lib(tmp_path)
    assert config.import_contracts == "kiln"
    [artifact] = _importlinter(config, tmp_path)
    assert "[importlinter:contract:frameworks-come-from-rn-forge]" in artifact.content
    assert "[importlinter:contract:packages-are-independent]" in artifact.content
    assert "owns its import contracts" not in artifact.content


def test_own_renders_only_the_root(tmp_path: Path) -> None:
    config = _lib(tmp_path, OWN_TAIL)
    assert config.import_contracts == "own"
    [artifact] = _importlinter(config, tmp_path)
    content = artifact.content
    assert "[importlinter]" in content
    assert "root_packages =" in content
    assert "include_external_packages = True" in content
    assert not [
        line
        for line in content.splitlines()
        if line.startswith("[importlinter:contract:")
    ]
    assert (
        "; This repository owns its import contracts: they are below the END marker."
        in content
    )


@pytest.mark.parametrize("archetype", ["python-app", "python-tool"])
def test_own_is_python_lib_only(tmp_path: Path, archetype: str) -> None:
    with pytest.raises(AppException):
        write_config(
            tmp_path,
            archetype,
            name="demo",
            tail=f'\n[archetype."{archetype}"]\nimport_contracts = "own"\n',
        )
        KilnConfig.load(tmp_path)


def test_an_unknown_value_is_refused(tmp_path: Path) -> None:
    with pytest.raises(AppException):
        _lib(tmp_path, 'import_contracts = "none"\n')


def _single(
    tmp_path: Path, archetype: str, name: str = "demo-tool", body: str = ""
) -> KilnConfig:
    text = f"""
schema_version = 1

[repository]
name = "{name}"
owner = "rn-forge"
archetype = "{archetype}"
{body}"""
    return _load(tmp_path, text)


def test_module_defaults_from_the_name(tmp_path: Path) -> None:
    assert _single(tmp_path, "python-tool").module == "demo_tool"


@pytest.mark.parametrize("archetype", ["python-tool", "python-app"])
def test_single_module_is_read_from_config(tmp_path: Path, archetype: str) -> None:
    config = _single(
        tmp_path,
        archetype,
        body=f'\n[archetype."{archetype}"]\nmodule = "rn_forge.demo"\n',
    )
    assert config.module == "rn_forge.demo"


def test_an_invalid_module_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(AppException):
        _single(
            tmp_path,
            "python-tool",
            body='\n[archetype."python-tool"]\nmodule = "Rn-Forge"\n',
        )


@pytest.mark.parametrize(
    "archetype", ["python-lib", "python-web-api", "python-web-app"]
)
def test_module_is_single_package_only(tmp_path: Path, archetype: str) -> None:
    with pytest.raises(AppException):
        _single(
            tmp_path,
            archetype,
            body=f'\n[archetype."{archetype}"]\nmodule = "rn_forge.demo"\n',
        )


def test_importlinter_names_the_declared_tool_module(tmp_path: Path) -> None:
    config = _single(
        tmp_path,
        "python-tool",
        body='\n[archetype."python-tool"]\nmodule = "rn_forge.demo"\n',
    )
    [artifact] = _importlinter(config, tmp_path)
    assert "root_package = rn_forge.demo\n" in artifact.content
    assert (
        "name = rn_forge.demo imports no framework or CLI toolkit directly"
        in artifact.content
    )


def _lint_demo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, files: dict[str, str]
) -> int:
    """Render `.importlinter` for a `python-app` named `demo`, build the package and lint it."""
    from importlinter import cli as importlinter_cli

    config_root = tmp_path / "config"
    write_config(config_root, "python-app", name="demo")
    config = KilnConfig.load(config_root)
    [artifact] = _importlinter(config, config_root)
    assert artifact.block is not None
    work = tmp_path / "work"
    work.mkdir()
    (work / ".importlinter").write_text(
        artifact.block.render("", artifact.content), encoding="utf-8"
    )
    for relative, text in files.items():
        path = work / "src" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    monkeypatch.chdir(work)
    monkeypatch.syspath_prepend(str(work / "src"))
    return importlinter_cli.lint_imports(config_filename=str(work / ".importlinter"))


def test_a_fresh_package_keeps_the_layers_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _lint_demo(
        tmp_path, monkeypatch, {"demo/__init__.py": "", "demo/commands.py": ""}
    )
    assert result == 0


def test_services_importing_adapters_breaks_the_layers_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _lint_demo(
        tmp_path,
        monkeypatch,
        {
            "demo/__init__.py": "",
            "demo/services/__init__.py": "",
            "demo/services/use.py": "import demo.adapters.store\n",
            "demo/adapters/__init__.py": "",
            "demo/adapters/store.py": "",
        },
    )
    assert result != 0


def test_domain_importing_an_entry_point_breaks_the_layers_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _lint_demo(
        tmp_path,
        monkeypatch,
        {
            "demo/__init__.py": "",
            "demo/commands.py": "",
            "demo/domain/__init__.py": "",
            "demo/domain/rule.py": "import demo.commands\n",
        },
    )
    assert result != 0


def test_an_entry_point_importing_domain_keeps_the_layers_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _lint_demo(
        tmp_path,
        monkeypatch,
        {
            "demo/__init__.py": "",
            "demo/commands.py": "import demo.domain.rule\n",
            "demo/domain/__init__.py": "",
            "demo/domain/rule.py": "",
        },
    )
    assert result == 0


def test_python_lib_renders_no_layers_contract(tmp_path: Path) -> None:
    config = KilnConfig.load(_root(tmp_path, "python-lib"))
    [artifact] = _importlinter(config, tmp_path)
    assert "dependencies-point-inward" not in artifact.content
    assert "type = layers" not in artifact.content


def test_the_web_archetypes_render_it_for_their_api_member(tmp_path: Path) -> None:
    root = _web_root(tmp_path, "python-web-api", "fastapi")
    [artifact] = PYTHON.artifacts(KilnConfig.load(root), root)
    assert "[importlinter:contract:dependencies-point-inward]" in artifact.content
    assert "containers =\n    demo_api\n" in artifact.content


def test_the_layers_contract_renders_whatever_the_docs_profile(
    tmp_path: Path,
) -> None:
    write_config(tmp_path, "python-app", name="demo", docs="none")
    config = KilnConfig.load(tmp_path)
    [artifact] = _importlinter(config, tmp_path)
    assert "[importlinter:contract:dependencies-point-inward]" in artifact.content
    assert "containers =\n    demo\n" in artifact.content


FRAMEWORK_CONTRACT = "framework-stays-at-the-edge"
FRAMEWORK_CONTRACT_NAME = "demo_api's domain and services import no web framework"


def _lint_demo_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    files: dict[str, str],
) -> tuple[int, str]:
    """Render `.importlinter` for a FastAPI `demo_api`, build the package and lint it."""
    from importlinter import cli as importlinter_cli

    config_root = tmp_path / "config"
    root = _web_root(config_root, "python-web-api", "fastapi")
    config = KilnConfig.load(root)
    [artifact] = PYTHON.artifacts(config, root)
    assert artifact.block is not None
    work = tmp_path / "work"
    work.mkdir()
    (work / ".importlinter").write_text(
        artifact.block.render("", artifact.content), encoding="utf-8"
    )
    for relative, text in files.items():
        path = work / "src" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    monkeypatch.chdir(work)
    monkeypatch.syspath_prepend(str(work / "src"))
    capfd.readouterr()
    result = importlinter_cli.lint_imports(config_filename=str(work / ".importlinter"))
    return result, capfd.readouterr().out


def _broken_contracts(output: str) -> list[str]:
    return [line for line in output.splitlines() if "BROKEN" in line]


def test_a_fresh_api_package_keeps_the_framework_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    result, _ = _lint_demo_api(
        tmp_path,
        monkeypatch,
        capfd,
        {"demo_api/__init__.py": "", "demo_api/app.py": ""},
    )
    assert result == 0


def test_domain_importing_fastapi_breaks_the_framework_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    result, output = _lint_demo_api(
        tmp_path,
        monkeypatch,
        capfd,
        {
            "demo_api/__init__.py": "",
            "demo_api/domain/__init__.py": "",
            "demo_api/domain/rule.py": "import fastapi\n",
        },
    )
    assert result != 0
    [broken] = _broken_contracts(output)
    assert FRAMEWORK_CONTRACT_NAME in broken


def test_services_importing_starlette_breaks_the_framework_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    result, output = _lint_demo_api(
        tmp_path,
        monkeypatch,
        capfd,
        {
            "demo_api/__init__.py": "",
            "demo_api/services/__init__.py": "",
            "demo_api/services/use.py": "import starlette\n",
        },
    )
    assert result != 0
    [broken] = _broken_contracts(output)
    assert FRAMEWORK_CONTRACT_NAME in broken


def test_http_importing_fastapi_keeps_the_framework_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    result, _ = _lint_demo_api(
        tmp_path,
        monkeypatch,
        capfd,
        {
            "demo_api/__init__.py": "",
            "demo_api/http/__init__.py": "",
            "demo_api/http/items.py": "import fastapi\n",
        },
    )
    assert result == 0


def test_only_fastapi_cells_carry_the_framework_contract(tmp_path: Path) -> None:
    marker = f"[importlinter:contract:{FRAMEWORK_CONTRACT}]"
    api = _web_root(tmp_path / "api", "python-web-api", "fastapi")
    [artifact] = PYTHON.artifacts(KilnConfig.load(api), api)
    assert marker in artifact.content
    django = _web_root(
        tmp_path / "django", "python-web-app", "django", extra='frontend = "angular"'
    )
    [artifact] = PYTHON.artifacts(KilnConfig.load(django), django)
    assert marker not in artifact.content
    app = _root(tmp_path / "app", "python-app")
    [artifact] = _importlinter(KilnConfig.load(app), app)
    assert marker not in artifact.content
