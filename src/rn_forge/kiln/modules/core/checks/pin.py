"""`kiln.pin` — the running kiln is the one `[kiln] ref` pins.

Reads only `config`, so it stays render-free. A SHA pin is compared with the
installed commit when kiln runs from an install. kiln's own repository runs its
working tree and needs no pin.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln import __version__
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig
from rn_forge.kiln.modules.core import kiln_ref
from rn_forge.kiln.product import running_install

__all__ = ["MISMATCH", "MISSING", "NAME", "check"]

NAME = "kiln-pin"
MISMATCH = "kiln.pin-mismatch"
MISSING = "kiln.pin-missing"

_OWN_MODULE = "rn_forge.kiln"


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Report a missing pin, or a tag or SHA pin that names another kiln than the running one."""
    del root
    label = CONFIG_PATH.as_posix()
    pin = config.kiln_pin
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
    if not kiln_ref.TAG.match(pin.ref):
        installed = running_install()
        if installed is None or installed.commit is None or pin.ref == installed.commit:
            return []
        return [
            Finding(
                MISMATCH,
                Severity.ERROR,
                f"[kiln] ref pins kiln {pin.ref[:12]}, but kiln "
                f"{installed.commit[:12]} is running — run kiln through `task`, "
                f"or move [kiln] ref",
                path=label,
            )
        ]
    pinned = pin.ref.removeprefix("v")
    if pinned == __version__:
        return []
    return [
        Finding(
            MISMATCH,
            Severity.ERROR,
            f"[kiln] ref pins kiln {pinned}, but kiln {__version__} is "
            f"running — run kiln through `task`, or move [kiln] ref",
            path=label,
        )
    ]
