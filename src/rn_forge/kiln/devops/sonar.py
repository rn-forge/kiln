"""Run the workspace's coverage tests and scan the checked-out branch on SonarCloud."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys

TESTS = ["task", "test:coverage"]


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def resolve_branch(requested: str | None) -> str:
    """Return the branch to analyze.

    Raises:
        ValueError: On `main`, on a detached HEAD without `requested`, or when
            `requested` differs from the checked-out branch.
    """
    current = _git("branch", "--show-current")
    if not current and not requested:
        raise ValueError("detached HEAD: pass --branch with the branch name")
    if current and requested and requested != current:
        raise ValueError(f"--branch {requested!r} differs from checked-out {current!r}")
    branch = requested or current
    if branch == "main":
        raise ValueError("refusing to upload a local scan as main")
    return branch


def scanner_command(branch: str) -> list[str]:
    """Return the scanner command; sources, tests and report come from the properties file."""
    return [
        "sonar-scanner",
        f"-Dsonar.branch.name={branch}",
        "-Dsonar.qualitygate.wait=true",
    ]


def scanner_env() -> dict[str, str]:
    """Return the environment without CI metadata that triggers scanner autodetection."""
    return {
        key: value
        for key, value in os.environ.items()
        if key != "CI" and not key.startswith("GITHUB_")
    }


def run(requested: str | None, dry_run: bool) -> int:
    """Run the coverage tests and the scan, and return the first failing status.

    Args:
        requested: The `--branch` value, when given.
        dry_run: Print the target and the commands and run nothing.
    """
    try:
        branch = resolve_branch(requested)
    except ValueError as error:
        print(f"kiln-devops: {error}", file=sys.stderr)
        return 2
    scanner = scanner_command(branch)
    print(f"target: {branch}")
    if _git("status", "--porcelain"):
        print(
            "note: the working tree has uncommitted changes; this scan is not CI "
            "evidence for any commit"
        )
    if dry_run:
        print(shlex.join(TESTS))
        print(shlex.join(scanner))
        return 0
    if not os.environ.get("SONAR_TOKEN"):
        print("kiln-devops: SONAR_TOKEN is not set", file=sys.stderr)
        return 2
    if shutil.which("sonar-scanner") is None:
        print("kiln-devops: sonar-scanner is not installed", file=sys.stderr)
        return 2
    status = subprocess.run(TESTS, check=False).returncode
    if status:
        return status
    return subprocess.run(scanner, env=scanner_env(), check=False).returncode
