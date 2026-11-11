"""Tests for `kiln-devops site-assemble` (S9.4.2)."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from rn_forge.kiln.devops import cli

FIXTURE = Path(__file__).parent / "fixtures" / "site" / "index.html"


def _stub_pnpm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **targets: str) -> None:
    """A `pnpm` on PATH that serves `nx show` JSON; `targets` maps a target to its projects."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "pnpm"
    cases = "".join(
        f"  \"exec nx show projects --json --with-target {target}\") echo '{projects}' ;;\n"
        for target, projects in targets.items()
    )
    script.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        f"{cases}"
        '  "exec nx show project core --json") echo \'{"root": "libs/core"}\' ;;\n'
        '  "exec nx show project ui --json") echo \'{"root": "libs/ui"}\' ;;\n'
        "  \"exec nx show projects --json --with-target \"*) echo '[]' ;;\n"
        "esac\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    for path, text in {
        "libs/core/package.json": json.dumps({"description": 'Core & <lib> "x"'}),
        "libs/ui/package.json": json.dumps({"name": "ui"}),
        "dist/compodoc/core/index.html": "a",
        "dist/compodoc/ui/index.html": "b",
        "dist/storybook/ui/index.html": "c",
    }.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    return root


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *args: str,
    compodoc: str = "[]",
    storybook: str = "[]",
) -> Path:
    root = _workspace(tmp_path)
    _stub_pnpm(
        tmp_path, monkeypatch, compodoc=compodoc, **{"build-storybook": storybook}
    )
    monkeypatch.chdir(root)
    assert cli.main(["site-assemble", *args]) == 0
    return root


def _existing(root: Path) -> None:
    (root / ".docs-site").mkdir()
    (root / ".docs-site" / "index.html").write_text("mkdocs")
    (root / ".docs-site" / "guide.html").write_text("guide")


def test_s9_4_2_1_site_dir_is_the_first_argument(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _run(tmp_path, monkeypatch, ".docs-site")
    assert (root / ".docs-site" / "index.html").is_file()
    assert not (root / "dist" / "site").exists()


def test_s9_4_2_1_the_default_site_dir_is_dist_site(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _run(tmp_path, monkeypatch)
    assert (root / "dist" / "site" / "index.html").is_file()


def test_s9_4_2_1_existing_content_and_index_are_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _workspace(tmp_path)
    _existing(root)
    _stub_pnpm(tmp_path, monkeypatch, compodoc="[]", **{"build-storybook": "[]"})
    monkeypatch.chdir(root)
    assert cli.main(["site-assemble", ".docs-site"]) == 0
    site = root / ".docs-site"
    assert (site / "index.html").read_text() == "mkdocs"
    assert (site / "guide.html").read_text() == "guide"
    assert (site / ".nojekyll").is_file()


def test_s9_4_2_1_no_doc_target_keeps_index_and_makes_no_subsites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _workspace(tmp_path)
    _existing(root)
    _stub_pnpm(tmp_path, monkeypatch, compodoc="[]", **{"build-storybook": "[]"})
    monkeypatch.chdir(root)
    assert cli.main(["site-assemble", ".docs-site"]) == 0
    site = root / ".docs-site"
    assert (site / "index.html").read_text() == "mkdocs"
    assert (site / ".nojekyll").is_file()
    assert not (site / "api").exists()
    assert not (site / "storybook").exists()


def test_s9_4_2_2_a_relative_site_dir_resolves_against_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _run(tmp_path, monkeypatch, "out/site")
    assert (root / "out" / "site" / ".nojekyll").is_file()


def test_s9_4_2_3_a_project_without_output_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _run(tmp_path, monkeypatch, compodoc='["core"]', storybook='["ui"]')
    site = root / "dist" / "site"
    assert (site / "api" / "core" / "index.html").read_text() == "a"
    assert (site / "storybook" / "ui" / "index.html").read_text() == "c"
    assert not (site / "api" / "ui").exists()


def test_s9_4_2_3_a_project_with_declared_target_but_no_output_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _workspace(tmp_path)
    (root / "dist" / "compodoc" / "ui" / "index.html").unlink()
    (root / "dist" / "compodoc" / "ui").rmdir()
    _stub_pnpm(
        tmp_path, monkeypatch, compodoc='["core","ui"]', **{"build-storybook": "[]"}
    )
    monkeypatch.chdir(root)
    assert cli.main(["site-assemble"]) == 1
    assert capsys.readouterr().err == (
        f"ui: expected compodoc output not found at {root}/dist/compodoc/ui\n"
    )
    assert not (root / "dist" / "site" / "index.html").exists()


def test_s9_4_2_4_index_html_is_the_javascripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "rn-forge/demo")
    root = _run(tmp_path, monkeypatch, compodoc='["core","ui"]', storybook='["ui"]')
    assert (root / "dist" / "site" / "index.html").read_text() == FIXTURE.read_text()
