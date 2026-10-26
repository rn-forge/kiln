"""The console-script entry point.

`[project.scripts]` points at `app` itself; there is no `main()`.
`CliApp.__call__` returns the mapped exit code. The CLI and lifecycle
declaration, built by `build_tool_app`, is read
from the packaged `cli.toml`, not from `.rn-forge/kiln/config.toml`: kiln runs
from inside other repos' environments.
"""

from __future__ import annotations

from importlib.resources import files

from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.tooling.cli.lifecycle import build_tool_app

SURFACE = DocumentUtils.read(files("rn_forge.kiln").joinpath("cli.toml"))

app = build_tool_app(SURFACE)
