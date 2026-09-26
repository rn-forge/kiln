"""kiln, as pykit's lifecycle verbs see it.

`[lifecycle]` in `cli.toml` names `PRODUCT`; `rn-forge-tooling` mounts all six verbs
under `kiln self`, so the install-health check is `kiln self doctor` and
`kiln doctor` stays the repository check.
"""

from __future__ import annotations

from collections.abc import Sequence

from rn_forge.commons.findings import Finding, Severity
from rn_forge.tooling.install import Check, Link, ToolHome, ToolProduct

from rn_forge.kiln import __version__

__all__ = ["PRODUCT", "Kiln"]


def check_home(home: ToolHome) -> list[Finding]:
    """Report where kiln is, or would be, installed."""
    return [Finding("kiln.home", Severity.INFO, f"home is {home.product_dir}")]


class Kiln(ToolProduct):
    """kiln: one command on PATH, one check of its own."""

    def artifacts(self) -> Sequence[Link]:
        """Put the command on PATH."""
        return (Link("bin/kiln", "bin/kiln"),)

    def checks(self) -> Sequence[Check]:
        """Check the install's home."""
        return (check_home,)


PRODUCT = Kiln(name="kiln", version=__version__, repo="rn-forge/kiln")
