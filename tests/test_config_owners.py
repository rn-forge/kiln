"""`KilnConfig` is the one owner of the section, archetype and name answers."""

from __future__ import annotations

from pathlib import Path

import pytest
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.config import CiConfig
from rn_forge.kiln.modules.core.config.schema import KilnPin
from rn_forge.kiln.modules.docs.config import DocsConfig
from rn_forge.kiln.modules.tasks.config import TasksConfig
from tests.conftest import write_config

SRC = Path(__file__).resolve().parents[1] / "src" / "rn_forge" / "kiln"


def test_s18_7_1_1_only_config_reads_the_document_by_getattr() -> None:
    offenders = sorted(
        path.relative_to(SRC).as_posix()
        for path in SRC.rglob("*.py")
        if path != SRC / "config.py"
        and any(
            needle in path.read_text(encoding="utf-8")
            for needle in ("getattr(config.document", "getattr(self.document")
        )
    )
    assert offenders == []


def test_s18_7_1_2_sections_default_as_today(tmp_path: Path) -> None:
    write_config(tmp_path, "python-tool", tail='\n[kiln]\nref = "v1.2.3"\n')
    config = KilnConfig.load(tmp_path)
    assert config.ci == CiConfig()
    assert config.docs == DocsConfig()
    assert config.tasks == TasksConfig()
    assert config.kiln_pin == KilnPin(ref="v1.2.3")


CELLS = [
    ("python-app", {}, (False, False, False, False, (), None, None)),
    (
        "python-lib",
        {"packages": ["packages/a"]},
        (True, False, False, False, ("packages/a",), None, None),
    ),
    (
        "python-web-api",
        {"backend": "fastapi"},
        (False, True, False, False, (), "demo-api", "demo_api"),
    ),
    (
        "python-web-app",
        {"backend": "fastapi", "frontend": "angular"},
        (False, True, True, False, (), "demo-api", "demo_api"),
    ),
    ("node-lib", {}, (False, False, False, True, (), None, None)),
    ("python-tool", {}, (False, False, False, False, (), None, None)),
]


@pytest.mark.parametrize(("archetype", "extra", "expected"), CELLS)
def test_s18_7_1_3_archetype_answers(
    tmp_path: Path,
    archetype: str,
    extra: dict[str, object],
    expected: tuple[object, ...],
) -> None:
    write_config(tmp_path, archetype, name="demo", **extra)  # type: ignore[arg-type]
    config = KilnConfig.load(tmp_path)
    assert (
        config.is_workspace,
        config.is_web,
        config.is_web_app,
        config.is_node_lib,
        config.docs_packages,
        config.api_package,
        config.api_module,
    ) == expected


def test_s18_7_1_4_module_name_is_the_one_conversion() -> None:
    from rn_forge.kiln.modules.core.names import module_name
    from rn_forge.kiln.modules.python import artifacts

    assert module_name("rn-forge-cli") == "rn_forge_cli"
    assert not hasattr(artifacts, "root_package")


def test_s18_7_1_5_web_project_keeps_both_answers(tmp_path: Path) -> None:
    from rn_forge.kiln.modules.cicd import artifacts

    write_config(
        tmp_path,
        "python-web-app",
        name="demo",
        backend="fastapi",
        frontend="angular",
        tail='web_dir = "apps/portal"\n',
    )
    # F18.10 makes the tasks and cicd Nx project names one.
    assert KilnConfig.load(tmp_path).web_project == "portal"
    assert artifacts._WEB_PROJECT == "web"  # noqa: SLF001
