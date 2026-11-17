"""Shared helpers for the check tests.

A check reads a repo, so every test needs a repo: the smallest tree that
carries a valid `.rn-forge/kiln/config.toml` and whatever the rule under test
looks at.
"""

from __future__ import annotations

import ast
import fcntl
import json
import os
import shutil
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from rn_forge.commons.findings import Finding
from rn_forge.commons.generation import Action

if TYPE_CHECKING:
    from rn_forge.kiln.config import KilnConfig

CONFIG = """
schema_version = 1

[repository]
name = "{name}"
owner = "rn-forge"
archetype = "{archetype}"
lifecycle = {lifecycle}

[docs]
profile = "{docs}"
{docs_extra}{ci}"""

LIB_PACKAGES = ["packages/alpha", "packages/beta"]
"""The member packages a `python-lib` test config lists."""

MISSING_REQUIRED = """
[project]
name = "example"
version = "0.1.0"
dependencies = []
"""
"""A `pyproject.toml` that lacks the dependency `rn-forge-commons`."""


def write_config(
    root: Path,
    archetype: str = "python-app",
    *,
    lifecycle: bool = False,
    docs: str = "none",
    docs_extra: str = "",
    name: str = "example",
    provider: str | None = None,
    release: str | None = None,
    sonar: bool | None = None,
    frontend: str | None = None,
    backend: str | None = None,
    packages: list[str] | None = None,
    tail: str = "",
) -> Path:
    """Write a kiln config under *root* and return *root*.

    `docs_extra` goes inside `[docs]`; `tail` goes after every table.
    """
    ci = ""
    if provider is not None:
        ci += f'provider = "{provider}"\n'
    if sonar is not None:
        ci += f"sonar = {str(sonar).lower()}\n"
    if release is not None:
        ci += f'release = "{release}"\n'
    if ci:
        ci = "\n[ci]\n" + ci
    text = CONFIG.format(
        name=name,
        archetype=archetype,
        lifecycle=str(lifecycle).lower(),
        docs=docs,
        docs_extra=f"{docs_extra}\n" if docs_extra else "",
        ci=ci,
    )
    fields = {
        "backend": backend and json.dumps(backend),
        "frontend": frontend and json.dumps(frontend),
        "packages": None if packages is None else json.dumps(packages),
    }
    lines = [f"{key} = {value}" for key, value in fields.items() if value is not None]
    if lines:
        text += f'\n[archetype."{archetype}"]\n' + "\n".join(lines) + "\n"
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(text + tail, encoding="utf-8")
    return root


@pytest.fixture
def repo(tmp_path: Path):
    """Build a repo root with a kiln config, and return its path.

    `at` puts the repo in a subdirectory of the test's temporary directory;
    every keyword that `write_config` does not take is a file to write
    (`__` stands for `/`).
    """

    def build(
        archetype: str = "python-app",
        lifecycle: bool = False,
        docs: str = "none",
        *,
        at: str = "",
        release: str | None = None,
        sonar: bool | None = None,
        frontend: str | None = None,
        backend: str | None = None,
        packages: list[str] | None = None,
        tail: str = "",
        docs_extra: str = "",
        name: str = "example",
        provider: str | None = None,
        **files: str,
    ) -> Path:
        root = tmp_path / at if at else tmp_path
        write_config(
            root,
            archetype,
            lifecycle=lifecycle,
            docs=docs,
            docs_extra=docs_extra,
            name=name,
            provider=provider,
            release=release,
            sonar=sonar,
            frontend=frontend,
            backend=backend,
            packages=packages,
            tail=tail,
        )
        for relative, content in files.items():
            path = root / relative.replace("__", "/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    return build


@pytest.fixture
def write_state(tmp_path: Path):
    """Write a `state.json` with the given entries."""

    def build(entries: dict[str, object], schema_version: str = "1") -> Path:
        path = tmp_path / ".rn-forge" / "kiln" / "state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": schema_version,
                    "metadata": {"kiln_version": "test", "config_hash": "0"},
                    "entries": entries,
                }
            ),
            encoding="utf-8",
        )
        return path

    return build


# The flags `kiln new` needs for an archetype beyond `--archetype` and `--docs`.
FLAGS: dict[str, dict[str, str]] = {
    "python-web-api": {"backend": "fastapi"},
    "python-web-app": {"backend": "fastapi", "frontend": "angular"},
}


# The archetypes whose `kiln new` runs a slow Nx workspace build; one copy is
# built per test run and shared by every xdist worker.
SHARED_ARCHETYPES = ("node-lib", "python-web-app")


@pytest.fixture(scope="session")
def shared_build(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[str, Callable[[Path], None]], Path]:
    """Return `(name, build) -> Path`: builds `name` once per test run, across
    xdist workers, and returns its directory; the result is read-only.
    """

    def run(name: str, build: Callable[[Path], None]) -> Path:
        base = tmp_path_factory.getbasetemp()
        if os.environ.get("PYTEST_XDIST_WORKER"):
            base = base.parent
        shared = base / "shared"
        shared.mkdir(parents=True, exist_ok=True)
        target = shared / name
        marker = shared / f"{name}.done"
        with (shared / f"{name}.lock").open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            if not marker.exists():
                shutil.rmtree(target, ignore_errors=True)
                target.mkdir()
                build(target)
                marker.touch()
        return target

    return run


def _render(parent: Path, archetype: str) -> Path:
    """Run `kiln new` for `archetype` in `parent` and return the new root."""
    from rn_forge.kiln import commands
    from rn_forge.kiln.modules.core import cycle

    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(parent)
        new_repo(
            Path(archetype),
            archetype=archetype,
            docs="mkdocs",
            yes=True,
            **FLAGS.get(archetype, {}),
        )
    root = parent / archetype
    if archetype == "python-lib":
        for args in (
            ("init", "-q"),
            ("remote", "add", "origin", "https://github.com/rn-forge/python-lib"),
        ):
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
        for package in ("lib-alpha", "lib-beta"):
            commands.generate_package(package, path=root)
        # generate_package writes a bare skeleton, so the library's
        # packages carry their starter.
        cycle.apply(root, starters="packages/")
    return root


@pytest.fixture(scope="session")
def rendered(
    tmp_path_factory: pytest.TempPathFactory,
    shared_build: Callable[[str, Callable[[Path], None]], Path],
) -> Callable[[str], Path]:
    """Return `(archetype) -> Path` to a repository `kiln new` rendered once.

    The result is read-only; a test that changes it copies it first.
    """
    cache: dict[str, Path] = {}

    def build(archetype: str) -> Path:
        if archetype in cache:
            return cache[archetype]
        if archetype in SHARED_ARCHETYPES:
            root = (
                shared_build(archetype, lambda parent: _render(parent, archetype))
                / archetype
            )
        else:
            root = _render(tmp_path_factory.mktemp(archetype), archetype)
        cache[archetype] = root
        return root

    return build


def new_repo(directory: Path, **kwargs: Any) -> None:
    """`commands.new` with `owner="rn-forge"` unless the call gives one.

    The owner is required; a test about the owner itself calls
    `commands.new` directly.
    """
    from rn_forge.kiln import commands

    kwargs.setdefault("owner", "rn-forge")
    commands.new(directory, **kwargs)


@pytest.fixture(scope="session")
def kiln_remote(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    """A local bare repository with one commit on `feature/v1`, tagged `v0.0.1`.

    Returns its `file://` URL and the commit's SHA.
    """
    base = tmp_path_factory.mktemp("kiln-remote")
    work = base / "work"
    work.mkdir()
    git(work, "init", "-q", "-b", "feature/v1")
    git(work, "commit", "-q", "--allow-empty", "-m", "initial")
    git(work, "tag", "v0.0.1")
    bare = base / "kiln.git"
    git(base, "clone", "-q", "--bare", str(work), str(bare))
    return bare.as_uri(), git(work, "rev-parse", "HEAD")


@pytest.fixture(scope="session")
def kiln_remote_sha(kiln_remote: tuple[str, str]) -> str:
    """The commit `feature/v1` and `v0.0.1` name in the local kiln remote."""
    return kiln_remote[1]


@pytest.fixture(autouse=True)
def _local_kiln_remote(
    kiln_remote: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point `kiln_ref.REMOTE` at the local remote, so no test reaches the network."""
    from rn_forge.kiln.modules.core import kiln_ref

    monkeypatch.setattr(kiln_ref, "REMOTE", kiln_remote[0])


@pytest.fixture(autouse=True, scope="session")
def _no_uv_locked() -> Iterator[None]:
    """CI sets UV_LOCKED=1 for kiln's own lock; tests that run `task setup` in a
    repository they just wrote (no uv.lock yet) must not inherit it.

    Session-scoped with its own MonkeyPatch, so a test's `monkeypatch.undo()`
    cannot bring the variable back.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.delenv("UV_LOCKED", raising=False)
        yield


class _Requires(list):
    """The marks for `requires`, usable as a decorator, `marks=` or `pytestmark`."""

    def __call__(self, func):
        for mark in self:
            func = mark(func)
        return func


def requires(*tools: str) -> _Requires:
    """Mark a test as needing live tools, and skip it where one is absent.

    `pnpm` is the exception: a missing `pnpm` skips only when `CI` is unset.
    """
    marks = _Requires()
    for tool in tools:
        marker = tool if tool in ("task", "pnpm") else "tool"
        marks.append(getattr(pytest.mark, f"requires_{marker}"))
        absent = shutil.which(tool) is None
        if tool == "pnpm":
            absent = absent and not os.environ.get("CI")
        marks.append(pytest.mark.skipif(absent, reason=f"{tool} is not on PATH"))
    return marks


IGNORE = shutil.ignore_patterns(
    ".venv",
    ".uv-cache",
    ".ruff_cache",
    ".import_linter_cache",
    ".pytest_cache",
    ".docs-site",
    ".git",
    "__pycache__",
)
"""What a copy of a rendered golden leaves behind."""


@pytest.fixture
def rendered_copy(
    tmp_path: Path, rendered: Callable[[str], Path]
) -> Callable[..., Path]:
    """Return `(archetype, name="repo") -> Path`: a writable copy of the
    rendered *archetype* at `tmp_path / name`.
    """

    def copy(archetype: str, name: str = "repo") -> Path:
        root = tmp_path / name
        shutil.copytree(rendered(archetype), root, ignore=IGNORE)
        return root

    return copy


def git(cwd: Path, *args: str) -> str:
    """Run `git` in *cwd* as a throwaway committer; return its stripped stdout."""
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def snapshot(*roots: Path) -> dict[str, bytes]:
    """Every file under *roots*, by absolute path, with its bytes."""
    return {
        str(path): path.read_bytes()
        for root in roots
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def actions(root: Path, tmp_path: Path) -> dict[str, Action]:
    """The action `cycle.plan` takes for each key of *root*."""
    from rn_forge.kiln.modules.core import cycle

    return {
        change.key: change.action
        for change in cycle.plan(root, home=tmp_path / "home").changes
    }


def run_check(name: str, root: Path) -> list[Finding]:
    """Run the registered check *name* over *root*; an unregistered one raises."""
    from rn_forge.kiln import checks
    from rn_forge.kiln.config import KilnConfig

    registered = {check.name: check for check in checks.CHECKS}
    return registered[name].run(KilnConfig.load(root), root)


def module_findings(module: str, config: KilnConfig, root: Path) -> list[Finding]:
    """Stand in for the removed `Module.checks()`: every registered check of *module*."""
    from rn_forge.kiln import checks

    return [
        finding
        for entry in checks.CHECKS
        if entry.module == module
        for finding in entry.run(config, root)
    ]


SRC = Path(__file__).resolve().parents[1] / "src" / "rn_forge" / "kiln"


def oversized(
    *directories: str, max_lines: int | None = None, max_function: int = 60
) -> list[str]:
    """Every file over *max_lines* and function over *max_function* lines under SRC's *directories*."""
    found: list[str] = []
    for directory in directories:
        for path in sorted((SRC / directory).rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            label = path.relative_to(SRC).as_posix()
            if max_lines is not None and len(text.splitlines()) > max_lines:
                found.append(f"{label} ({len(text.splitlines())} lines)")
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    length = (node.end_lineno or node.lineno) - node.lineno + 1
                    if length > max_function:
                        found.append(f"{label}:{node.lineno} {node.name} ({length})")
    return found
