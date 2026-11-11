"""kiln's packaged CLI declaration matches the one in its own config.

kiln declares its command line twice — in `.rn-forge/kiln/config.toml`, like
every rn-forge repo, and in `src/rn_forge/kiln/cli.toml`, which is what an
installed kiln reads (see that file's header). Two copies with nothing
comparing them is how a repo ends up with one of them wrong, so this compares
them. F4.8 makes one render the other, and this test goes away with the copy.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest
from rn_forge.kiln import commands
from rn_forge.kiln.modules.python import scaffold as python_scaffold

ROOT = Path(__file__).resolve().parents[1]


def _table(path: Path, key: str) -> dict[str, object]:
    return tomllib.loads(path.read_text(encoding="utf-8"))[key]


def test_packaged_surface_matches_repo_config() -> None:
    packaged = _table(ROOT / "src" / "rn_forge" / "kiln" / "cli.toml", "cli")
    declared = _table(ROOT / ".rn-forge" / "kiln" / "config.toml", "cli")
    assert packaged == declared


def test_s4_5_5_packaged_lifecycle_matches_repo_config() -> None:
    packaged = _table(ROOT / "src" / "rn_forge" / "kiln" / "cli.toml", "lifecycle")
    declared = _table(ROOT / ".rn-forge" / "kiln" / "config.toml", "lifecycle")
    assert packaged == declared


def test_s13_1_1_6_the_cli_has_docs_generate_and_no_other_docs_command() -> None:
    names = [
        command["name"]
        for command in _table(ROOT / ".rn-forge" / "kiln" / "config.toml", "cli")[
            "commands"
        ]
    ]
    assert [name for name in names if name.startswith("docs-")] == ["docs-generate"]


@pytest.mark.parametrize(
    "path",
    [
        ROOT / "src" / "rn_forge" / "kiln" / "cli.toml",
        ROOT / ".rn-forge" / "kiln" / "config.toml",
    ],
)
def test_s16_8_1_1_init_is_not_a_command(path: Path) -> None:
    names = [command["name"] for command in _table(path, "cli")["commands"]]
    assert "init" not in names
    assert not hasattr(commands, "init")
    assert "init" not in commands.__all__


_GONE_FROM_COMMANDS = (
    "_final_steps",
    "_run_task",
    "_missing_seeds",
    "_seed_rows",
    "_seed",
    "_ALWAYS_REPLACED",
    "_EPICS_INDEX",
    "_EPIC_ROW",
    "_has_content",
    "_replaced_seeds",
    "_dedupe_gitignore",
    "_surviving_group",
    "_require_packages",
    "_require_clean",
    "_git_remote_name",
    "_origin_owner",
    "_init_name",
    "_init_preflight",
    "_INIT_FILES",
    "_own_name",
    "_canonical",
    "_project_name",
    "_archive",
)


def test_s16_8_1_3_adoption_helpers_are_gone() -> None:
    assert [name for name in _GONE_FROM_COMMANDS if hasattr(commands, name)] == []
    assert importlib.util.find_spec("rn_forge.kiln.modules.core.remote") is None
    assert not hasattr(python_scaffold, "add_task_tools")
    assert not hasattr(python_scaffold, "missing_task_tools")


def test_s16_8_1_4_no_source_mentions_init() -> None:
    source = ROOT / "src" / "rn_forge" / "kiln"
    hits = [
        str(path.relative_to(ROOT))
        for pattern in ("*.py", "*.j2", "*.toml")
        for path in source.rglob(pattern)
        if "kiln init" in path.read_text(encoding="utf-8")
    ]
    assert hits == []


def test_s16_8_3_3_no_source_names_the_adopt_prompt() -> None:
    pattern = re.compile(r"kiln prompt (--name )?adopt|prompts/adopt")
    source = ROOT / "src" / "rn_forge" / "kiln"
    hits = [
        str(path.relative_to(ROOT))
        for path in source.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and pattern.search(path.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert hits == []


def test_s16_9_7_1_the_default_log_level_is_info() -> None:
    from rn_forge.cli import CliSurface
    from rn_forge.cli.options import LogLevel
    from rn_forge.commons.fs.documents import DocumentUtils

    surface = CliSurface.load(
        DocumentUtils.read(ROOT / "src" / "rn_forge" / "kiln" / "cli.toml"),
        key="cli",
    )

    assert surface.default_log_level is LogLevel.INFO


def test_s16_9_7_2_apply_prints_no_verbose_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rendered: Callable[[str], Path],
    capfd: pytest.CaptureFixture[str],
) -> None:
    from rn_forge.kiln import main

    root = tmp_path / "repo"
    shutil.copytree(
        rendered("python-tool"),
        root,
        ignore=shutil.ignore_patterns(".venv", ".uv-cache", ".git", "__pycache__"),
    )
    monkeypatch.chdir(root)

    code = main.app(["apply", "--dry-run"])

    captured = capfd.readouterr()
    output = captured.out + captured.err
    assert code == 0
    assert "read_file" not in output
