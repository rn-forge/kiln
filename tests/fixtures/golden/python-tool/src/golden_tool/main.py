"""The console-script entry point.

The command line is declared in `.rn-forge/kiln/config.toml` under `[cli]`
and built from that declaration by `CliApp.from_config`. `[project.scripts]`
points at `app` itself; there is no `main()`. `CliApp.__call__` returns the
mapped exit code.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.cli import CliApp

CONFIG = Path(__file__).resolve().parents[2] / ".rn-forge" / "kiln" / "config.toml"

app = CliApp.from_config(CONFIG)
