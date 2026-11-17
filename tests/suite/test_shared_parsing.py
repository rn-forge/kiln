"""S18.7.3 — shared parsing has one implementation."""

from __future__ import annotations

import ast
from pathlib import Path

import rn_forge.kiln as kiln_package
from rn_forge.kiln.devops.ci import normalize, requirement_name

KILN = Path(kiln_package.__file__).parent
MODULES = KILN / "modules"
COMMANDS = KILN / "commands"


def _python_files(*roots: Path) -> list[Path]:
    return sorted(p for root in roots for p in root.rglob("*.py"))


def _defined_names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def test_s18_7_3_1_subprocess_only_in_the_process_helper() -> None:
    helper = MODULES / "core" / "process.py"
    importers: list[str] = []
    executors: list[str] = []
    for path in _python_files(MODULES, COMMANDS):
        text = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import) and any(
                alias.name == "subprocess" for alias in node.names
            ):
                importers.append(str(path))
            elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
                importers.append(str(path))
        if "Process.execute(" in text and path != helper:
            executors.append(str(path))
    assert importers == []
    assert executors == []
    assert helper.is_file()


def test_s18_7_3_2_one_step_scanner() -> None:
    from rn_forge.kiln.modules.core.steps import step_commands

    lines = ["- run: task a", "  run: |", "    task b", "    task c", "- name: x"]
    assert step_commands(lines, ("run",)) == [
        (1, "task a"),
        (3, "    task b"),
        (4, "    task c"),
    ]
    for path in (
        MODULES / "tasks" / "checks" / "layout.py",
        MODULES / "cicd" / "checks" / "entrypoint.py",
    ):
        assert not {"_RUN_LINE", "STEP_LINE", "BLOCK_SCALAR", "_BLOCK_SCALAR"} & (
            _defined_names(path)
        )


def test_s18_7_3_3_one_docs_helper_each() -> None:
    from rn_forge.kiln.modules.docs import packages, pages, parsed, work
    from rn_forge.kiln.modules.docs.findings import error

    assert callable(error)
    assert callable(parsed.local_links)
    assert callable(pages.content_pages)
    assert callable(pages.nav_pages)
    assert callable(work.feature_sort_key)
    assert callable(packages.project_urls)

    # Copies left under the merge rule, if any, are listed here with a reason.
    allowed: dict[str, set[str]] = {}
    gone = {"_error", "_content_pages", "_is_page", "_nav_names", "_FEATURE_FILE_RE"}
    for path in _python_files(MODULES / "docs"):
        assert not (gone & _defined_names(path) - allowed.get(path.name, set())), path


def test_s18_7_3_4_devops_names_follow_packaging() -> None:
    assert normalize("Foo_Bar.baz") == "foo-bar-baz"
    assert requirement_name("Foo_Bar[x]>=1; python_version>'3'") == "foo-bar"
