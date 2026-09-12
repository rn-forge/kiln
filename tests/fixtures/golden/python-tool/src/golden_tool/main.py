"""The console-script entry point.

There is no app construction here, and that is the point of kiln ADR-0009: the
command line is *declared* in `.rn-forge/kiln/config.toml` under `[cli]` and
built from that declaration. A repository writes command functions and this
three-line module, and nothing else.

The config document is found relative to this file because a golden repo runs
from its checkout; a tool installed into `$RNF_HOME` resolves its own root
instead, which is what `kiln`'s `umbrella.find_root` is for.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.cli import run
from rn_forge.cli.declare import declare

CONFIG = Path(__file__).resolve().parents[2] / ".rn-forge" / "kiln" / "config.toml"

app = declare(CONFIG)


def main() -> int:
    """Run the declared application and return its exit code."""
    return run(app)
