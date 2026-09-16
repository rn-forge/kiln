"""Shared helpers for the check tests.

A check reads a repo, so every test needs a repo: the smallest tree that
carries a valid `.rn-forge/kiln/config.toml` and whatever the rule under test
looks at.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CONFIG = """
schema_version = 1

[repository]
name = "example"
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
