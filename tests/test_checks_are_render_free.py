"""`kiln doctor` never loads the generation engine.

`task validate` runs `kiln doctor` on every CI run (kiln ADR-0010), so the
render-free half has to stay cheap: importing it must not drag in Jinja or
`rn_forge.tooling.generation`. `.importlinter` carries the Jinja half of this;
it cannot carry the engine half, because import-linter rejects subpackages of
external packages. So this imports the checks in a clean interpreter and asks
what came with them.
"""

from __future__ import annotations

import subprocess
import sys

PROBE = """
import sys
import rn_forge.kiln.checks  # noqa: F401

loaded = sorted(
    name
    for name in sys.modules
    if name == "jinja2"
    or name == "rn_forge.tooling.generation"
    or name.startswith(("jinja2.", "rn_forge.tooling.generation."))
)
print(",".join(loaded))
"""


def test_importing_the_checks_loads_no_renderer() -> None:
    result = subprocess.run(
        [sys.executable, "-c", PROBE], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "", (
        f"`kiln doctor` pulled in a renderer: {result.stdout.strip()}"
    )
