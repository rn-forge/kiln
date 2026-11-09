"""S16.7.1 — `KilnConfig.docs_site_dir` is the one place the build directory is decided."""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.kiln.config import KilnConfig

BASE = """
schema_version = 1

[repository]
name = "demo"
owner = "rn-forge"
archetype = "python-tool"
"""


@pytest.mark.parametrize(
    ("docs", "expected"),
    [
        ("", ".docs-site"),
        ('\n[docs]\nprofile = "mkdocs"\nsite_dir = "out/site"\n', "out/site"),
        ('\n[docs]\nprofile = "mkdocs"\nsite_dir = ""\n', "site"),
    ],
)
def test_s16_7_1_4_the_property(tmp_path: Path, docs: str, expected: str) -> None:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(BASE + docs, encoding="utf-8")
    assert KilnConfig.load(tmp_path).docs_site_dir == expected
