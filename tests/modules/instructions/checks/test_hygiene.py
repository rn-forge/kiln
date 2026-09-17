"""S4.3.5 — `root-hygiene`: loose Markdown at the repo root."""

from __future__ import annotations

from pathlib import Path

from rn_forge.kiln import checks


def _findings(root: Path) -> list[tuple[str, str | None]]:
    return [(f.code, f.path) for f in checks.run(root, only="root-hygiene")]


def test_s4_3_5_the_allowed_root_files_pass(repo) -> None:
    root = repo(
        **{
            name: "# x\n"
            for name in (
                "README.md",
                "CLAUDE.md",
                "AGENTS.md",
                "CHANGELOG.md",
                "CONTRIBUTING.md",
            )
        }
    )
    assert _findings(root) == []


def test_s4_3_5_a_stray_root_markdown_file_warns(repo) -> None:
    root = repo(**{"NOTES.md": "# Notes\n", "docs__notes.md": "# Nested is fine\n"})
    findings = checks.run(root, only="root-hygiene")
    assert [(f.code, f.path, f.severity.name) for f in findings] == [
        ("hygiene.stray-root-file", "NOTES.md", "WARNING")
    ]
