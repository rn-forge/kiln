"""S5.3.6 — `.gitignore` is uv's body, then Nx's, then kiln's one block.

Offline: the upstream bodies are the captured fixtures under
`tests/fixtures/scaffold/`. The live capture that proves the uv fixture's
provenance is in `tests/modules/python/test_scaffold.py`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle, gitignore
from rn_forge.kiln.modules.core.artifacts import GITIGNORE_BLOCK, render

SCAFFOLD = Path(__file__).resolve().parents[2] / "fixtures" / "scaffold"
UV_BODY = (SCAFFOLD / "uv" / ".gitignore").read_text(encoding="utf-8")
NX_BODY = (SCAFFOLD / "nx-angular" / ".gitignore").read_text(encoding="utf-8")

CONFIG = 'schema_version = 1\n\n[repository]\nname = "demo"\narchetype = "python-app"\n'


def _kiln_body(root: Path) -> str:
    (artifact,) = [a for a in render(KilnConfig.load(root)) if a.path == ".gitignore"]
    return artifact.content


@pytest.fixture
def root(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    config = repo / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG, encoding="utf-8")
    return repo


def _compose(root: Path, *bodies: str) -> None:
    for body in bodies:
        gitignore.append(root, body)


def test_s5_3_6_1_composition_is_uv_then_nx_then_kiln(root: Path) -> None:
    _compose(root, UV_BODY, NX_BODY)
    cycle.apply(root, home=root.parent / "home")

    text = (root / ".gitignore").read_text(encoding="utf-8")
    expected = GITIGNORE_BLOCK.render(
        UV_BODY + "\n" + NX_BODY.rstrip("\n") + "\n", _kiln_body(root)
    )
    assert text == expected
    assert text.index("__pycache__/") < text.index("node_modules")
    assert text.index("node_modules") < text.index("# BEGIN rn-forge kiln")


def test_s5_3_6_1_without_a_frontend_it_is_uv_then_kiln(root: Path) -> None:
    _compose(root, UV_BODY)
    cycle.apply(root, home=root.parent / "home")

    text = (root / ".gitignore").read_text(encoding="utf-8")
    assert text == GITIGNORE_BLOCK.render(UV_BODY, _kiln_body(root))
    assert text.count("# Python-generated files") == 1


def test_s5_3_6_2_negations_keep_their_order(root: Path) -> None:
    _compose(root, UV_BODY, NX_BODY)
    lines = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    start = lines.index(".vscode/*")
    assert lines[start : start + 5] == [
        ".vscode/*",
        "!.vscode/settings.json",
        "!.vscode/tasks.json",
        "!.vscode/launch.json",
        "!.vscode/extensions.json",
    ]


@pytest.mark.parametrize(
    "body",
    [
        "dist\n!dist/keep",  # no final newline
        "dist\r\n!dist/keep\r\n",  # CRLF
        "\n\ndist\n!dist/keep\n\n\n",  # blank padding
    ],
)
def test_s5_3_6_2_upstream_bodies_are_normalized_not_rewritten(
    root: Path, body: str
) -> None:
    _compose(root, "# uv\n.venv", body)
    assert (root / ".gitignore").read_text(encoding="utf-8") == (
        "# uv\n.venv\n\ndist\n!dist/keep\n"
    )


def test_s5_3_6_2_an_empty_body_adds_no_section(root: Path) -> None:
    _compose(root, UV_BODY, "\n\n")
    assert (root / ".gitignore").read_text(encoding="utf-8") == UV_BODY


def test_s5_3_6_2_two_applies_keep_bodies_and_user_rules_with_one_block(
    root: Path,
) -> None:
    home = root.parent / "home"
    _compose(root, UV_BODY, NX_BODY)
    cycle.apply(root, home=home)
    path = root / ".gitignore"
    path.write_text(path.read_text(encoding="utf-8") + "\nsecrets.env\n", "utf-8")
    before = path.read_text(encoding="utf-8")

    cycle.apply(root, home=home)
    after_first = path.read_text(encoding="utf-8")
    cycle.apply(root, home=home)

    assert after_first == before
    assert path.read_text(encoding="utf-8") == before
    assert before.startswith(UV_BODY)
    assert before.count("# BEGIN rn-forge kiln") == 1
    assert before.endswith("secrets.env\n")


IGNORED = (
    ".venv/bin/python",
    "apps/api/.venv/bin/python",
    "__pycache__/x.pyc",
    "apps/api/src/demo_api/__pycache__/x.pyc",
    "apps/api/src/demo_api/x.pyc",
    "build/x",
    "apps/api/build/x",
    "dist/x.whl",
    "apps/api/dist/x.whl",
    "wheels/x.whl",
    "apps/api/src/demo_api.egg-info/PKG-INFO",
    ".pytest_cache/x",
    "apps/api/.pytest_cache/x",
    ".ruff_cache/x",
    "apps/api/.ruff_cache/x",
    ".import_linter_cache/x",
    ".uv-cache/x",
    "apps/api/.uv-cache/x",
    ".coverage",
    ".coverage.host.1",
    "coverage.xml",
    ".docs-site/index.html",
    "site/index.html",
    ".rn-forge/kiln/backups/x",
    ".rn-forge/kiln/rendered/x",
    ".rn-forge/kiln/state.lock",
)

TRACKED = (
    "pyproject.toml",
    "uv.lock",
    "apps/api/pyproject.toml",
    "apps/api/src/demo_api/__init__.py",
    "apps/api/src/demo_api/app.py",
    "apps/api/tests/test_app.py",
    "demo.code-workspace",
    ".rn-forge/kiln/config.toml",
    ".rn-forge/kiln/state.json",
    ".vscode/extensions.json",
)


@pytest.mark.parametrize("bodies", [(UV_BODY,), (UV_BODY, NX_BODY)])
def test_s5_3_6_3_check_ignore_covers_outputs_and_leaves_sources(
    root: Path, bodies: tuple[str, ...]
) -> None:
    _compose(root, *bodies)
    cycle.apply(root, home=root.parent / "home")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)

    def ignored(path: str) -> bool:
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", path], cwd=root, check=False
        )
        return result.returncode == 0

    assert [p for p in IGNORED if not ignored(p)] == []
    assert [p for p in TRACKED if ignored(p)] == []
