"""Release notes: a section of a Keep a Changelog file."""

from __future__ import annotations

import re


def changelog_section(changelog: str, version: str) -> str:
    """Return the body under `## [<version>]` up to the next `## [` heading.

    The heading is `## [<version>]` followed by the end of the line or
    ` - <date>`; the version must match exactly.

    Args:
        changelog: The text of a Keep a Changelog file.
        version: The version whose section to return.

    Returns:
        The section body with surrounding whitespace removed.

    Raises:
        ValueError: The version has no heading, or its body is empty.
    """
    heading = re.compile(
        rf"^## \[{re.escape(version)}\](?: - .*)?[ \t]*$", re.MULTILINE
    )
    match = heading.search(changelog)
    if match is None:
        raise ValueError(f"no `## [{version}]` heading in the changelog")
    rest = changelog[match.end() :]
    following = re.search(r"^## \[", rest, re.MULTILINE)
    body = (rest[: following.start()] if following else rest).strip()
    if not body:
        raise ValueError(f"the `## [{version}]` section is empty")
    return body
