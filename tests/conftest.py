"""Shared helpers for the check tests.

A check reads a repo, so every test needs a repo: the smallest tree that
carries a valid `.rn-forge/kiln/config.toml` and whatever the rule under test
looks at.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

CONFIG = """
schema_version = 1

[repository]
name = "example"
owner = "rn-forge"
archetype = "{archetype}"
lifecycle = {lifecycle}

[docs]
profile = "{docs}"

[ci]
provider = "github"
"""


@pytest.fixture
def repo(tmp_path: Path):
    """Build a repo root with a kiln config, and return its path."""

    def build(
        archetype: str = "python-app",
        lifecycle: bool = False,
        docs: str = "none",
        **files: str,
    ) -> Path:
        config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            CONFIG.format(
                archetype=archetype, lifecycle=str(lifecycle).lower(), docs=docs
            ),
            encoding="utf-8",
        )
        for relative, content in files.items():
            path = tmp_path / relative.replace("__", "/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return tmp_path

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


@pytest.fixture(scope="session")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], Path]:
    """Return `(archetype) -> Path` to a repository `kiln new` rendered once.

    The result is read-only; a test that changes it copies it first.
    """
    from rn_forge.kiln import commands

    cache: dict[str, Path] = {}

    def build(archetype: str) -> Path:
        if archetype in cache:
            return cache[archetype]
        parent = tmp_path_factory.mktemp(archetype)
        with pytest.MonkeyPatch.context() as patch:
            patch.chdir(parent)
            commands.new(
                Path(archetype),
                archetype=archetype,
                docs="mkdocs",
                owner="rn-forge",
                yes=True,
                **FLAGS.get(archetype, {}),
            )
        root = parent / archetype
        if archetype == "python-lib":
            for args in (
                ("init", "-q"),
                ("remote", "add", "origin", "https://github.com/rn-forge/python-lib"),
            ):
                subprocess.run(
                    ["git", *args], cwd=root, check=True, capture_output=True
                )
            for package in ("lib-alpha", "lib-beta"):
                commands.generate_package(package, path=root)
        cache[archetype] = root
        return root

    return build


@pytest.fixture(autouse=True)
def _default_owner(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Give `kiln new` and `kiln init` `owner="rn-forge"` unless the test says not to.

    S16.6.8 made the owner required; a test about the owner itself asks for the
    `ownerless` fixture and passes its own.
    """
    if "ownerless" in request.fixturenames:
        return
    import functools

    from rn_forge.kiln import commands

    for name in ("new", "init"):
        original = getattr(commands, name)

        @functools.wraps(original)
        def with_owner(*args: object, _original=original, **kwargs: object) -> object:
            kwargs.setdefault("owner", "rn-forge")
            return _original(*args, **kwargs)

        monkeypatch.setattr(commands, name, with_owner)


@pytest.fixture
def ownerless() -> None:
    """Opt a test out of `_default_owner`."""


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
