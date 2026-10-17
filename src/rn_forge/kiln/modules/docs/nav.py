"""Generate `mkdocs.yml` navigation from `docs/_areas.yml` and the docs tree.

Pages are ordered with `index.md` first and untitled, so that
`navigation.indexes` makes it the section's page, followed by its linked pages
in link order, then all remaining pages alphabetically.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.fs.documents import YamlUtils

from rn_forge.kiln.modules.docs.areas import Area, load_areas
from rn_forge.kiln.modules.docs.markdown import is_external, links
from rn_forge.kiln.modules.docs.work import epic_range, range_label

__all__ = [
    "ACRONYMS",
    "NAV_BLOCK",
    "NavEntry",
    "build_nav",
    "mark_nav",
    "page_title",
    "title_from_filename",
    "update_nav",
]

NAV_BLOCK = ManagedBlock("derived nav", indent="  ")
"""The fenced block inside `mkdocs.yml`'s ``nav:`` that this module owns."""

ACRONYMS = {"adr": "ADR", "api": "API", "cli": "CLI", "ci": "CI", "id": "ID"}
"""Filename words that are capitalised rather than title-cased."""


def title_from_filename(name: str) -> str:
    """Turn ``task-cli-api.md`` into ``Task CLI API``."""
    stem = name.removesuffix(".md")
    return " ".join(
        ACRONYMS.get(word.lower(), word.capitalize()) for word in stem.split("-")
    )


def page_title(path: Path) -> str:
    """The text of *path*'s first `# ` heading, else its filename's title."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return title_from_filename(path.name)


def _linked_order(index_path: Path) -> list[str]:
    if not index_path.exists():
        return []
    return [
        link.partition("#")[0]
        for link in links(index_path.read_text(encoding="utf-8"))
        if not is_external(link) and link.partition("#")[0].endswith(".md")
    ]


def _children_entries(docs_root: Path, area_key: str) -> list[tuple[str | None, str]]:
    area_dir = docs_root / area_key
    index_path = area_dir / "index.md"

    ordered: list[str] = []
    if index_path.exists():
        ordered.append(f"{area_key}/index.md")
    for link in _linked_order(index_path):
        rel = link if link.startswith(f"{area_key}/") else f"{area_key}/{link}"
        if (docs_root / rel).exists() and rel not in ordered:
            ordered.append(rel)
    for page in sorted(area_dir.glob("*.md")):
        rel = f"{area_key}/{page.name}"
        if page.name == "index.md" or page.name.startswith("_") or rel in ordered:
            continue
        ordered.append(rel)

    return [
        (None if rel == f"{area_key}/index.md" else page_title(docs_root / rel), rel)
        for rel in ordered
    ]


NavEntry = dict[str, "str | list[str | NavEntry]"]
"""One mkdocs nav entry: a title mapped to a page path or to nested entries."""

BLOCK_INDENT = "  "
"""What every serialized nav line is indented by, to sit under ``nav:``."""


_EPIC_DIR_RE = re.compile(r"^E(\d+)-")
_FEATURE_FILE_RE = re.compile(r"^F(\d+)\.(\d+)-.*\.md$")


def _is_page(page: Path) -> bool:
    return page.name != "index.md" and not page.name.startswith("_")


def _epic_entry(docs_root: Path, epic_dir: Path) -> NavEntry:
    def rel(page: Path) -> str:
        return page.relative_to(docs_root).as_posix()

    index = epic_dir / "index.md"
    title = page_title(index)
    others = [p for p in epic_dir.glob("*.md") if _is_page(p)]
    features = sorted(
        (p for p in others if _FEATURE_FILE_RE.match(p.name)),
        key=lambda p: tuple(int(n) for n in re.findall(r"\d+", p.name.split("-")[0])),
    )
    rest = sorted((p for p in others if p not in features), key=lambda p: p.name)
    children: list[str | NavEntry] = [rel(index)]
    children.extend({page_title(p): rel(p)} for p in [*features, *rest])
    return {title: children}


def _work_entry(docs_root: Path, area: Area) -> NavEntry:
    area_dir = docs_root / area.key
    items: list[str | NavEntry] = []
    if (area_dir / "index.md").exists():
        items.append(f"{area.key}/index.md")
    epic_list = area_dir / "epics" / "index.md"
    if epic_list.exists():
        items.append({page_title(epic_list): f"{area.key}/epics/index.md"})
    epic_dirs = sorted(
        (
            (int(match.group(1)), path)
            for path in (area_dir / "epics").glob("E*-*")
            if path.is_dir()
            and (path / "index.md").exists()
            and (match := _EPIC_DIR_RE.match(path.name))
        ),
        key=lambda pair: pair[0],
    )
    ranges: dict[tuple[int, int], list[str | NavEntry]] = {}
    for number, path in epic_dirs:
        ranges.setdefault(epic_range(number), []).append(_epic_entry(docs_root, path))
    items.extend({range_label(*span): ranges[span]} for span in sorted(ranges))
    items.extend(
        {page_title(p): f"{area.key}/{p.name}"}
        for p in sorted(area_dir.glob("*.md"), key=lambda p: p.name)
        if _is_page(p)
    )
    return {area.title: items}


def _area_entry(
    docs_root: Path, area: Area, packages: Sequence[str] = ()
) -> NavEntry | None:
    """The nav entry for *area*, or ``None`` when it contributes nothing."""
    if area.nav == "include":
        if not packages:
            return None
        return {
            area.title: [{Path(p).name: f"!include {p}/mkdocs.yml"} for p in packages]
        }
    area_dir = docs_root / area.key
    if (area.optional or area.generated) and not area_dir.is_dir():
        return None
    if area.nav == "work":
        return _work_entry(docs_root, area)
    if area.nav == "index-only":
        return {area.title: f"{area.key}/index.md"}
    entries = _children_entries(docs_root, area.key)
    if not entries:
        return None
    return {
        area.title: [rel if title is None else {title: rel} for title, rel in entries]
    }


def build_nav(docs_root: str | Path, packages: Sequence[str] = ()) -> str:
    """Render the derived nav's body for the docs tree at *docs_root*."""
    docs_root = Path(docs_root)
    nav: list[NavEntry] = [{"Home": "index.md"}]
    nav.extend(
        entry
        for area in load_areas(docs_root)
        if (entry := _area_entry(docs_root, area, packages)) is not None
    )
    serialized = YamlUtils.serialize(nav, width=sys.maxsize)
    return "".join(
        f"{BLOCK_INDENT}{line}\n" if line else "\n" for line in serialized.splitlines()
    )


def update_nav(
    mkdocs_path: str | Path, docs_root: str | Path, packages: Sequence[str] = ()
) -> tuple[str, bool]:
    """Return `mkdocs.yml`'s new text and whether it differs from what is on disk.

    Writes nothing — the caller decides whether this is a check or a rewrite.

    Raises:
        AppException: The nav's markers are missing or malformed.
    """
    mkdocs_path = Path(mkdocs_path)
    current = mkdocs_path.read_text(encoding="utf-8")
    if NAV_BLOCK.extract(current) is None:
        raise AppException(
            "{} has no {!r} / {!r} markers",
            mkdocs_path,
            NAV_BLOCK.begin.strip(),
            NAV_BLOCK.end.strip(),
        )
    updated = NAV_BLOCK.render(current, build_nav(docs_root, packages))
    return updated, updated != current


def mark_nav(text: str) -> str:
    """Return *text* with `NAV_BLOCK`'s markers placed around ``nav:``'s entries.

    Text that already carries the markers is returned as it is. The entries are
    the lines after the ``nav:`` line (at column 0) up to the first non-blank
    line that does not start with a space; trailing blank lines stay outside.
    With no ``nav:`` line, an empty marked nav is appended.
    """
    if NAV_BLOCK.extract(text) is not None:
        return text
    lines = text.splitlines(keepends=True)
    start = next(
        (i for i, line in enumerate(lines) if line.rstrip("\r\n") == "nav:"), None
    )
    if start is None:
        head = text if text.endswith("\n") or not text else text + "\n"
        return f"{head}\nnav:\n{NAV_BLOCK.begin}\n{NAV_BLOCK.end}\n"
    first = start + 1
    stop = first
    last = first
    while stop < len(lines) and (not lines[stop].strip() or lines[stop][0] == " "):
        stop += 1
        if lines[stop - 1].strip():
            last = stop
    before, entries, after = lines[:first], lines[first:last], lines[last:]
    if before[-1][-1:] != "\n":
        before[-1] += "\n"
    if entries and entries[-1][-1:] != "\n":
        entries[-1] += "\n"
    return "".join(
        [*before, NAV_BLOCK.begin, "\n", *entries, NAV_BLOCK.end, "\n", *after]
    )
