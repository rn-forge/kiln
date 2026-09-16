"""This tool as the lifecycle verbs see it.

`[cli.lifecycle]` in `.rn-forge/kiln/config.toml` names `PRODUCT`; the verbs
themselves — `install`, `upgrade`, `uninstall`, `cleanup`, `status`, `doctor` —
come from `rn-forge-tooling`.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib.metadata import version

from rn_forge.commons.findings import Finding, Severity
from rn_forge.tooling.install import Check, Link, ToolHome, ToolProduct


def check_home(home: ToolHome) -> list[Finding]:
    """Report where this tool is, or would be, installed."""
    return [Finding("golden-tool.home", Severity.INFO, f"home is {home.product_dir}")]


class GoldenTool(ToolProduct):
    """`golden-tool`: one command on PATH, one check of its own."""

    def artifacts(self) -> Sequence[Link]:
        """Put the command on PATH."""
        return (Link("bin/golden-tool", "bin/golden-tool"),)

    def checks(self) -> Sequence[Check]:
        """Check the install's home."""
        return (check_home,)


PRODUCT = GoldenTool(
    name="golden-tool", version=version("golden-tool"), repo="rn-forge/golden-tool"
)
