"""Read epic, feature and release pages, and validate their metadata tables."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.blocks import HTML_COMMENT, ManagedBlock

__all__ = [
    "BOARD_BLOCK",
    "EPIC_KEYS",
    "FEATURE_KEYS",
    "RELEASE_KEYS",
    "RELEASE_STATUSES",
    "SCOPE_BLOCK",
    "STATES",
    "Epic",
    "Feature",
    "FeatureRow",
    "Page",
    "Release",
    "Work",
    "load_work",
    "read_metadata",
    "render_board",
    "render_scope",
    "validate",
]

EPIC_KEYS = ("State", "Tags", "Start Date", "Closed Date", "Entry criteria")
FEATURE_KEYS = (
    "State",
    "Parent",
    "Iteration",
    "Tags",
    "Start Date",
    "Closed Date",
    "Predecessors",
    "Source",
    "Entry criteria",
)
RELEASE_KEYS = ("Status", "Start Date", "Finish Date")
STATES = ("New", "Active", "Closed", "Removed")
RELEASE_STATUSES = ("planned", "in progress", "shipped")

BOARD_BLOCK = ManagedBlock("derived board", comment=HTML_COMMENT)
"""The fenced board region of `docs/specs/index.md`."""

SCOPE_BLOCK = ManagedBlock("derived scope", comment=HTML_COMMENT)
"""The fenced Scope region of a release page."""

_COUNT_ORDER = ("Active", "New", "Closed", "Removed")
_NO_FEATURES = "—"
_PER_FEATURE = "Per feature; see the epic."

_HEADER_RE = re.compile(r"^\|\s*\|\s*\|\s*$")
_DELIMITER_RE = re.compile(r"^\|\s*:?-+:?\s*\|\s*:?-+:?\s*\|\s*$")
_ROW_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|(.*)\|\s*$")
_FEATURE_ID_RE = re.compile(r"F\d+\.\d+")
_FEATURE_FILE_RE = re.compile(r"^F\d+\.\d+-.*\.md$")
_RELEASE_RE = re.compile(r"release-(\d+)")
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
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


@dataclass(frozen=True)
class Feature:
    page: Page
    id: str
    epic_number: int
    epic_dir: str

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


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _metadata(lines: list[str]) -> tuple[list[tuple[str, str]], int] | None:
    """The metadata pairs and the index of the first line after the table."""
    i = next((n for n, line in enumerate(lines) if line.startswith("# ")), None)
    if i is None:
        return None
    i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i + 1 >= len(lines):
        return None
    if not (_HEADER_RE.match(lines[i]) and _DELIMITER_RE.match(lines[i + 1])):
        return None
    i += 2
    pairs: list[tuple[str, str]] = []
    while i < len(lines) and (row := _ROW_RE.match(lines[i])):
        pairs.append((row.group(1).strip(), row.group(2).strip()))
        i += 1
    return pairs, i


def read_metadata(text: str) -> list[tuple[str, str]] | None:
    """The `(key, value)` rows of the metadata table after the title, or `None`."""
    found = _metadata(text.splitlines())
    return None if found is None else found[0]


def _title(lines: list[str]) -> str:
    return next(
        (line.removeprefix("# ").strip() for line in lines if line.startswith("# ")),
        "",
    )


def _page(path: Path) -> tuple[Page, list[str], int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    found = _metadata(lines)
    pairs, end = found if found else ([], 0)
    return Page(path, _title(lines), tuple(pairs)), lines, end


def _feature_rows(lines: list[str]) -> tuple[tuple[FeatureRow, ...], bool]:
    """The first feature table's rows, and whether it has a `State` column."""
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        start = i
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            i += 1
        block = lines[start:i]
        if len(block) < 3:
            continue
        headers = _cells(block[0])
        body = [_cells(line) for line in block[2:]]
        if not any(row and _FEATURE_ID_RE.search(row[0]) for row in body):
            continue
        state = headers.index("State") if "State" in headers else None
        tags = headers.index("Tags") if "Tags" in headers else None

        def cell(row: list[str], column: int | None) -> str:
            return row[column] if column is not None and column < len(row) else ""

        rows: list[FeatureRow] = []
        for row in body:
            found = _FEATURE_ID_RE.search(row[0]) if row else None
            if found is None:
                continue
            link = _LINK_RE.search(row[0])
            target = link.group(1).partition("#")[0].rsplit("/", 1)[-1] if link else ""
            rows.append(
                FeatureRow(
                    found.group(0),
                    target if _FEATURE_FILE_RE.match(target) else None,
                    cell(row, state),
                    cell(row, tags),
                )
            )
        return tuple(rows), state is not None
    return (), True


def _number(name: str) -> int:
    match = _NUMBER_RE.search(name)
    return int(match.group(0)) if match else 0


def load_work(docs_root: Path) -> Work:
    """Load every epic, feature and release page under *docs_root*."""
    epics: list[Epic] = []
    features: list[Feature] = []
    for index in sorted(
        (docs_root / "specs" / "epics").glob("*/index.md"),
        key=lambda p: _number(p.parent.name),
    ):
        page, lines, end = _page(index)
        rows, has_state = _feature_rows(lines[end:])
        epics.append(
            Epic(page, _number(index.parent.name), index.parent.name, rows, has_state)
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
                    _number(index.parent.name),
                    index.parent.name,
                )
            )
    releases = [
        Release(_page(p)[0], _number(p.parent.name), p.parent.name)
        for p in sorted(
            (docs_root / "releases").glob("release-*/index.md"),
            key=lambda p: _number(p.parent.name),
        )
    ]
    return Work(tuple(epics), tuple(features), tuple(releases))


def _tags(value: str | None) -> set[str]:
    return {tag.strip().lower() for tag in (value or "").split(",") if tag.strip()}


def _page_findings(
    page: Page,
    rel: str,
    keys: tuple[str, ...],
    state_key: str,
    vocabulary: tuple[str, ...],
) -> list[Finding]:
    """Findings common to every page type: shape, state and the date rules."""
    out: list[Finding] = []

    def err(code: str, message: str) -> None:
        out.append(Finding(f"docs.work-{code}", Severity.ERROR, message, path=rel))

    highest = -1
    seen: set[str] = set()
    for key, _ in page.meta:
        if key not in keys:
            err("unknown-key", f"has unknown key {key!r}")
        elif key in seen:
            err("repeated-key", f"repeats key {key!r}")
        else:
            seen.add(key)
            position = keys.index(key)
            if position < highest:
                err("key-order", f"has key {key!r} out of order")
            highest = max(highest, position)
    state = page.get(state_key)
    if state is None:
        err("missing-key", f"has no {state_key!r}")
    elif state not in vocabulary:
        err(
            "invalid-state",
            f"has {state_key!r} {state!r}, not one of {', '.join(vocabulary)}",
        )
    return out


def validate(work: Work, repo_root: Path) -> list[Finding]:
    """Apply the work-model rules to every page; report every broken one."""
    out: list[Finding] = []
    releases = {release.number for release in work.releases}

    def rel(page: Page) -> str:
        return page.path.relative_to(repo_root).as_posix()

    def err(page: Page, code: str, message: str) -> None:
        out.append(
            Finding(f"docs.work-{code}", Severity.ERROR, message, path=rel(page))
        )

    def closed_date(page: Page, state: str | None) -> None:
        closed = page.get("Closed Date")
        if closed is not None and state != "Closed":
            err(page, "dates", f"has Closed Date but its State is {state}")
        if state == "Closed" and closed is None:
            err(page, "dates", "is Closed but has no Closed Date")

    def entry_criteria(page: Page) -> None:
        has = page.get("Entry criteria") is not None
        deferred = "deferred" in _tags(page.get("Tags"))
        if has and not deferred:
            err(page, "entry-criteria", "has Entry criteria but no deferred tag")
        if deferred and not has:
            err(page, "entry-criteria", "is tagged deferred but has no Entry criteria")

    def base(
        page: Page, keys: tuple[str, ...], state_key: str, vocab: tuple[str, ...]
    ) -> str | None:
        """Shape findings; returns the state when it is valid, else `None`."""
        out.extend(_page_findings(page, rel(page), keys, state_key, vocab))
        state = page.get(state_key)
        return state if state in vocab else None

    for epic in work.epics:
        page = epic.page
        if not page.meta:
            err(page, "no-metadata", "has no metadata table after its title")
            continue
        state = base(page, EPIC_KEYS, "State", STATES)
        if state is not None:
            closed_date(page, state)
            start = page.get("Start Date")
            if state in ("Active", "Closed") and start is None:
                err(page, "dates", f"is {state} but has no Start Date")
            if state in ("New", "Removed") and start is not None:
                err(page, "dates", f"has Start Date but its State is {state}")
        entry_criteria(page)
        if not epic.has_state_column:
            err(page, "no-state-column", "has a feature table with no State column")

    for feature in work.features:
        page = feature.page
        if not page.meta:
            err(page, "no-metadata", "has no metadata table after its title")
            continue
        state = base(page, FEATURE_KEYS, "State", STATES)
        for key in ("Parent", "Predecessors"):
            if page.get(key) is None:
                err(page, "missing-key", f"has no {key!r}")
        if state is not None:
            closed_date(page, state)
        entry_criteria(page)
        value = page.get("Iteration")
        if value is None:
            if state == "Active":
                err(page, "iteration", "is Active but has no Iteration")
        elif feature.iteration is None:
            err(page, "iteration", f"has Iteration {value!r} that names no release-<n>")
        elif int(feature.iteration.removeprefix("release-")) not in releases:
            err(
                page,
                "iteration",
                f"has Iteration {value!r} but {feature.iteration} does not exist",
            )

    for release in work.releases:
        page = release.page
        if not page.meta:
            err(page, "no-metadata", "has no metadata table after its title")
            continue
        status = base(page, RELEASE_KEYS, "Status", RELEASE_STATUSES)
        if status is not None:
            finish = page.get("Finish Date")
            if finish is not None and status != "shipped":
                err(page, "dates", f"has Finish Date but its Status is {status}")
            if status == "shipped" and finish is None:
                err(page, "dates", "is shipped but has no Finish Date")

    _identities(work, rel, err)
    return out


def _identities(
    work: Work,
    rel: Callable[[Page], str],
    err: Callable[[Page, str, str], None],
) -> None:
    """Duplicate IDs, and table rows that disagree with their feature file."""
    row_ids = Counter(row.id for epic in work.epics for row in epic.rows)
    reported: set[str] = set()
    for epic in work.epics:
        for row in epic.rows:
            if row_ids[row.id] > 1 and row.id not in reported:
                reported.add(row.id)
                err(
                    epic.page,
                    "duplicate-id",
                    f"lists {row.id}, which is listed more than once",
                )
    file_ids: dict[str, Feature] = {}
    for feature in work.features:
        if feature.id in file_ids:
            err(
                feature.page,
                "duplicate-id",
                f"shares ID {feature.id} with {rel(file_ids[feature.id].page)}",
            )
        else:
            file_ids[feature.id] = feature
    by_file = {(f.epic_dir, f.page.path.name): f for f in work.features}
    for epic in work.epics:
        for row in epic.rows:
            feature = by_file.get((epic.dir, row.file or ""))
            actual = feature.page.get("State") if feature else None
            if (
                feature is not None
                and actual is not None
                and epic.has_state_column
                and row.state != actual
            ):
                err(
                    epic.page,
                    "state-mismatch",
                    f"lists {row.id} as {row.state!r} but {feature.page.path.name} has State {actual!r}",
                )


def _id_key(feature_id: str) -> tuple[int, ...]:
    return tuple(int(n) for n in _NUMBER_RE.findall(feature_id))


def _release_rows(work: Work) -> list[str]:
    rows: list[str] = []
    for release in sorted(work.releases, key=lambda r: -r.number):
        page = release.page
        status = page.get("Status") or ""
        if finish := page.get("Finish Date"):
            status += f" ({finish})"
        counts = Counter(
            f.page.get("State") for f in work.features if f.iteration == release.dir
        )
        features = (
            " · ".join(
                f"{counts[state]} {state}" for state in _COUNT_ORDER if counts[state]
            )
            or _NO_FEATURES
        )
        rows.append(
            f"| [{page.title}](../releases/{release.dir}/index.md) | {status} | {features} |"
        )
    return rows


def _backlog(work: Work) -> dict[str, dict[int, list[str]]]:
    """Backlog cells by section (`New`, `Deferred`), then by epic number."""
    epics = {epic.number: epic for epic in work.epics}
    by_id = {(f.epic_dir, f.id) for f in work.features}
    # (epic number, feature id, file, state, tags)
    items: list[tuple[int, str, str | None, str, set[str]]] = [
        (
            f.epic_number,
            f.id,
            f.page.path.name,
            f.page.get("State") or "",
            _tags(f.page.get("Tags")),
        )
        for f in work.features
        if f.iteration is None
    ]
    for epic in work.epics:
        epic_tags = _tags(epic.page.get("Tags"))
        for row in epic.rows:
            # A row whose ID has a file in this epic is that feature, however linked.
            if (epic.dir, row.id) not in by_id:
                items.append(
                    (epic.number, row.id, None, row.state, _tags(row.tags) or epic_tags)
                )

    def section(state: str, tags: set[str]) -> str | None:
        if "deferred" in tags:
            return "Deferred"
        return "New" if state == "New" else None

    grouped: dict[str, dict[int, list[tuple[tuple[int, ...], str]]]] = {}
    for number, feature_id, file, state, tags in items:
        name = section(state, tags) if state != "Removed" else None
        if name is None:
            continue
        text = (
            f"[{feature_id}](epics/{epics[number].dir}/{file})" if file else feature_id
        )
        grouped.setdefault(name, {}).setdefault(number, []).append(
            (_id_key(feature_id), text)
        )
    cells = {
        name: {
            number: [text for _, text in sorted(entries)]
            for number, entries in by_epic.items()
        }
        for name, by_epic in grouped.items()
    }
    for epic in work.epics:
        has_files = any(f.epic_number == epic.number for f in work.features)
        if epic.page.get("State") == "New" and not has_files and not epic.rows:
            name = section("New", _tags(epic.page.get("Tags"))) or "New"
            cells.setdefault(name, {})[epic.number] = [_NO_FEATURES]
    return cells


def render_board(work: Work) -> str:
    """The body of the board region: releases, then the unscheduled backlog."""
    epics = {epic.number: epic for epic in work.epics}
    lines = [
        "",
        "## Releases",
        "",
        "| Release | Status | Features |",
        "| -- | -- | -- |",
        *_release_rows(work),
        "",
        "## Backlog",
        "",
    ]
    backlog = _backlog(work)
    if not backlog:
        lines.append("Every feature is on a release or Removed.")
    else:
        lines.append("Features with no Iteration, by State and epic.")
    for name in ("New", "Deferred"):
        if name not in backlog:
            continue
        deferred = name == "Deferred"
        lines += [
            "",
            f"### {name}",
            "",
            "| Epic | Features | Entry criteria |"
            if deferred
            else "| Epic | Features |",
            "| -- | -- | -- |" if deferred else "| -- | -- |",
        ]
        for number in sorted(backlog[name]):
            epic = epics[number]
            row = f"| [{epic.page.title}](epics/{epic.dir}/index.md) | {', '.join(backlog[name][number])} |"
            if deferred:
                row += f" {epic.page.get('Entry criteria') or _PER_FEATURE} |"
            lines.append(row)
    lines.append("")
    return "\n".join(lines) + "\n"


def render_scope(work: Work, release: Release) -> str:
    """The body of *release*'s Scope region: the features whose `Iteration` names it."""
    features = sorted(
        (f for f in work.features if f.iteration == release.dir),
        key=lambda f: (f.epic_number, _id_key(f.id)),
    )
    lines = ["", "| Feature | Epic | State |", "| -- | -- | -- |"]
    lines += [
        f"| [{f.id}](../../specs/epics/{f.epic_dir}/{f.page.path.name}) "
        f"| E{f.epic_number} | {f.page.get('State') or ''} |"
        for f in features
    ]
    lines.append("")
    return "\n".join(lines) + "\n"
