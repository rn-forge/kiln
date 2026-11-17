"""The work-item model: epic, feature and release pages, and their metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rn_forge.commons.fs.blocks import HTML_COMMENT, ManagedBlock
from rn_forge.commons.text.markdown import MarkdownUtils

from rn_forge.kiln.modules.docs import parsed
from rn_forge.kiln.modules.docs.policy import POLICY

BOARD_BLOCK = ManagedBlock("derived board", comment=HTML_COMMENT)
"""The fenced board region of `docs/specs/index.md`."""

SCOPE_BLOCK = ManagedBlock("derived scope", comment=HTML_COMMENT)
"""The fenced Scope region of a release page."""

EPICS_BLOCK = ManagedBlock("derived epics", comment=HTML_COMMENT)
"""The fenced epic list region of `docs/specs/epics/index.md`."""

FEATURES_BLOCK = ManagedBlock("derived features", comment=HTML_COMMENT)
"""The fenced features region of an epic page."""

STORIES_BLOCK = ManagedBlock("derived stories", comment=HTML_COMMENT)
"""The fenced stories region of a feature page."""

FEATURE_FILE = re.compile(r"^F(\d+)\.(\d+)-.*\.md$")
"""A feature page's file name: `F<epic>.<n>-<name>.md`."""

STORY_HEADING_RE = re.compile(r"^## (S\d+\.\d+\.\d+) — (.+?)\s*$")

_BOLD_KEY_RE = re.compile(r"^\*\*(.+?)\*\*$")
_FEATURE_ID_RE = re.compile(r"F\d+\.\d+")
_RELEASE_RE = re.compile(r"release-(\d+)")
_NUMBER_RE = re.compile(r"\d+")


@dataclass(frozen=True)
class Page:
    path: Path
    title: str
    meta: tuple[tuple[str, str], ...]

    def get(self, key: str) -> str | None:
        """The value of the first *key* row, or `None`."""
        return next((value for k, value in self.meta if k == key), None)


@dataclass(frozen=True)
class FeatureRow:
    id: str
    file: str | None
    state: str
    tags: str


@dataclass(frozen=True)
class Epic:
    page: Page
    number: int
    dir: str
    rows: tuple[FeatureRow, ...]
    has_state_column: bool
    briefs: tuple[Path, ...] = ()


@dataclass(frozen=True)
class Story:
    id: str
    title: str
    state: str
    depends_on: str


@dataclass(frozen=True)
class Feature:
    page: Page
    id: str
    epic_number: int
    epic_dir: str
    stories: tuple[Story, ...] = ()

    @property
    def iteration(self) -> str | None:
        """The `release-<n>` name the `Iteration` value links to, or `None`."""
        match = _RELEASE_RE.search(self.page.get("Iteration") or "")
        return f"release-{match.group(1)}" if match else None


@dataclass(frozen=True)
class Release:
    page: Page
    number: int
    dir: str


@dataclass(frozen=True)
class Work:
    epics: tuple[Epic, ...]
    features: tuple[Feature, ...]
    releases: tuple[Release, ...]


def _metadata(lines: list[str]) -> tuple[list[tuple[str, str]], int] | None:
    """The metadata pairs and the index of the first line after the table."""
    text = "\n".join(lines)
    title = next((h for h in parsed.headings(text) if h.level == 1), None)
    if title is None:
        return None
    first = next(
        (n for n in range(title.line + 1, len(lines)) if lines[n].strip()), None
    )
    if first is None:
        return None
    table = next(
        (
            t
            for t in MarkdownUtils.tables(text)
            if t.start == first and t.header == ("", "")
        ),
        None,
    )
    if table is None:
        return None
    pairs: list[tuple[str, str]] = []
    for row in table.rows:
        key = _BOLD_KEY_RE.match(row[0])
        if key is None:
            break
        pairs.append((key.group(1).strip(), row[1]))
    return pairs, table.start + 2 + len(pairs)


def metadata_end(lines: list[str]) -> int | None:
    """The index of the first line after the metadata table, or `None`."""
    found = _metadata(lines)
    return None if found is None else found[1]


def _title(lines: list[str]) -> str:
    return parsed.title_markup("\n".join(lines)) or ""


def _page(path: Path) -> tuple[Page, list[str], int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    found = _metadata(lines)
    pairs, end = found if found else ([], 0)
    return Page(path, _title(lines), tuple(pairs)), lines, end


def _outside_fence(lines: list[str]) -> list[str]:
    begin = FEATURES_BLOCK.begin.strip()
    end = FEATURES_BLOCK.end.strip()
    kept: list[str] = []
    inside = False
    for line in lines:
        if line.strip() == begin:
            inside = True
        elif line.strip() == end:
            inside = False
        elif not inside:
            kept.append(line)
    return kept


def _feature_rows(lines: list[str]) -> tuple[tuple[FeatureRow, ...], bool]:
    """The first feature table's rows, and whether it has a `State` column.

    Lines inside a derived features fence are not hand-written rows.
    """
    for table in MarkdownUtils.tables("\n".join(_outside_fence(lines))):
        if not any(_FEATURE_ID_RE.search(row[0]) for row in table.rows):
            continue
        headers = table.header
        state = headers.index("State") if "State" in headers else None
        tags = headers.index("Tags") if "Tags" in headers else None
        rows: list[FeatureRow] = []
        for row in table.rows:
            found = _FEATURE_ID_RE.search(row[0])
            if found is None:
                continue
            targets = parsed.links(row[0])
            target = targets[0].partition("#")[0].rsplit("/", 1)[-1] if targets else ""
            rows.append(
                FeatureRow(
                    found.group(0),
                    target if FEATURE_FILE.match(target) else None,
                    row[state] if state is not None else "",
                    row[tags] if tags is not None else "",
                )
            )
        return tuple(rows), state is not None
    return (), True


_DEPENDS_RE = re.compile(r"\*\*Depends on:\*\*([^·]*)")


def read_stories(text: str) -> tuple[Story, ...]:
    """The stories of a feature page: each `## S<n>.<m>.<k> — <title>` heading.

    A heading inside fenced code is ignored. A story's state and dependencies
    come from the first `**State:**` paragraph before the next `## ` heading.
    """
    lines = MarkdownUtils.strip_fenced_code(text).splitlines()
    stories: list[Story] = []
    for i, line in enumerate(lines):
        heading = STORY_HEADING_RE.match(line)
        if heading is None:
            continue
        state = depends = ""
        for j, following in enumerate(lines[i + 1 :], i + 1):
            if following.startswith("## "):
                break
            if following.startswith("**State:**"):
                paragraph = [following]
                for rest in lines[j + 1 :]:
                    if not rest.strip() or rest.startswith("## "):
                        break
                    paragraph.append(rest)
                joined = " ".join(paragraph)
                state = joined.removeprefix("**State:**").split("·")[0].strip()
                found = _DEPENDS_RE.search(joined)
                depends = found.group(1).strip() if found else ""
                break
        stories.append(Story(heading.group(1), heading.group(2), state, depends))
    return tuple(stories)


def feature_sort_key(path: Path) -> tuple[int, int]:
    """The (epic, feature) numbers of a feature page's file name."""
    match = FEATURE_FILE.match(path.name)
    if match is None:
        raise ValueError(f"not a feature page name: {path.name}")
    return int(match.group(1)), int(match.group(2))


def page_number(name: str) -> int:
    match = _NUMBER_RE.search(name)
    return int(match.group(0)) if match else 0


def load_work(docs_root: Path) -> Work:
    """Load every epic, feature and release page under *docs_root*."""
    epics: list[Epic] = []
    features: list[Feature] = []
    for index in sorted(
        (docs_root / POLICY.nested[0].path).glob("*/index.md"),
        key=lambda p: page_number(p.parent.name),
    ):
        page, lines, end = _page(index)
        rows, has_state = _feature_rows(lines[end:])
        epics.append(
            Epic(
                page,
                page_number(index.parent.name),
                index.parent.name,
                rows,
                has_state,
                tuple(sorted((index.parent / "_briefs").glob("*.md"))),
            )
        )
        for path in sorted(
            index.parent.glob("F*.md"),
            key=lambda p: tuple(
                int(n) for n in re.findall(r"\d+", p.name.split("-")[0])
            ),
        ):
            features.append(
                Feature(
                    _page(path)[0],
                    path.name.split("-")[0],
                    page_number(index.parent.name),
                    index.parent.name,
                    read_stories(path.read_text(encoding="utf-8")),
                )
            )
    releases = [
        Release(_page(p)[0], page_number(p.parent.name), p.parent.name)
        for p in sorted(
            (docs_root / "releases").glob("release-*/index.md"),
            key=lambda p: page_number(p.parent.name),
        )
    ]
    return Work(tuple(epics), tuple(features), tuple(releases))


def tag_set(value: str | None) -> set[str]:
    """The lower-cased, comma-separated tags in *value*."""
    return {tag.strip().lower() for tag in (value or "").split(",") if tag.strip()}
