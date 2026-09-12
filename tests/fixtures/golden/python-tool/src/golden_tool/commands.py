"""The commands this repo's CLI exposes.

A command function is all a repository writes. The application around it — the
root callback, the standard `--log-level`/`--json` flags, the
error-to-exit-code mapping — is built from the `[cli]` table in
`.rn-forge/kiln/config.toml` by `rn_forge.cli.declare` (kiln ADR-0009).
"""

from __future__ import annotations

from rn_forge.cli import console

from golden_tool import greet


def hello(name: str) -> None:
    """Print a greeting for NAME.

    ``name`` has no default, so Typer makes it a positional argument — a
    parameter with a default would become a ``--name`` option instead. That is
    Typer's rule, and it is reachable from here without importing Typer, which
    `.importlinter` forbids in product code.
    """
    console.print(greet(name))
