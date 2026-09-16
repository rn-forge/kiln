"""The console-script entry point.

`[project.scripts]` points at `app` itself; there is no `main()`.
`CliApp.__call__` returns the mapped exit code. The CLI declaration is read
from the packaged `cli.toml`, not from `.rn-forge/kiln/config.toml`: kiln runs
from inside other repos' environments.
"""

from __future__ import annotations

import tomllib
from importlib.resources import files

from rn_forge.cli import CliApp

SURFACE = tomllib.loads(
    files("rn_forge.kiln").joinpath("cli.toml").read_text(encoding="utf-8")
)

app = CliApp.from_config(SURFACE)
