"""The docs conventions kiln holds a generated repo to.

The shape of a policy — numbered series, sequence areas, nested areas — and
kiln's own instance of it, `POLICY`: what an ADR is named, what an epic
directory looks like, which instruction files count.

The area *keys* are deliberately not here. `docs/_areas.yml` is seeded by kiln
and then owned by the repo, so a repo can declare an area kiln has never heard
of (D44) and the checks validate the tree against whatever it declares.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = [
    "KEBAB_NAME",
    "POLICY",
    "DocsPolicy",
    "NestedArea",
    "NumberedArea",
    "SequenceArea",
]

KEBAB_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")
"""Default :attr:`DocsPolicy.page_name` pattern."""

STATUS_LINE = re.compile(r"^\*\*Status:\*\*\s*(.+)$", re.MULTILINE)
"""Markdown status-line syntax."""


@dataclass(frozen=True, slots=True)
class NumberedArea:
    """A series of numbered documents, each carrying a status line.

    Args:
        path: The series' directory, relative to the docs root.
        filename: Page-name pattern with one capturing group: the number.
        statuses: Allowed statuses, matched against the lowercased value.
        label: What the series is called, in check messages.
        shape: The naming rule in human form, in check messages.
    """

    path: str
    filename: re.Pattern[str]
    statuses: re.Pattern[str]
    label: str
    shape: str


@dataclass(frozen=True, slots=True)
class SequenceArea:
    """Numbered sibling directories, each with its own ``index.md``.

    Args:
        path: The area's directory, relative to the docs root.
        dirname: Directory-name pattern.
        shape: The naming rule in human form, in check messages.
    """

    path: str
    dirname: re.Pattern[str]
    shape: str


@dataclass(frozen=True, slots=True)
class NestedArea:
    """Named container directories holding named pages.

    Args:
        path: The area's directory, relative to the docs root.
        dirname: Container-directory name pattern.
        dir_shape: The container naming rule in human form.
        page_glob: Which pages inside a container this rule applies to.
        page_name: Page-name pattern for those pages.
        page_shape: The page naming rule in human form.
    """

    path: str
    dirname: re.Pattern[str]
    dir_shape: str
    page_glob: str
    page_name: re.Pattern[str]
    page_shape: str


@dataclass(frozen=True, slots=True)
class DocsPolicy:
    """One repository's documentation conventions.

    Args:
        instruction_files: Root instruction files, in the order they are
            looked for. At least one must exist and lead to the docs rules.
        page_name: Naming rule for ordinary content pages.
        numbered: The numbered document series, when there is one.
        sequences: Sequence areas, if any.
        nested: Nested areas, if any.
    """

    instruction_files: tuple[str, ...]
    page_name: re.Pattern[str] = KEBAB_NAME
    numbered: NumberedArea | None = None
    sequences: tuple[SequenceArea, ...] = field(
        default_factory=tuple[SequenceArea, ...]
    )
    nested: tuple[NestedArea, ...] = field(default_factory=tuple[NestedArea, ...])

    def __post_init__(self) -> None:
        if not self.instruction_files:
            raise ValueError("A docs policy needs at least one instruction file")


POLICY = DocsPolicy(
    # One of these leads to the docs rules, never all of them: AGENTS.md is
    # typically a pointer at CLAUDE.md, not a second copy.
    instruction_files=("CLAUDE.md", "AGENTS.md"),
    page_name=KEBAB_NAME,
    numbered=NumberedArea(
        path="adr",
        filename=re.compile(r"^ADR-(\d{4})\.md$"),
        statuses=re.compile(r"^(proposed|accepted|deprecated)"),
        label="ADR",
        shape="ADR-<nnnn>.md",
    ),
    sequences=(
        SequenceArea(
            path="releases",
            dirname=re.compile(r"^release-(\d+)$"),
            shape="release-<n>/",
        ),
    ),
    nested=(
        NestedArea(
            path="specs/epics",
            dirname=re.compile(r"^E(\d+)-[a-z0-9-]+$"),
            dir_shape="E<n>-<kebab-name>/",
            page_glob="F*.md",
            page_name=re.compile(r"^F(\d+)\.(\d+)-[a-z0-9-]+\.md$"),
            page_shape="F<n>.<m>-<kebab-name>.md",
        ),
    ),
)
"""kiln's docs policy, the one every generated repo is checked against."""
