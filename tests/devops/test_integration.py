"""Tests for `kiln-devops integration`: service containers around a package's tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from rn_forge.kiln.devops import cli, integration
from rn_forge.kiln.devops.ci import Package, Service


class Runner:
    def __init__(self, pytest_code: int = 0, health: list[str] | None = None) -> None:
        self.calls: list[tuple[list[str], dict[str, str]]] = []
        self.pytest_code = pytest_code
        self.health = health or ["healthy"]

    def __call__(
        self,
        command: list[str],
        env: dict[str, str] | None = None,
        capture: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, env or {}))
        code, out = 0, ""
        if command[:2] == ["docker", "inspect"]:
            out = self.health.pop(0) if len(self.health) > 1 else self.health[0]
            if "{{.State.Status}}" in command:
                out = "running"
        elif command[0] == "uv":
            code = self.pytest_code
        return subprocess.CompletedProcess(command, code, stdout=out)

    def commands(self) -> list[list[str]]:
        return [c for c, _ in self.calls]


def _package() -> Package:
    return Package(
        "app",
        "packages/app",
        "app",
        services=(
            Service(
                "postgres",
                "postgres:17",
                ports=("5432:5432",),
                health_cmd="pg_isready -U ci",
                env={"POSTGRES_USER": "ci"},
                expose={"DATABASE_URL": "postgresql://ci@localhost:5432/ci"},
            ),
            Service(
                "redis", "redis:7", expose={"REDIS_URL": "redis://localhost:6379/0"}
            ),
        ),
    )


def _no_sleep(_: float) -> None:
    return None


def test_s15_8_2_5_run() -> None:
    runner = Runner(pytest_code=3)
    code = integration.run(_package(), runner, ["-m", "x"], sleep=_no_sleep)
    assert code == 3
    commands = runner.commands()
    pg = commands[0]
    assert pg[:3] == ["docker", "run", "-d"]
    assert pg[pg.index("--name") + 1] == "kiln-ci-app-postgres"
    assert ["-e", "POSTGRES_USER=ci"] == pg[pg.index("-e") : pg.index("-e") + 2]
    assert ["-p", "5432:5432"] == pg[pg.index("-p") : pg.index("-p") + 2]
    assert pg[pg.index("--health-cmd") + 1] == "pg_isready -U ci"
    assert pg[-1] == "postgres:17"
    redis = commands[1]
    assert "--health-cmd" not in redis and redis[-1] == "redis:7"
    inspects = [c for c in commands if c[:2] == ["docker", "inspect"]]
    assert any("kiln-ci-app-postgres" in c for c in inspects)
    pytest_call = next((c, e) for c, e in runner.calls if c[0] == "uv")
    assert pytest_call[0] == [
        "uv", "run", "--directory", "packages/app", "--package", "app",
        "pytest", "-q", "-m", "x",
    ]  # fmt: skip
    assert pytest_call[1] == {
        "DATABASE_URL": "postgresql://ci@localhost:5432/ci",
        "REDIS_URL": "redis://localhost:6379/0",
    }
    assert commands[-2:] == [
        ["docker", "rm", "-f", "kiln-ci-app-postgres"],
        ["docker", "rm", "-f", "kiln-ci-app-redis"],
    ]


def test_s15_8_2_5_run_waits_for_health() -> None:
    runner = Runner(health=["starting", "starting", "healthy"])
    package = Package("app", "a", "app", services=(_package().services[0],))
    assert integration.run(package, runner, [], sleep=_no_sleep) == 0
    inspects = [c for c in runner.commands() if c[:2] == ["docker", "inspect"]]
    assert len(inspects) == 3
    assert "{{.State.Health.Status}}" in inspects[0]
    verbs = [c[1] if c[0] == "docker" else c[0] for c in runner.commands()]
    assert verbs == ["run", "inspect", "inspect", "inspect", "uv", "rm"]


def test_s15_8_2_5_run_without_health_cmd_waits_for_running() -> None:
    runner = Runner(health=["running"])
    package = Package("app", "a", "app", services=(_package().services[1],))
    assert integration.run(package, runner, [], sleep=_no_sleep) == 0
    inspect = next(c for c in runner.commands() if c[:2] == ["docker", "inspect"])
    assert "{{.State.Status}}" in inspect


def test_s15_8_2_5_run_removes_containers_when_never_healthy() -> None:
    runner = Runner(health=["unhealthy"])
    package = Package("app", "a", "app", services=(_package().services[0],))
    assert integration.run(package, runner, [], sleep=_no_sleep, attempts=3) == 1
    assert not any(c[0] == "uv" for c in runner.commands())
    assert runner.commands()[-1] == ["docker", "rm", "-f", "kiln-ci-app-postgres"]


def test_s15_8_2_6_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.uv.workspace]\nmembers = ["pkgs/*"]\n\n'
        '[tool.workspace-ci]\npytest-args = ["-x"]\n'
    )
    member = tmp_path / "pkgs/app"
    member.mkdir(parents=True)
    (member / "pyproject.toml").write_text(
        '[project]\nname = "app"\nversion = "1"\n\n'
        '[tool.workspace-ci.integration.redis]\nimage = "redis:7"\n'
    )
    monkeypatch.chdir(tmp_path)
    seen: list[tuple[str, list[str]]] = []

    def fake(
        package: Package, runner: object, pytest_args: list[str], **_: object
    ) -> int:
        seen.append((package.name, pytest_args))
        return 7

    monkeypatch.setattr(integration, "run", fake)
    assert cli.main(["integration", "app"]) == 7
    assert seen == [("app", ["-x"])]
