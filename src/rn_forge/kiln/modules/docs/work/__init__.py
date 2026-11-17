"""Read epic, feature and release pages, validate their metadata, render regions."""

from __future__ import annotations

from rn_forge.kiln.modules.docs.parsed import (
    EPIC_RANGE,
    epic_range,
    range_label,
    title_markup,
)
from rn_forge.kiln.modules.docs.work.model import (
    BOARD_BLOCK,
    EPICS_BLOCK,
    FEATURE_FILE,
    FEATURES_BLOCK,
    SCOPE_BLOCK,
    STORIES_BLOCK,
    STORY_HEADING_RE,
    Page,
    Story,
    Work,
    feature_sort_key,
    load_work,
    metadata_end,
    read_stories,
)
from rn_forge.kiln.modules.docs.work.render import (
    render_board,
    render_epics,
    render_features,
    render_scope,
    render_stories,
)
from rn_forge.kiln.modules.docs.work.validate import validate

__all__ = [
    "BOARD_BLOCK",
    "EPICS_BLOCK",
    "EPIC_RANGE",
    "FEATURES_BLOCK",
    "FEATURE_FILE",
    "SCOPE_BLOCK",
    "STORIES_BLOCK",
    "STORY_HEADING_RE",
    "Page",
    "Story",
    "Work",
    "epic_range",
    "feature_sort_key",
    "load_work",
    "metadata_end",
    "range_label",
    "read_stories",
    "render_board",
    "render_epics",
    "render_features",
    "render_scope",
    "render_stories",
    "title_markup",
    "validate",
]
