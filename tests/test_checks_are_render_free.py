"""`kiln doctor` never loads the generation engine.

`task validate` runs `kiln doctor` on every CI run (kiln ADR-0006), so the
render-free half has to stay cheap: importing it must not drag in Jinja,
`rn_forge.commons.generation` or `rn_forge.commons.text.templates`.
`.importlinter` carries the Jinja half of this; it cannot carry the engine
half, because import-linter rejects subpackages of external packages. So this
imports the checks in a clean interpreter and asks what came with them.
"""

from __future__ import annotations

import subprocess
import sys

PROBE = """
import sys
import rn_forge.kiln.checks  # noqa: F401
EXTRA
watched = ("jinja2", "rn_forge.commons.generation", "rn_forge.commons.text.templates")
loaded = sorted(
    name
    for name in sys.modules
    if name in watched or name.startswith(tuple(w + "." for w in watched))
)
print(",".join(loaded))
"""


def _run(extra: str = "") -> str:
    result = subprocess.run(
        [sys.executable, "-c", PROBE.replace("EXTRA", extra)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_importing_the_checks_loads_no_renderer() -> None:
    loaded = _run()
    assert loaded == "", f"`kiln doctor` pulled in a renderer: {loaded}"


def test_s7_3_1_1_probe_sees_the_engine() -> None:
    loaded = _run("import rn_forge.commons.generation")
    assert "rn_forge.commons.generation" in loaded.split(",")
