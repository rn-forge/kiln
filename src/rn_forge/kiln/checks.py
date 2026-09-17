"""The render-free checks, and the registry `kiln doctor` runs them from.

`.importlinter` forbids anything under `rn_forge.kiln.modules.*.checks` from
importing `jinja2` or `rn_forge.tooling.generation`. `kiln doctor --full` is
where the render-dependent checks live.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd.checks import entrypoint, pins
from rn_forge.kiln.modules.core.checks import generated
from rn_forge.kiln.modules.docs.checks import nav, site, structure
from rn_forge.kiln.modules.instructions.checks import hygiene
from rn_forge.kiln.modules.python.checks import pyproject, rn_forge_deps
from rn_forge.kiln.modules.tasks.checks import layout

__all__ = ["CHECKS", "Check", "names", "run"]

CheckFunction = Callable[[KilnConfig, Path], list[Finding]]


@dataclass(frozen=True, slots=True)
class Check:
    """One render-free check, and the module that owns it."""

    name: str
    module: str
    run: CheckFunction


CHECKS: tuple[Check, ...] = (
    Check(generated.NAME, "core", generated.check),
    Check(rn_forge_deps.NAME, "python", rn_forge_deps.check),
    Check(pyproject.NAME, "python", pyproject.check),
    Check(layout.NAME, "tasks", layout.check),
    Check(entrypoint.NAME, "cicd", entrypoint.check),
    Check(pins.NAME, "cicd", pins.check),
    Check(structure.NAME, "docs", structure.check),
    Check(nav.NAME, "docs", nav.check),
    Check(site.NAME, "docs", site.check),
    Check(hygiene.NAME, "instructions", hygiene.check),
)
"""Every check `kiln doctor` runs, in module apply order."""


def names() -> tuple[str, ...]:
    """The name each check answers to on `--only`."""
    return tuple(check.name for check in CHECKS)


def run(root: Path, only: str | None = None) -> list[Finding]:
    """Run every check over *root*, or just the one *only* names.

    Raises:
        AppException: *only* names no check, or *root*'s config cannot be read.
    """
    selected: Sequence[Check] = CHECKS
    if only is not None:
        selected = [check for check in CHECKS if check.name == only]
        if not selected:
            raise AppException(
                "Unknown check {!r} — this kiln runs {}", only, ", ".join(names())
            )

    config = KilnConfig.load(root)
    findings: list[Finding] = []
    for check in selected:
        findings.extend(check.run(config, root))
    return findings
