"""The GitHub Actions adapter: `$GITHUB_OUTPUT` lines and the event context."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence


def output_lines(outputs: Mapping[str, object]) -> list[str]:
    """Return `key=value` lines for `$GITHUB_OUTPUT`, with non-strings as JSON."""
    return [
        f"{key}={value if isinstance(value, str) else json.dumps(value)}"
        for key, value in outputs.items()
    ]


def sonar_branch(event: str, ref_type: str, ref_name: str) -> str:
    """Return the Sonar branch name to analyze, or "" to leave a pull request to the scanner.

    Raises:
        ValueError: For a tag ref, or any event other than push,
            workflow_dispatch and pull_request.
    """
    if event == "pull_request":
        return ""
    if event not in ("push", "workflow_dispatch"):
        raise ValueError(f"unsupported event for Sonar analysis: {event}")
    if ref_type != "branch":
        raise ValueError(
            f"unsupported ref for Sonar analysis: {ref_type} {ref_name}; run it on a branch"
        )
    return ref_name


def sonar_target() -> str:
    """Return the `branch-arg=` output line for the run in `EVENT_NAME`, `REF_TYPE` and `REF_NAME`.

    Raises:
        ValueError: As `sonar_branch`.
    """
    branch = sonar_branch(
        os.environ["EVENT_NAME"], os.environ["REF_TYPE"], os.environ["REF_NAME"]
    )
    return f"branch-arg=-Dsonar.branch.name={branch}" if branch else "branch-arg="


def _capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def run(command: list[str]) -> None:
    """Run `command` with its stdout sent to stderr.

    Raises:
        SystemExit: With the command's exit status when it fails.
    """
    result = subprocess.run(command, stdout=sys.stderr, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


def release_draft(tag: str) -> str | None:
    """Return `"true"` or `"false"` for the release `tag`'s draft flag, or None when there is no release.

    The release, not the tag, is the record of what shipped. Checking the tag
    instead would make a half-finished publish permanent: the tag would exist,
    the release would not, and every rerun would skip.
    """
    result = _capture(
        ["gh", "release", "view", tag, "--json", "isDraft", "--jq", ".isDraft"]
    )
    draft = result.stdout.strip() if result.returncode == 0 else ""
    return draft if draft in ("true", "false") else None


def remote_tag_exists(tag: str) -> bool:
    """Return whether `origin` has the tag `tag`.

    A tag without a published release is a release that failed after tagging;
    it must rebuild from the tag, because rebuilding from `HEAD` would ship a
    different commit under that version.

    Raises:
        SystemExit: With the exit status of a failing `git ls-remote`.
    """
    result = _capture(["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"])
    if result.returncode:
        raise SystemExit(result.returncode)
    return bool(result.stdout.strip())


def release_state(tag: str, draft: str | None, tagged: bool) -> dict[str, str]:
    """Return the `release-state` outputs: `tag`, `should-release`, `draft` and `tagged`.

    Args:
        tag: The release tag.
        draft: The result of `release_draft(tag)`.
        tagged: The result of `remote_tag_exists(tag)`.
    """
    return {
        "tag": tag,
        "should-release": _flag(draft != "false"),
        "draft": _flag(draft == "true"),
        "tagged": _flag(tagged),
    }


def publish_commands(
    tag: str,
    title: str,
    target: str,
    files: Sequence[str],
    draft: str | None,
    tagged: bool,
) -> list[list[str]]:
    """Return the `gh` commands that publish `tag`, or `[]` when it is already published.

    A leftover draft is deleted first. `gh release create` makes the tag itself
    at `target`, as part of publishing; tagging in a separate earlier step is
    what made a failed upload unrecoverable. On a resumed release the tag
    already exists and is reused as it is, with `--verify-tag`.

    Args:
        tag: The release tag.
        title: The release title.
        target: The commit a new tag is made at.
        files: The assets to upload, in order.
        draft: The result of `release_draft(tag)`.
        tagged: The result of `remote_tag_exists(tag)`.
    """
    if draft == "false":
        return []
    commands: list[list[str]] = []
    if draft == "true":
        commands.append(["gh", "release", "delete", tag, "--yes"])
    where = ["--verify-tag"] if tagged else ["--target", target]
    commands.append(
        ["gh", "release", "create", tag, *files, *where]
        + ["--title", title, "--generate-notes"]
    )
    return commands


def already_published(tag: str) -> None:
    """Write the message for a release that is already published to stderr."""
    print(f"Release {tag} already published; nothing to do.", file=sys.stderr)


def release_source(tag: str) -> str:
    """Check out `tag` when `origin` has it, and return the checked-out commit.

    Raises:
        SystemExit: With the exit status of a failing `git` command.
    """
    if remote_tag_exists(tag):
        run(["git", "fetch", "--no-tags", "origin", f"refs/tags/{tag}:refs/tags/{tag}"])
        run(["git", "checkout", "--detach", tag])
    result = _capture(["git", "rev-parse", "HEAD"])
    if result.returncode:
        raise SystemExit(result.returncode)
    return result.stdout.strip()


def _flag(value: bool) -> str:
    return "true" if value else "false"
