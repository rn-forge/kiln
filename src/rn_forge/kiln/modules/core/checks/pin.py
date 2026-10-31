"""`kiln.pin` — the running kiln is the one `[kiln] ref` pins.

Reads only `config`, so it stays render-free. A branch ref is the interim
before kiln's first release and is not compared. kiln's own repository runs its
working tree and needs no pin.
"""

from __future__ import annotations

import re
from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln import __version__
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig

__all__ = ["MISMATCH", "MISSING", "NAME", "check"]

NAME = "kiln-pin"
MISMATCH = "kiln.pin-mismatch"
MISSING = "kiln.pin-missing"

_TAG = re.compile(r"^v(\d+\.\d+\.\d+)$")
_OWN_MODULE = "rn_forge.kiln"


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Report a missing pin, or a tag pin that names another kiln than the running one."""
    del root
    label = CONFIG_PATH.as_posix()
    pin = getattr(config.document, "kiln", None)
    if pin is None:
        if config.module == _OWN_MODULE:
            return []
        return [
            Finding(
                MISSING,
                Severity.WARNING,
                "no [kiln] ref — pin the kiln this repository runs",
                path=label,
            )
        ]
    tag = _TAG.match(pin.ref)
    if tag is None or tag.group(1) == __version__:
        return []
    return [
        Finding(
            MISMATCH,
            Severity.ERROR,
            f"[kiln] ref pins kiln {tag.group(1)}, but kiln {__version__} is "
            f"running — run kiln through `task`, or move [kiln] ref",
            path=label,
        )
    ]
