"""S4.3.5 — the scaffolded bodies of `README.md`, `CLAUDE.md` and `AGENTS.md`."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.instructions.scaffold import scaffold

ARCHETYPES = ("python-app", "python-tool", "python-lib")

CONFIG = 'schema_version = 1\n\n[repository]\nname = "demo"\nowner = "rn-forge"\narchetype = "python-app"\n'

README = """# demo

What this repository is, in a paragraph.

## Working here

- Run everything through `task`. `task validate` is the gate.
- A file whose first line says it was generated is owned by kiln: edit
  `.rn-forge/kiln/config.toml` and run `task kiln:apply`, never the file. The
  standard is [.rn-forge/kiln/standard.md](.rn-forge/kiln/standard.md).

## Conventions

- Python 3.14, `src/` layout, pyright strict, ruff for lint and format.
"""

CLAUDE = """@AGENTS.md

## Claude-only

Instructions that only Claude Code should follow go here. Everything every agent
should follow is in [AGENTS.md](AGENTS.md).
"""

AGENTS = """# AGENTS.md

What this repository is, how to set it up and the conventions everyone follows
are in [README.md](README.md). This file holds what an agent needs beyond that.

## Rules

- Replace this line with a rule every agent must follow in this repository.

## Guardrails

- Replace this line with something an agent must not do without asking.

## Do and don't

- Do: replace this line.
- Don't: replace this line.

## Examples

Replace this section with one worked example of a change made the way this
repository wants it.

## Story workflow

Replace this section with how a story is picked up, built, checked and handed
back in this repository.
"""

BULLETS = (
    "- Run everything through `task`. `task validate` is the gate.\n",
    "- A file whose first line says it was generated is owned by kiln: edit\n"
    "  `.rn-forge/kiln/config.toml` and run `task kiln:apply`, never the file. The\n"
    "  standard is [.rn-forge/kiln/standard.md](.rn-forge/kiln/standard.md).\n",
)


def _root(tmp_path: Path) -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    return tmp_path


def test_s4_3_5_scaffold_writes_the_three_bodies(tmp_path: Path) -> None:
    root = _root(tmp_path)
    scaffold(root, KilnConfig.load(root))
    assert (root / "README.md").read_text(encoding="utf-8") == README
    assert (root / "AGENTS.md").is_file()


def test_s4_3_5_scaffold_never_overwrites_a_present_body(tmp_path: Path) -> None:
    root = _root(tmp_path)
    for name in ("README.md", "CLAUDE.md", "AGENTS.md"):
        (root / name).write_text("mine\n", encoding="utf-8")
    scaffold(root, KilnConfig.load(root))
    for name in ("README.md", "CLAUDE.md", "AGENTS.md"):
        assert (root / name).read_text(encoding="utf-8") == "mine\n"


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s4_3_5_readme_bullets_appear_verbatim_in_every_rendered_readme(
    archetype: str, rendered: Callable[[str], Path]
) -> None:
    text = (rendered(archetype) / "README.md").read_text(encoding="utf-8")
    for bullet in BULLETS:
        assert bullet in README
        assert bullet in text


def test_s4_3_5_readme_is_mdformat_clean(
    tmp_path: Path, rendered: Callable[[str], Path]
) -> None:
    """Formatted under the `.mdformat.toml` a rendered repo carries."""
    root = _root(tmp_path)
    scaffold(root, KilnConfig.load(root))
    (root / ".mdformat.toml").write_bytes(
        (rendered("python-app") / ".mdformat.toml").read_bytes()
    )
    result = subprocess.run(
        [sys.executable, "-m", "mdformat", "--check", "README.md"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


WEB_CONFIG = """schema_version = 1

[repository]
name = "{name}"
owner = "rn-forge"
archetype = "python-web-api"

[archetype."python-web-api"]
backend = "fastapi"
{extra}
"""


def _mdformat_check(
    root: Path, rendered: Callable[[str], Path]
) -> subprocess.CompletedProcess[str]:
    (root / ".mdformat.toml").write_bytes(
        (rendered("python-app") / ".mdformat.toml").read_bytes()
    )
    return subprocess.run(
        [sys.executable, "-m", "mdformat", "--check", "README.md"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("name", "extra", "app_path"),
    [
        ("demo", "", "apps/api/src/demo_api/app.py"),
        (
            "a-rather-long-repository-name",
            'api_dir = "services/backend-api"',
            "services/backend-api/src/a_rather_long_repository_name_api/app.py",
        ),
    ],
)
def test_s5_3_6_8_web_readme_names_the_api_path_and_is_mdformat_clean(
    tmp_path: Path,
    name: str,
    extra: str,
    app_path: str,
    rendered: Callable[[str], Path],
) -> None:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(WEB_CONFIG.format(name=name, extra=extra), encoding="utf-8")
    scaffold(tmp_path, KilnConfig.load(tmp_path))

    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert f"`{app_path}`" in readme
    assert "`task api:dev`" in readme
    assert "`app`" in readme
    assert "repo-owned" in readme
    result = _mdformat_check(tmp_path, rendered)
    assert result.returncode == 0, result.stdout + result.stderr


FASTAPI_MODULE = """The smallest such module uses `rn-forge-fastapi`'s standard application:

```python
from rn_forge.fastapi import AppConfig, FastApiApp

app = FastApiApp(AppConfig())
```
"""


def test_s5_3_7_1_fastapi_readme_shows_the_standard_module(
    tmp_path: Path, rendered: Callable[[str], Path]
) -> None:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(WEB_CONFIG.format(name="demo", extra=""), encoding="utf-8")
    scaffold(tmp_path, KilnConfig.load(tmp_path))

    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert FASTAPI_MODULE in readme
    before, after = readme.split(FASTAPI_MODULE)
    assert before.endswith("are repo-owned from then on.\n\n")
    assert "create that module yourself" not in readme
    assert "seeded it with a small router and a test" in readme.replace("\n", " ")
    assert after.startswith("\n## Conventions")
    result = _mdformat_check(tmp_path, rendered)
    assert result.returncode == 0, result.stdout + result.stderr


def test_s5_3_7_2_django_readme_has_no_fastapi_module(
    tmp_path: Path, rendered: Callable[[str], Path]
) -> None:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        WEB_CONFIG.format(name="demo", extra="").replace(
            'backend = "fastapi"', 'backend = "django"'
        ),
        encoding="utf-8",
    )
    scaffold(tmp_path, KilnConfig.load(tmp_path))

    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "## Running the API" in readme
    assert "rn_forge.fastapi" not in readme
    result = _mdformat_check(tmp_path, rendered)
    assert result.returncode == 0, result.stdout + result.stderr


def test_s5_3_6_8_non_web_readme_has_no_api_section(tmp_path: Path) -> None:
    root = _root(tmp_path)
    scaffold(root, KilnConfig.load(root))
    assert "api:dev" not in (root / "README.md").read_text(encoding="utf-8")


def test_s16_10_2_1_claude_md_is_the_import_and_a_claude_only_stub(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    scaffold(root, KilnConfig.load(root))
    assert (root / "CLAUDE.md").read_text(encoding="utf-8") == CLAUDE


def test_s16_10_2_2_agents_md_is_a_skeleton_that_links_readme(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    scaffold(root, KilnConfig.load(root))
    assert (root / "AGENTS.md").read_text(encoding="utf-8") == AGENTS


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_s16_10_2_3_readme_carries_no_agent_directive(
    archetype: str, rendered: Callable[[str], Path]
) -> None:
    text = (rendered(archetype) / "README.md").read_text(encoding="utf-8")
    assert "CLAUDE.md" not in text
    assert "AGENTS.md" not in text
    assert "agent" not in text.lower()


STANDARD_ARCHETYPES = (
    "python-app",
    "python-tool",
    "python-lib",
    "python-web-api",
    "python-web-app",
    "node-lib",
)


FLAGS = {
    "python-web-api": {"backend": "fastapi"},
    "python-web-app": {"backend": "fastapi", "frontend": "angular"},
}


def _cell(
    archetype: str, profile: str, tmp_path: Path, rendered: Callable[[str], Path]
) -> Path:
    if profile == "mkdocs":
        return rendered(archetype)
    from rn_forge.kiln import commands

    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(tmp_path)
        commands.new(
            Path(archetype),
            archetype=archetype,
            docs="none",
            owner="rn-forge",
            yes=True,
            **FLAGS.get(archetype, {}),
        )
    return tmp_path / archetype


@pytest.mark.parametrize("profile", ["mkdocs", "none"])
@pytest.mark.parametrize("archetype", STANDARD_ARCHETYPES)
def test_s16_9_12_1_standard_is_mdformat_clean(
    archetype: str,
    profile: str,
    tmp_path: Path,
    rendered: Callable[[str], Path],
) -> None:
    cell = _cell(archetype, profile, tmp_path, rendered)
    root = tmp_path / "check"
    (root / ".rn-forge" / "kiln").mkdir(parents=True)
    (root / ".mdformat.toml").write_bytes((cell / ".mdformat.toml").read_bytes())
    (root / ".rn-forge" / "kiln" / "standard.md").write_bytes(
        (cell / ".rn-forge" / "kiln" / "standard.md").read_bytes()
    )
    result = subprocess.run(
        [sys.executable, "-m", "mdformat", "--check", ".rn-forge/kiln/standard.md"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_s16_9_12_2_seeded_mdformat_config_has_no_exclude(
    rendered: Callable[[str], Path],
) -> None:
    text = (rendered("python-tool") / ".mdformat.toml").read_text(encoding="utf-8")
    assert "standard.md" not in text
    assert set(tomllib.loads(text)) == {"wrap", "plugin"}
