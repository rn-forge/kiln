"""The umbrella release: a GitHub release for the newest shipped release page."""

from __future__ import annotations

import re
import shlex
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from rn_forge.kiln.devops import github

# The planner may not import kiln's docs module (ADR-0017), so these two
# patterns repeat the ones in `rn_forge.kiln.modules.docs.work` (`_BOLD_KEY_RE`
# and the metadata table) at their minimum: a title line, then a `| **Key** |
# value |` table.
_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$")
_ROW_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*$")
_DIR_RE = re.compile(r"release-(\d+)")


@dataclass(frozen=True)
class Release:
    tag: str
    title: str
    notes: str


def _read(page: Path, tag: str) -> Release | None:
    """Return the release for a shipped `page`, or None for any other status."""
    lines = page.read_text(encoding="utf-8").splitlines()
    title = next((m.group(1) for m in map(_TITLE_RE.match, lines) if m), None)
    if title is None:
        return None
    status = None
    end = 0
    seen = False
    for n, line in enumerate(lines):
        row = _ROW_RE.match(line)
        if row:
            seen = True
            if row.group(1) == "Status":
                status = row.group(2)
        elif seen and not line.startswith("|"):
            end = n
            break
    else:
        end = len(lines)
    if status != "shipped":
        return None
    return Release(tag, title, "\n".join(lines[end:]).strip("\n") + "\n")


def shipped(releases: Path) -> list[Release]:
    """Return the release of each `release-<n>/index.md` marked `shipped`, by number."""
    found: list[tuple[int, Release]] = []
    for directory in releases.iterdir():
        match = _DIR_RE.fullmatch(directory.name)
        page = directory / "index.md"
        if match is None or not page.is_file():
            continue
        release = _read(page, directory.name)
        if release is not None:
            found.append((int(match.group(1)), release))
    return [release for _, release in sorted(found, key=lambda item: item[0])]


def create_command(release: Release, notes_file: str, sha: str) -> list[str]:
    """Return the `gh` command that creates `release` at `sha`."""
    return [
        "gh", "release", "create", release.tag,
        "--title", release.title,
        "--notes-file", notes_file,
        "--target", sha,
        "--latest",
    ]  # fmt: skip


def run(releases: Path, sha: str, dry_run: bool) -> int:
    """Create the newest shipped release if it has none; with `dry_run`, print the command.

    Lower shipped releases without a GitHub release are named on stderr and not created.

    Raises:
        FileNotFoundError: When `releases` is not a directory.
    """
    if not releases.is_dir():
        raise FileNotFoundError(f"no release pages at '{releases}'")
    found = shipped(releases)
    if not found:
        print("No shipped release is missing its GitHub release.", file=sys.stderr)
        return 0
    *lower, newest = found
    for release in lower:
        if dry_run or not github.release_exists(release.tag):
            print(
                f"kiln-devops: skipped {release.tag}: no GitHub release, and only the "
                "newest shipped release is created; create it by hand to backfill",
                file=sys.stderr,
            )
    if not dry_run and github.release_exists(newest.tag):
        print("No shipped release is missing its GitHub release.", file=sys.stderr)
        return 0
    notes = Path(tempfile.mkdtemp(prefix="kiln-umbrella-")) / f"{newest.tag}.md"
    notes.write_text(newest.notes, encoding="utf-8")
    command = create_command(newest, str(notes), sha)
    if dry_run:
        print(shlex.join(command))
    else:
        github.run(command)
    return 0
