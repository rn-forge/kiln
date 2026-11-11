"""Assemble the docs site from each project's `compodoc` and `build-storybook` output."""

from __future__ import annotations

import html
import json
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.parse import quote

# (title, target, source directory under `dist/`, directory under the site)
_SECTIONS = (
    ("API reference", "compodoc", "compodoc", "api"),
    ("Storybook", "build-storybook", "storybook", "storybook"),
)

# JavaScript's `encodeURIComponent` leaves these unescaped.
_URI_SAFE = "!~*'()"

_PAGE_HEAD = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>@NAME@ docs</title>
    <style>
      :root {
        color-scheme: light dark;
        --fg: #1a1a1a;
        --bg: #ffffff;
        --muted: #666666;
        --border: #e0e0e0;
        --accent: #6236ff;
      }
      @media (prefers-color-scheme: dark) {
        :root {
          --fg: #f0f0f0;
          --bg: #121212;
          --muted: #a0a0a0;
          --border: #333333;
          --accent: #a78bfa;
        }
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        font-family:
          -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: var(--fg);
        background: var(--bg);
        display: flex;
        justify-content: center;
        padding: 4rem 1.5rem;
      }
      main {
        max-width: 720px;
        width: 100%;
      }
      h1 {
        font-size: 1.75rem;
        margin-bottom: 0.25rem;
      }
      h2 {
        font-size: 1.25rem;
        margin: 2rem 0 0;
      }
      .cards {
        display: grid;
        gap: 1rem;
        margin-top: 1rem;
      }
      a.card {
        display: block;
        padding: 1.25rem 1.5rem;
        border: 1px solid var(--border);
        border-radius: 10px;
        text-decoration: none;
        color: inherit;
      }
      a.card:hover {
        border-color: var(--accent);
      }
      a.card h3 {
        margin: 0 0 0.25rem;
        font-size: 1.1rem;
        color: var(--accent);
      }
      a.card p {
        margin: 0;
        color: var(--muted);
        font-size: 0.95rem;
      }
    </style>
  </head>
  <body>
"""

_PAGE_TAIL = """    </main>
  </body>
</html>
"""


def _escape(text: str) -> str:
    return html.escape(text, quote=False).replace('"', "&quot;")


def _description(root: Path, project_root: str) -> str:
    try:
        package = json.loads(
            (root / project_root / "package.json").read_text(encoding="utf-8")
        )
        return str(package.get("description") or "")
    except OSError, ValueError, AttributeError:
        return ""


def assemble(
    root: Path,
    site: Path,
    projects: Mapping[str, Sequence[tuple[str, str]]],
    name: str | None = None,
) -> None:
    """Copy each project's output under `site` and write `index.html` and `.nojekyll`.

    Existing content of `site` is kept, and so is an existing `index.html`.

    Args:
        root: The workspace root.
        site: The site directory.
        projects: Each target (`compodoc`, `build-storybook`) mapped to its
            `(project, project_root)` pairs.
        name: The title of a generated `index.html`; the root's name when omitted.

    Raises:
        FileNotFoundError: With one line per project whose output is missing; the
            others are still copied, but no `index.html` is written.
    """
    site.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    body = ""
    for title, target, source, directory in _SECTIONS:
        found = projects.get(target, ())
        if not found:
            continue
        cards = ""
        for project, project_root in found:
            origin = root / "dist" / source / project
            if not origin.exists():
                missing.append(
                    f"{project}: expected {target} output not found at {origin}"
                )
                continue
            shutil.copytree(origin, site / directory / project, dirs_exist_ok=True)
            description = _description(root, project_root)
            href = f"./{directory}/{quote(project, safe=_URI_SAFE)}/"
            cards += (
                f'\n        <a class="card" href="{href}">'
                f"\n          <h3>{_escape(project)}</h3>"
            )
            if description:
                cards += f"\n          <p>{_escape(description)}</p>"
            cards += "\n        </a>"
        body += (
            f"\n      <h2>{_escape(title)}</h2>"
            f'\n      <div class="cards">{cards}\n      </div>'
        )
    if missing:
        raise FileNotFoundError("\n".join(missing))
    index = site / "index.html"
    if not index.exists():
        title = _escape(name or root.name)
        head = _PAGE_HEAD.replace("@NAME@", title)
        index.write_text(
            f"{head}    <main>\n      <h1>{title}</h1>{body}\n{_PAGE_TAIL}",
            encoding="utf-8",
        )
    (site / ".nojekyll").write_text("", encoding="utf-8")
