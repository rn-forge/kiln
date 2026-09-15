"""The console-script entry point.

There is no app construction here, and that is the point of kiln ADR-0009: the
command line is *declared* in `.rn-forge/kiln/config.toml` under `[cli]` and
built from that declaration by `CliApp.from_config`. A repository writes
command functions and this three-line module, and nothing else. There is no
`main()`: `[project.scripts]` points at `app` itself, and `CliApp.__call__`
returns the mapped exit code.

The config document is found relative to this file because a golden repo runs
from its checkout.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.cli import CliApp

CONFIG = Path(__file__).resolve().parents[2] / ".rn-forge" / "kiln" / "config.toml"

app = CliApp.from_config(CONFIG)
