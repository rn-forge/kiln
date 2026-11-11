"""S19.1.2: a fresh render of every archetype is formatter-clean."""

import os
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FEATURE = ROOT / "docs/specs/epics/E19-formatting-standard/F19.1-yaml-formatter.md"
BIN = Path(sys.executable).parent
ARCHETYPES = [
    "python-app",
    "python-tool",
    "python-lib",
    "python-web-api",
    "python-web-app",
    "node-lib",
]
PRUNED = {
    ".git",
    "node_modules",
    ".venv",
    ".uv-cache",
    ".nx",
    ".angular",
    "dist",
    "coverage",
    ".docs-site",
    ".pytest_cache",
}
# kiln's own copies; the rendered `.gitignore` ignores them, so no task sees them.
IGNORED = (".rn-forge/kiln/backups", ".rn-forge/kiln/rendered")


def _settled() -> tuple[dict[str, str], str]:
    _, _, rest = FEATURE.read_text(encoding="utf-8").partition("### Settled by S19.1.1")
    rows: dict[str, str] = {}
    lines = rest.splitlines()
    end = 0
    for i, line in enumerate(lines):
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells[0] not in ("Key", "--"):
                rows[cells[0]] = cells[1]
            end = i + 1
        elif rows:
            break
    block = "\n".join(lines[end:]).lstrip().removeprefix("```yaml\n")
    return rows, block.partition("```")[0]


_ROWS, YAML_CONFIG = _settled()
YAML_PACKAGE = _ROWS["Package"].strip("`")
YAML_EXECUTABLE = _ROWS["Executable"].strip("`")
YAML_CHECK = tuple(_ROWS["Check command"].strip("`").split()[1:])
YAML_CONFIG_FILE = _ROWS["Config file"].strip("`")
PACKAGE_MANAGER_FILES = {
    Path(p.strip().strip("`")).name for p in _ROWS["Excluded files"].split(",")
}


def _files(root: Path, *suffixes: str) -> list[str]:
    found = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in PRUNED]
        for name in names:
            relative = str((Path(base) / name).relative_to(root))
            if name.endswith(suffixes) and not relative.startswith(IGNORED):
                found.append(relative)
    return sorted(found)


def _run(root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s19_1_2_1_rendered_markdown_is_mdformat_clean(
    archetype: str, rendered: Callable[[str], Path]
) -> None:
    root = rendered(archetype)
    done = _run(
        root, [sys.executable, "-m", "mdformat", "--check", *_files(root, ".md")]
    )
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s19_1_2_2_rendered_toml_is_taplo_clean(
    archetype: str, rendered: Callable[[str], Path]
) -> None:
    root = rendered(archetype)
    done = _run(
        root,
        [str(BIN / "taplo"), "fmt", "--check", "--diff", *_files(root, ".toml")],
    )
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s19_1_2_3_rendered_yaml_is_clean(
    archetype: str, rendered: Callable[[str], Path], tmp_path: Path
) -> None:
    root = rendered(archetype)
    (tmp_path / YAML_CONFIG_FILE).write_text(YAML_CONFIG, encoding="utf-8")
    names = [
        n
        for n in _files(root, ".yml", ".yaml")
        if Path(n).name not in PACKAGE_MANAGER_FILES
    ]
    for name in names:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, tmp_path / name)
    done = _run(tmp_path, [str(BIN / YAML_EXECUTABLE), *YAML_CHECK, *names])
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s19_1_2_4_the_lists_are_not_empty(
    archetype: str, rendered: Callable[[str], Path]
) -> None:
    root = rendered(archetype)
    assert "README.md" in _files(root, ".md")
    assert ".taplo.toml" in _files(root, ".toml")
    assert {"Taskfile.yml", "tasks/quality.yml", ".github/workflows/ci.yml"} <= set(
        _files(root, ".yml")
    )


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def test_s19_1_2_5_the_tools_are_locked() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    entries = [
        e
        for e in project["dependency-groups"]["dev"]
        if e.startswith(YAML_PACKAGE + ">=")
    ]
    assert len(entries) == 1
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked = {p["name"]: p["version"] for p in lock["package"]}
    floor = entries[0].split(">=")[1]
    assert _version_key(floor) <= _version_key(locked[YAML_PACKAGE])
