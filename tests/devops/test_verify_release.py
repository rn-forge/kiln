"""Tests for `kiln-devops verify-release`: install a published release and import it."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from rn_forge.kiln.devops import cli, verify_release
from rn_forge.kiln.devops.verify_release import Spec


class Runner:
    def __init__(self, install_codes: list[int] | None = None) -> None:
        self.calls: list[tuple[list[str], dict[str, str]]] = []
        self.install_codes = install_codes or [0]

    def __call__(
        self,
        command: list[str],
        env: dict[str, str] | None = None,
        capture: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, env or {}))
        code = 0
        if command[:3] == ["uv", "pip", "install"]:
            code = (
                self.install_codes.pop(0)
                if len(self.install_codes) > 1
                else self.install_codes[0]
            )
        return subprocess.CompletedProcess(command, code, stdout="")

    def commands(self) -> list[list[str]]:
        return [c for c, _ in self.calls]


def _spec(source: str, directory: str = ".") -> Spec:
    return Spec(
        name="pkg-a",
        module="pkg_a",
        version="1.2.3",
        tag="pkg-a-v1.2.3",
        source=source,
        repository_url="https://github.com/o/r",
        dir=directory,
    )


def test_s15_8_4_1_pypi() -> None:
    runner = Runner()
    assert verify_release.run(_spec("pypi"), runner, sleep=lambda _: None) == 0
    commands = runner.commands()
    assert commands[0][:2] == ["uv", "venv"]
    install = next(c for c in commands if c[:3] == ["uv", "pip", "install"])
    assert "--no-cache" in install
    assert install[-1] == "pkg-a==1.2.3"
    assert not any("git+" in part for c in commands for part in c)
    venv = commands[0][-1]
    assert runner.calls[1][1]["VIRTUAL_ENV"] == venv
    assert commands[-1] == [f"{venv}/bin/python", "-c", "import pkg_a"]


def test_s15_8_4_1_pypi_retries_then_fails() -> None:
    runner = Runner(install_codes=[1])
    waits: list[float] = []
    assert (
        verify_release.run(_spec("pypi"), runner, sleep=waits.append, attempts=3) == 1
    )
    installs = [c for c in runner.commands() if c[:3] == ["uv", "pip", "install"]]
    assert len(installs) == 3
    assert len(waits) == 2
    assert not any(c[-2:-1] == ["-c"] for c in runner.commands())


def test_s15_8_4_1_pypi_retries_until_published() -> None:
    runner = Runner(install_codes=[1, 0])
    assert verify_release.run(_spec("pypi"), runner, sleep=lambda _: None) == 0


def test_s15_8_4_2_tag() -> None:
    runner = Runner()
    assert verify_release.run(_spec("git", "packages/a"), runner) == 0
    commands = runner.commands()
    assert commands[0] == [
        "git",
        "fetch",
        "--no-tags",
        "origin",
        "refs/tags/pkg-a-v1.2.3",
    ]
    install = next(c for c in commands if c[:3] == ["uv", "pip", "install"])
    assert install[-1] == (
        "pkg-a @ git+https://github.com/o/r@pkg-a-v1.2.3#subdirectory=packages/a"
    )
    assert "--no-cache" in install


def test_s15_8_4_2_tag_of_a_single_package_has_no_subdirectory() -> None:
    runner = Runner()
    spec = Spec("tool", "tool", "1.0.0", "v1.0.0", "git", "https://github.com/o/r", ".")
    assert verify_release.run(spec, runner) == 0
    install = next(c for c in runner.commands() if c[:3] == ["uv", "pip", "install"])
    assert install[-1] == "tool @ git+https://github.com/o/r@v1.0.0"


def test_s15_8_4_cli_tag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-tool"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    (tmp_path / "src" / "my_tool").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REPOSITORY_URL", "https://github.com/o/r")
    seen: list[Spec] = []
    monkeypatch.setattr(
        verify_release, "run", lambda spec, runner, **_: seen.append(spec) or 0
    )
    assert cli.main(["verify-release", "--source", "git", "v1.0.0"]) == 0
    assert seen == [
        Spec(
            "my-tool",
            "my_tool",
            "1.0.0",
            "v1.0.0",
            "git",
            "https://github.com/o/r",
            ".",
        )
    ]
