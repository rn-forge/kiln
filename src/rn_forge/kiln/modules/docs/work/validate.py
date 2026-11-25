"""The work-model rules: every broken epic, feature and release page."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln.modules.docs.work.model import (
    Epic,
    Feature,
    Page,
    Release,
    Work,
    tag_set,
)

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
RELEASE_KEYS = ("Status", "Start Date", "Finish Date", "Security Evidence")
STATES = ("New", "Active", "Closed", "Removed")
RELEASE_STATUSES = ("planned", "in progress", "shipped")

_CONTRADICTS = {"New": ("Active", "Closed"), "Closed": ("New", "Active")}


@dataclass
class _Report:
    root: Path
    findings: list[Finding]

    def rel(self, page: Page) -> str:
        """*page*'s path relative to the repository root."""
        return page.path.relative_to(self.root).as_posix()

    def err(self, page: Page, code: str, message: str) -> None:
        """Record an error finding `docs.work-<code>` on *page*."""
        self.findings.append(
            Finding(f"docs.work-{code}", Severity.ERROR, message, path=self.rel(page))
        )


def _page_findings(
    report: _Report,
    page: Page,
    keys: tuple[str, ...],
    state_key: str,
    vocabulary: tuple[str, ...],
) -> None:
    """Findings common to every page type: shape, state and the date rules."""
    highest = -1
    seen: set[str] = set()
    for key, _ in page.meta:
        if key not in keys:
            report.err(page, "unknown-key", f"has unknown key {key!r}")
        elif key in seen:
            report.err(page, "repeated-key", f"repeats key {key!r}")
        else:
            seen.add(key)
            position = keys.index(key)
            if position < highest:
                report.err(page, "key-order", f"has key {key!r} out of order")
            highest = max(highest, position)
    state = page.get(state_key)
    if state is None:
        report.err(page, "missing-key", f"has no {state_key!r}")
    elif state not in vocabulary:
        report.err(
            page,
            "invalid-state",
            f"has {state_key!r} {state!r}, not one of {', '.join(vocabulary)}",
        )


def _base(
    report: _Report,
    page: Page,
    keys: tuple[str, ...],
    state_key: str,
    vocabulary: tuple[str, ...],
) -> str | None:
    """Shape findings; returns the state when it is valid, else `None`."""
    _page_findings(report, page, keys, state_key, vocabulary)
    state = page.get(state_key)
    return state if state in vocabulary else None


def _closed_date(report: _Report, page: Page, state: str | None) -> None:
    closed = page.get("Closed Date")
    if closed is not None and state != "Closed":
        report.err(page, "dates", f"has Closed Date but its State is {state}")
    if state == "Closed" and closed is None:
        report.err(page, "dates", "is Closed but has no Closed Date")


def _entry_criteria(report: _Report, page: Page) -> None:
    has = page.get("Entry criteria") is not None
    deferred = "deferred" in tag_set(page.get("Tags"))
    if has and not deferred:
        report.err(page, "entry-criteria", "has Entry criteria but no deferred tag")
    if deferred and not has:
        report.err(
            page, "entry-criteria", "is tagged deferred but has no Entry criteria"
        )


def _validate_epic(report: _Report, work: Work, epic: Epic) -> None:
    page = epic.page
    if not page.meta:
        report.err(page, "no-metadata", "has no metadata table after its title")
        return
    state = _base(report, page, EPIC_KEYS, "State", STATES)
    if state is not None:
        _closed_date(report, page, state)
        start = page.get("Start Date")
        if state in ("Active", "Closed") and start is None:
            report.err(page, "dates", f"is {state} but has no Start Date")
        if state in ("New", "Removed") and start is not None:
            report.err(page, "dates", f"has Start Date but its State is {state}")
    _entry_criteria(report, page)
    has_files = any(f.epic_dir == epic.dir for f in work.features)
    if not has_files and not epic.has_state_column:
        report.err(page, "no-state-column", "has a feature table with no State column")


def _validate_feature(report: _Report, feature: Feature, releases: set[int]) -> None:
    page = feature.page
    if not page.meta:
        report.err(page, "no-metadata", "has no metadata table after its title")
        return
    state = _base(report, page, FEATURE_KEYS, "State", STATES)
    for key in ("Parent", "Predecessors"):
        if page.get(key) is None:
            report.err(page, "missing-key", f"has no {key!r}")
    if state is not None:
        _closed_date(report, page, state)
    _entry_criteria(report, page)
    value = page.get("Iteration")
    if value is None:
        if state == "Active":
            report.err(page, "iteration", "is Active but has no Iteration")
    elif feature.iteration is None:
        report.err(
            page, "iteration", f"has Iteration {value!r} that names no release-<n>"
        )
    elif int(feature.iteration.removeprefix("release-")) not in releases:
        report.err(
            page,
            "iteration",
            f"has Iteration {value!r} but {feature.iteration} does not exist",
        )


def _validate_release(report: _Report, release: Release) -> None:
    page = release.page
    if not page.meta:
        report.err(page, "no-metadata", "has no metadata table after its title")
        return
    status = _base(report, page, RELEASE_KEYS, "Status", RELEASE_STATUSES)
    if status is not None:
        finish = page.get("Finish Date")
        if finish is not None and status != "shipped":
            report.err(page, "dates", f"has Finish Date but its Status is {status}")
        if status == "shipped" and finish is None:
            report.err(page, "dates", "is shipped but has no Finish Date")


def validate(work: Work, repo_root: Path) -> list[Finding]:
    """Apply the work-model rules to every page; report every broken one."""
    report = _Report(repo_root, [])
    releases = {release.number for release in work.releases}
    for epic in work.epics:
        _validate_epic(report, work, epic)
    for feature in work.features:
        _validate_feature(report, feature, releases)
    for release in work.releases:
        _validate_release(report, release)
    _identities(report, work)
    _contradictions(report, work)
    report.findings.extend(_briefs(work, repo_root))
    return report.findings


def _briefs(work: Work, repo_root: Path) -> list[Finding]:
    """A brief left behind for a closed or removed story, or for no story."""
    out: list[Finding] = []
    for epic in work.epics:
        stories = {
            story.id: story
            for feature in work.features
            if feature.epic_dir == epic.dir
            for story in feature.stories
        }
        for brief in epic.briefs:
            path = brief.relative_to(repo_root).as_posix()
            story = stories.get(brief.stem)
            state = story.state.split(" ")[0] if story else ""
            if story is None:
                message = (
                    f"is a brief for {brief.stem}, which is not a story in {epic.dir}"
                )
                code = "docs.work-brief-unknown"
            elif state in ("Closed", "Removed"):
                message = f"is a brief for {story.id}, which is {state}; delete it"
                code = "docs.work-brief-closed"
            else:
                continue
            out.append(Finding(code, Severity.ERROR, message, path=path))
    return out


def _contradictions(report: _Report, work: Work) -> None:
    """An epic or feature whose state its features or stories contradict."""

    def check(page: Page, children: list[tuple[str, str]]) -> None:
        state = page.get("State") or ""
        bad = [(i, s) for i, s in children if s in _CONTRADICTS.get(state, ())]
        if bad:
            report.findings.append(
                Finding(
                    "docs.state-contradicts-work",
                    Severity.ERROR,
                    f"is {state} but " + ", ".join(f"{i} is {s}" for i, s in bad),
                    path=report.rel(page),
                )
            )

    for epic in work.epics:
        features = [f for f in work.features if f.epic_dir == epic.dir]
        ids = {f.id for f in features}
        check(
            epic.page,
            [(f.id, f.page.get("State") or "") for f in features]
            + [(row.id, row.state) for row in epic.rows if row.id not in ids],
        )
    for feature in work.features:
        check(
            feature.page,
            [(story.id, story.state.split(" ")[0]) for story in feature.stories],
        )


def _identities(report: _Report, work: Work) -> None:
    """Duplicate IDs, and table rows that disagree with their feature file."""
    row_ids = Counter(row.id for epic in work.epics for row in epic.rows)
    reported: set[str] = set()
    for epic in work.epics:
        for row in epic.rows:
            if row_ids[row.id] > 1 and row.id not in reported:
                reported.add(row.id)
                report.err(
                    epic.page,
                    "duplicate-id",
                    f"lists {row.id}, which is listed more than once",
                )
    file_ids: dict[str, Feature] = {}
    for feature in work.features:
        if feature.id in file_ids:
            report.err(
                feature.page,
                "duplicate-id",
                f"shares ID {feature.id} with {report.rel(file_ids[feature.id].page)}",
            )
        else:
            file_ids[feature.id] = feature
    by_file = {(f.epic_dir, f.page.path.name): f for f in work.features}
    for epic in work.epics:
        epic_file_ids = {f.id for f in work.features if f.epic_dir == epic.dir}
        for row in epic.rows:
            if row.id in epic_file_ids:
                report.err(
                    epic.page,
                    "feature-table",
                    f"lists {row.id} by hand; its derived features table shows it",
                )
                continue
            feature = by_file.get((epic.dir, row.file or ""))
            actual = feature.page.get("State") if feature else None
            if (
                feature is not None
                and actual is not None
                and epic.has_state_column
                and row.state != actual
            ):
                report.err(
                    epic.page,
                    "state-mismatch",
                    f"lists {row.id} as {row.state!r} but {feature.page.path.name} has State {actual!r}",
                )
