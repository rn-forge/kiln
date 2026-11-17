"""Render the derived regions of the work pages."""

from __future__ import annotations

import posixpath
import re
from collections import Counter
from collections.abc import Iterable

from rn_forge.commons.text.markdown import MarkdownUtils

from rn_forge.kiln.modules.docs.parsed import epic_range, range_label
from rn_forge.kiln.modules.docs.work.model import (
    Epic,
    Feature,
    Release,
    Work,
    page_number,
    tag_set,
)

_COUNT_ORDER = ("Active", "New", "Closed", "Removed")
_NO_FEATURES = "—"
_PER_FEATURE = "Per feature; see the epic."


def _counts(states: Iterable[str | None]) -> str:
    """*states* as `n State` terms in board order, or the empty marker."""
    counts = Counter(states)
    return (
        " \u00b7 ".join(
            f"{counts[name]} {name}" for name in _COUNT_ORDER if counts[name]
        )
        or _NO_FEATURES
    )


def _cell(text: str) -> str:
    """*text* with its pipes escaped for a table cell."""
    return text.replace("|", "\\|")


def _story_counts(feature: Feature) -> str:
    return _counts(story.state.split(" ")[0] for story in feature.stories)


def _body(lines: list[str]) -> str:
    """The region body for *lines*, ending in a blank line."""
    return "\n".join([*lines, ""]) + "\n"


def _id_key(feature_id: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", feature_id))


def _release_rows(work: Work) -> list[str]:
    rows: list[str] = []
    for release in sorted(work.releases, key=lambda r: -r.number):
        page = release.page
        status = page.get("Status") or ""
        if finish := page.get("Finish Date"):
            status += f" ({finish})"
        features = _counts(
            f.page.get("State") for f in work.features if f.iteration == release.dir
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
            tag_set(f.page.get("Tags")),
        )
        for f in work.features
        if f.iteration is None
    ]
    for epic in work.epics:
        epic_tags = tag_set(epic.page.get("Tags"))
        for row in epic.rows:
            # A row whose ID has a file in this epic is that feature, however linked.
            if (epic.dir, row.id) not in by_id:
                items.append(
                    (
                        epic.number,
                        row.id,
                        None,
                        row.state,
                        tag_set(row.tags) or epic_tags,
                    )
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
            name = section("New", tag_set(epic.page.get("Tags"))) or "New"
            cells.setdefault(name, {})[epic.number] = [_NO_FEATURES]
    return cells


_INLINE_LINK = re.compile(r"(\]\()([^)\s]*)(\))")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def _rebase_links(cell: str, epic_dir: str) -> str:
    """Rewrite inline link targets from the epic page's frame to the board's."""

    def rebase(match: re.Match[str]) -> str:
        target = match.group(2)
        if _SCHEME.match(target) or target.startswith("/"):
            return match.group(0)
        path, hash_, anchor = target.partition("#")
        base = f"epics/{epic_dir}/"
        path = posixpath.normpath(base + path) if path else base + "index.md"
        return f"{match.group(1)}{path}{hash_}{anchor}{match.group(3)}"

    return _INLINE_LINK.sub(rebase, cell)


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
                criteria = epic.page.get("Entry criteria")
                row += f" {_rebase_links(criteria, epic.dir) if criteria else _PER_FEATURE} |"
            lines.append(row)
    return _body(lines)


def render_scope(work: Work, release: Release) -> str:
    """The body of *release*'s Scope region: the features whose `Iteration` names it."""
    features = sorted(
        (f for f in work.features if f.iteration == release.dir),
        key=lambda f: (f.epic_number, _id_key(f.id)),
    )
    lines = ["", "| Feature | Epic | State |", "| -- | -- | -- |"]
    lines += [
        f"| [{_cell(f.page.title)}]"
        f"(../../specs/epics/{f.epic_dir}/{f.page.path.name}) "
        f"| E{f.epic_number} | {f.page.get('State') or ''} |"
        for f in features
    ]
    return _body(lines)


def _epic_row(work: Work, epic: Epic) -> str:
    state = epic.page.get("State") or ""
    if "deferred" in tag_set(epic.page.get("Tags")):
        state += " (deferred)"
    features = [f for f in work.features if f.epic_dir == epic.dir]
    counts = _counts(
        [f.page.get("State") for f in features]
        if features
        else [row.state for row in epic.rows]
    )
    releases = sorted({f.iteration for f in features if f.iteration}, key=page_number)
    return (
        f"| [{epic.page.title}]({epic.dir}/index.md) | {state} | {counts} "
        f"| {', '.join(releases) or _NO_FEATURES} |"
    )


def render_epics(work: Work) -> str:
    """The body of the epic list region: one table per range that holds an epic."""
    if not work.epics:
        return "\nNo epics yet.\n\n"
    ranges: dict[tuple[int, int], list[Epic]] = {}
    for epic in work.epics:
        ranges.setdefault(epic_range(epic.number), []).append(epic)
    labels = {span: range_label(*span) for span in ranges}
    jump = " \u00b7 ".join(
        f"[{labels[span]}](#{MarkdownUtils.slugify(labels[span])})"
        for span in sorted(ranges)
    )
    lines = ["", f"Jump to: {jump}"]
    for span in sorted(ranges):
        lines += [
            "",
            f"## {labels[span]}",
            "",
            "| Epic | State | Features | Iterations |",
            "| -- | -- | -- | -- |",
            *(_epic_row(work, epic) for epic in ranges[span]),
        ]
    return _body(lines)


def render_stories(feature: Feature) -> str:
    """The body of a feature page's stories region."""
    if not feature.stories:
        return "\nNo stories yet.\n\n"
    lines = [
        "",
        f"**Stories:** {_story_counts(feature)}",
        "",
        "| Story | State | Depends on |",
        "| -- | -- | -- |",
    ]
    for story in feature.stories:
        text = f"{story.id} \u2014 {story.title}"
        lines.append(
            f"| [{_cell(text)}](#{MarkdownUtils.slugify(text)}) "
            f"| {story.state or _NO_FEATURES} | {story.depends_on or _NO_FEATURES} |"
        )
    return _body(lines)


def render_features(work: Work, epic: Epic) -> str:
    """The body of *epic*'s features region: one row per feature file."""
    lines = [
        "",
        "| Feature | State | Iteration | Stories |",
        "| -- | -- | -- | -- |",
    ]
    for feature in work.features:
        if feature.epic_dir != epic.dir:
            continue
        deferred = "deferred" in tag_set(feature.page.get("Tags"))
        iteration = feature.iteration or ("deferred" if deferred else _NO_FEATURES)
        title = _cell(feature.page.title)
        lines.append(
            f"| [{title}]({feature.page.path.name}) | {feature.page.get('State') or ''} "
            f"| {iteration} | {_story_counts(feature)} |"
        )
    return _body(lines)
