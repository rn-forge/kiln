"""The render-free checks, and the registry `kiln doctor` runs them from.

`.importlinter` forbids anything under `rn_forge.kiln.modules.*.checks` from
importing `jinja2` or `rn_forge.commons.generation`. `kiln doctor --full` is
where the render-dependent checks live.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rn_forge.commons.findings import Finding

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.checks import entrypoint, hooks, pins
from rn_forge.kiln.modules.core.checks import generated
from rn_forge.kiln.modules.docs.checks import derived, site, structure
from rn_forge.kiln.modules.python.checks import rn_forge_deps
from rn_forge.kiln.modules.tasks.checks import layout

__all__ = ["CHECKS", "Check", "names", "run"]

CheckFunction = Callable[[KilnConfig, Path], list[Finding]]


@dataclass(frozen=True, slots=True)
class Check:
    """One render-free check, and the module that owns it.

    An `ownership` check reads only kiln-owned files and blocks;
    `kiln new`, `kiln init`, `kiln apply` and `kiln config` fail on these
    alone. A `quality` check reads repository-owned content against a rule the
    standard defines; `kiln doctor` runs it with the rest.
    """

    name: str
    module: str
    run: CheckFunction
    scope: Literal["ownership", "quality"] = "ownership"


CHECKS: tuple[Check, ...] = (
    Check(generated.NAME, "core", generated.check),
    Check(rn_forge_deps.NAME, "python", rn_forge_deps.check, "quality"),
    Check(layout.NAME, "tasks", layout.check),
    Check(entrypoint.NAME, "cicd", entrypoint.check),
    Check(pins.NAME, "cicd", pins.check),
    Check(hooks.NAME, "cicd", hooks.check),
    Check(structure.NAME, "docs", structure.check, "quality"),
    Check(derived.NAME, "docs", derived.check),
    Check(site.NAME, "docs", site.check, "quality"),
)
"""Every check `kiln doctor` can run, in module apply order."""


def names() -> tuple[str, ...]:
    """The name of each check, in registry order."""
    return tuple(check.name for check in CHECKS)


def run(
    root: Path,
    scope: Literal["ownership"] | None = None,
) -> list[Finding]:
    """Run every check over *root*, or only the ownership checks when *scope*
    says so.

    Findings come in the order of the archetype's `modules`; checks of a module
    it does not list follow, in registry order.

    Raises:
        AppException: *root*'s config cannot be read, or its archetype is unknown.
    """
    selected: Sequence[Check] = [c for c in CHECKS if scope is None or c.scope == scope]

    config = KilnConfig.load(root)
    modules = archetypes.for_config(config).modules
    unlisted = len(modules)
    ordered = sorted(
        selected,
        key=lambda check: (
            modules.index(check.module) if check.module in modules else unlisted
        ),
    )
    findings: list[Finding] = []
    for check in ordered:
        findings.extend(check.run(config, root))
    return findings
