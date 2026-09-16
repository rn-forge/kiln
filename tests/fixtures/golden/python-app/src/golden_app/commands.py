"""The commands this repo's CLI exposes.

A command function is all a repository writes. `CliApp.from_config` builds
the application around it — the root callback, the standard
`--log-level`/`--json` flags, the error-to-exit-code mapping — from the
`[cli]` table in `.rn-forge/kiln/config.toml`.
"""

from __future__ import annotations

from rn_forge.commons import console

from golden_app import greet


def hello(name: str) -> None:
    """Print a greeting for NAME."""
    console.print(greet(name))
