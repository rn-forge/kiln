"""Shape tests for `kiln-devops`: a pure core, one dispatch table, one page reader."""

from __future__ import annotations

import argparse
from pathlib import Path

from rn_forge.kiln.devops import cli, umbrella
from rn_forge.kiln.modules.docs import work

CI = Path(cli.__file__).with_name("ci.py")

ARGV = {
    "plan": [],
    "releasable": ["ok"],
    "released": [],
    "smoke": ["pkg"],
    "integration": ["pkg"],
    "verify-release": ["--source", "pypi"],
    "adapters": [],
    "sonar-target": [],
    "sonar-local": [],
    "release-state": ["v1"],
    "release-source": ["v1"],
    "release-publish": ["v1", "--title", "T", "--target", "abc1234", "a.whl"],
    "notes": ["CHANGELOG.md", "1.0.0"],
    "dist-resolve": ["dist"],
    "dist-verify": ["dist"],
    "site-assemble": [],
    "consumer": ["root"],
    "licenses": ["--format", "pnpm"],
    "requirements": [],
    "umbrella": ["--sha", "abc1234"],
    "evidence": ["collect", "--run", "1", "--sha", "abc1234", "--controls", "c.json"],
}


def test_ci_is_pure() -> None:
    text = CI.read_text(encoding="utf-8")
    assert "import subprocess" not in text
    assert "print(" not in text


def test_every_evidence_step_dispatches_by_func() -> None:
    parser = cli._parser()
    steps = {
        "collect": ["--run", "1", "--sha", "abc1234", "--controls", "c.json"],
        "render": ["--run", "1", "--release", "1"],
    }
    for step, argv in steps.items():
        assert callable(parser.parse_args(["evidence", step, *argv]).func), step


def test_every_subcommand_dispatches_by_func() -> None:
    parser = cli._parser()
    action = next(
        a
        for a in parser._actions
        if isinstance(a, argparse._SubParsersAction)  # pyright: ignore[reportPrivateUsage]
    )
    assert set(action.choices) == set(ARGV)
    for name, argv in ARGV.items():
        assert callable(parser.parse_args([name, *argv]).func), name


PAGES = {
    1: "# Release 1 — First\n\n|  |  |\n| -- | -- |\n| **Status** | shipped |\n"
    "| **Date** | 2026-01-01 |\n\nBody one.\n\n## Criteria\n\n- a\n",
    2: "# Release 2 — Second\n\n|  |  |\n| -- | -- |\n| **Status** | shipped |\n\nBody two.\n",
    3: "# Release 3 — Third\n\n|  |  |\n| -- | -- |\n| **Status** | draft |\n\nBody three.\n",
}


def test_umbrella_and_work_read_pages_alike(tmp_path: Path) -> None:
    for number, text in PAGES.items():
        page = tmp_path / "releases" / f"release-{number}" / "index.md"
        page.parent.mkdir(parents=True)
        page.write_text(text, encoding="utf-8")
    shipped = {r.tag: r for r in umbrella.shipped(tmp_path / "releases")}
    pages = {r.dir: r.page for r in work.load_work(tmp_path).releases}
    assert set(pages) == {"release-1", "release-2", "release-3"}
    assert {t for t, p in pages.items() if p.get("Status") == "shipped"} == set(shipped)
    for tag, release in shipped.items():
        page = pages[tag]
        lines = page.path.read_text(encoding="utf-8").splitlines()
        end = work.metadata_end(lines)
        assert end is not None
        assert release.title == page.title
        assert release.notes == "\n".join(lines[end:]).strip("\n") + "\n"
