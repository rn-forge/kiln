"""The umbrella release: a GitHub release for the newest shipped release page."""

from __future__ import annotations

import re
import shlex
import sys
import tempfile
from collections.abc import Sequence
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
_RUN_ROW_RE = re.compile(r"^\| \*\*Run\*\* \|.*actions/runs/(\d+)")
_RECORD = "security-evidence.json"


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


def create_command(
    release: Release, notes_file: str, sha: str, files: Sequence[str] = ()
) -> list[str]:
    """Return the `gh` command that creates `release` at `sha`, attaching `files`."""
    return [
        "gh", "release", "create", release.tag, *files,
        "--title", release.title,
        "--notes-file", notes_file,
        "--target", sha,
        "--latest",
    ]  # fmt: skip


def _page_run(page: Path) -> int | None:
    """Return the run ID named on the evidence `page`, or None."""
    for line in page.read_text(encoding="utf-8").splitlines():
        match = _RUN_ROW_RE.match(line)
        if match:
            return int(match.group(1))
    return None


def evidence_files(
    releases: Path, tag: str, dest: Path
) -> tuple[list[str], str | None]:
    """Return the evidence assets for release `tag`, downloaded into `dest`, or `[]` and why not."""
    page = releases / tag / "security.md"
    if not page.is_file():
        return [], "no security.md"
    run = _page_run(page)
    if run is None:
        return [], "security.md names no run"
    record = dest / _RECORD
    if (
        not github.download_artifact(run, "security-evidence", dest)
        or not record.is_file()
    ):
        return [], f"run {run} has no security-evidence artifact"
    return [str(record), str(page)], None


def run(releases: Path, sha: str, dry_run: bool, evidence: bool = False) -> int:
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
    directory = Path(tempfile.mkdtemp(prefix="kiln-umbrella-"))
    notes = directory / f"{newest.tag}.md"
    notes.write_text(newest.notes, encoding="utf-8")
    files: list[str] = []
    if evidence:
        if dry_run:
            page = releases / newest.tag / "security.md"
            named = page.is_file() and _page_run(page) is not None
            files = [_RECORD, str(page)] if named else []
            why = "no security.md" if not page.is_file() else "security.md names no run"
        else:
            files, why = evidence_files(releases, newest.tag, directory)
        if not files:
            print(
                f"kiln-devops: {newest.tag}: no security evidence attached ({why})",
                file=sys.stderr,
            )
    command = create_command(newest, str(notes), sha, files)
    if dry_run:
        print(shlex.join(command))
    else:
        github.run(command)
    return 0
