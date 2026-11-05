"""The `integration` check: a package's tests against its declared service containers."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Protocol

from rn_forge.kiln.devops.ci import Package, Service

ATTEMPTS = 60
INTERVAL = 2.0


class Runner(Protocol):
    """Runs a command and returns its result.

    `env` is added to the process environment; `capture` returns stdout as text.
    """

    def __call__(
        self,
        command: list[str],
        env: dict[str, str] | None = None,
        capture: bool = False,
    ) -> subprocess.CompletedProcess[str]: ...


def subprocess_runner(
    command: list[str], env: dict[str, str] | None = None, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run `command` with `subprocess`; the default `Runner`."""
    return subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=capture,
        env={**os.environ, **env} if env else None,
    )


def container(package: Package, service: Service) -> str:
    """Return the name of the container that runs `service` for `package`."""
    return f"kiln-ci-{package.name}-{service.name}"


def start_command(package: Package, service: Service) -> list[str]:
    """Return the `docker run` command for `service`."""
    command = ["docker", "run", "-d", "--name", container(package, service)]
    for key, value in service.env.items():
        command += ["-e", f"{key}={value}"]
    for port in service.ports:
        command += ["-p", port]
    if service.health_cmd:
        command += [
            "--health-cmd", service.health_cmd,
            "--health-interval", "2s",
            "--health-timeout", "5s",
            "--health-retries", "30",
        ]  # fmt: skip
    return [*command, service.image]


def _ready(
    package: Package,
    service: Service,
    runner: Runner,
    sleep: Callable[[float], None],
    attempts: int,
) -> bool:
    field, want = (
        ("{{.State.Health.Status}}", "healthy")
        if service.health_cmd
        else ("{{.State.Status}}", "running")
    )
    for attempt in range(attempts):
        if attempt:
            sleep(INTERVAL)
        result = runner(
            ["docker", "inspect", "-f", field, container(package, service)],
            capture=True,
        )
        if result.stdout.strip() == want:
            return True
    return False


def run(
    package: Package,
    runner: Runner,
    pytest_args: list[str],
    sleep: Callable[[float], None] = time.sleep,
    attempts: int = ATTEMPTS,
) -> int:
    """Start `package`'s services, run its tests against them and remove them.

    The containers are removed also when the tests fail or a service never gets
    ready.

    Args:
        package: The member, with its services.
        runner: Runs every command.
        pytest_args: Arguments added to the pytest run.
        sleep: Waits between health checks.
        attempts: Health checks per service before giving up.

    Returns:
        The exit status of pytest, or the status of a failed `docker run`, or 1 when a service does not become
        ready.
    """
    expose = {k: v for s in package.services for k, v in s.expose.items()}
    try:
        for service in package.services:
            started = runner(start_command(package, service))
            if started.returncode:
                return started.returncode
        for service in package.services:
            if not _ready(package, service, runner, sleep, attempts):
                print(f"{service.name} did not become ready", file=sys.stderr)
                return 1
        return runner(
            [
                "uv", "run", "--directory", package.dir, "--package", package.name,
                "pytest", "-q", *pytest_args,
            ],
            env=expose,
        ).returncode  # fmt: skip
    finally:
        for service in package.services:
            runner(["docker", "rm", "-f", container(package, service)])
