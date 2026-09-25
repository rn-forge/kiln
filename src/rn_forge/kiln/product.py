"""kiln, as pykit's lifecycle verbs see it.

`[cli.lifecycle]` in `cli.toml` names `PRODUCT`; `install`, `upgrade`,
`uninstall`, `cleanup` and `status` come from `rn-forge-tooling` and are
mounted flat. `doctor` is excluded from that mount — `kiln doctor` already
means inspecting a generated repository — and the install-health check this
class declares is reachable instead as `kiln self-doctor`
(`commands.self_doctor`).
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
