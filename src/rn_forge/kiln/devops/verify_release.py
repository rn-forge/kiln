"""The `verify-release` check: install a published release from its registry and import it."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass

from rn_forge.kiln.devops.integration import Runner

PYPI_ATTEMPTS = 10
PYPI_INTERVAL = 30.0


@dataclass(frozen=True)
class Spec:
    """One release to verify.

    Attributes:
        name: The distribution name.
        module: The import name.
        version: The released version.
        tag: The release tag.
        source: `pypi` installs `name==version` from PyPI; `git` installs the tag.
        repository_url: The repository URL, for the `git` source.
        dir: The member's directory in the repository, for the `git` source.
    """

    name: str
    module: str
    version: str
    tag: str
    source: str
    repository_url: str = ""
    dir: str = "."


def requirement(spec: Spec) -> str:
    """Return the requirement `uv pip install` is given for `spec`."""
    if spec.source == "pypi":
        return f"{spec.name}=={spec.version}"
    subdirectory = "" if spec.dir in ("", ".") else f"#subdirectory={spec.dir}"
    return f"{spec.name} @ git+{spec.repository_url}@{spec.tag}{subdirectory}"


def run(
    spec: Spec,
    runner: Runner,
    sleep: Callable[[float], None] = time.sleep,
    attempts: int = PYPI_ATTEMPTS,
) -> int:
    """Install the release into a clean virtual environment and import its module.

    PyPI takes a while to serve a new release, so that install is retried.

    Args:
        spec: The release.
        runner: Runs every command.
        sleep: Waits between PyPI attempts.
        attempts: PyPI install attempts.

    Returns:
        0 when the module imports, else the status of the step that failed.
    """
    if spec.source == "git":
        fetched = runner(
            ["git", "fetch", "--no-tags", "origin", f"refs/tags/{spec.tag}"]
        )
        if fetched.returncode:
            return fetched.returncode
        attempts = 1
    venv = tempfile.mkdtemp(prefix="kiln-verify-")
    try:
        runner(["uv", "venv", "-q", venv])
        env = {"VIRTUAL_ENV": venv}
        install = [
            "uv",
            "pip",
            "install",
            "-q",
            "--no-cache",
            "--no-config",
            requirement(spec),
        ]
        status = 1
        for attempt in range(attempts):
            if attempt:
                sleep(PYPI_INTERVAL)
            status = runner(install, env=env).returncode
            if not status:
                break
        else:
            print(
                f"{requirement(spec)} is not installable after {attempts} attempt(s)",
                file=sys.stderr,
            )
        if status:
            return status
        return runner(
            [os.path.join(venv, "bin", "python"), "-c", f"import {spec.module}"]
        ).returncode
    finally:
        shutil.rmtree(venv, ignore_errors=True)
