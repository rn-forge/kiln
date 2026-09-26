"""kiln's packaged CLI declaration matches the one in its own config.

kiln declares its command line twice — in `.rn-forge/kiln/config.toml`, like
every rn-forge repo, and in `src/rn_forge/kiln/cli.toml`, which is what an
installed kiln reads (see that file's header). Two copies with nothing
comparing them is how a repo ends up with one of them wrong, so this compares
them. F4.8 makes one render the other, and this test goes away with the copy.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _table(path: Path, key: str) -> dict[str, object]:
    return tomllib.loads(path.read_text(encoding="utf-8"))[key]


def test_packaged_surface_matches_repo_config() -> None:
    packaged = _table(ROOT / "src" / "rn_forge" / "kiln" / "cli.toml", "cli")
    declared = _table(ROOT / ".rn-forge" / "kiln" / "config.toml", "cli")
    assert packaged == declared


def test_s4_5_5_packaged_lifecycle_matches_repo_config() -> None:
    packaged = _table(ROOT / "src" / "rn_forge" / "kiln" / "cli.toml", "lifecycle")
    declared = _table(ROOT / ".rn-forge" / "kiln" / "config.toml", "lifecycle")
    assert packaged == declared
