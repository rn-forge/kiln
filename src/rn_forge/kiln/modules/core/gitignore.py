"""Seeding `.gitignore` with upstream scaffolders' ignore bodies.

Each body is appended once, at scaffold time, before `apply` adds kiln's block.
Rules are never sorted or deduplicated: a negation means something only after
the rule it negates.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["GITIGNORE", "append", "normalize"]

GITIGNORE = ".gitignore"


def normalize(body: str) -> str:
    """*body* with LF endings, no leading or trailing blank lines and a final newline.

    Returns `""` for a blank body.
    """
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n" if lines else ""


def append(root: Path, body: str) -> None:
    """Append *body* to `root/.gitignore`, one blank line after what is there.

    Creates the file if absent; a blank *body* adds nothing.
    """
    target = root / GITIGNORE
    existing = normalize(target.read_text(encoding="utf-8")) if target.is_file() else ""
    sections = [section for section in (existing, normalize(body)) if section]
    if sections:
        target.write_text("\n".join(sections), encoding="utf-8")
