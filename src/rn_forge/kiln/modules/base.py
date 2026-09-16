"""The module contract, and the registry that composes modules.

A module owns one config section, the `kiln new` options that set it, the
artifacts it renders and the checks over what it rendered — and nothing else.
kiln owns the composition: which modules an archetype enables, the union of
their options, and the order they run in.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding
from rn_forge.commons.lang.models import StrictModel

if TYPE_CHECKING:
    from rn_forge.tooling.generation import Artifact

    from rn_forge.kiln.archetypes import Archetype
    from rn_forge.kiln.config import KilnConfig

__all__ = ["KilnModule", "ModuleRegistry", "Option"]


@dataclass(frozen=True, slots=True)
class Option:
    """One `kiln new` flag a module adds.

    Args:
        flag: The flag's name, without the leading `--`.
        key: The dotted config path the flag sets.
        help: One line for `--help`.
    """

    flag: str
    key: str
    help: str


class KilnModule(Protocol):
    """What every kiln module implements."""

    @property
    def name(self) -> str:
        """The module's name, as `archetype.toml` lists it."""
        ...

    @property
    def section(self) -> str | None:
        """The top-level config table this module owns, or None for none."""
        ...

    @property
    def config_model(self) -> type[StrictModel] | None:
        """The section's schema; its defaults are kiln's defaults layer."""
        ...

    def options(self) -> Sequence[Option]:
        """The `kiln new` flags this module adds."""
        ...

    def artifacts(self, config: KilnConfig) -> Sequence[Artifact]:
        """Render every artifact this module owns for *config*, writing nothing."""
        ...

    def checks(self, config: KilnConfig, root: Path) -> Sequence[Finding]:
        """Check what this module owns in the repo at *root*."""
        ...


class ModuleRegistry:
    """Every module this kiln ships, keyed by name, in registration order.

    Raises:
        AppException: From the constructor or :meth:`register`, when a module's
            name, section or option is already claimed by another module.
    """

    def __init__(self, modules: Iterable[KilnModule] = ()) -> None:
        self._modules: dict[str, KilnModule] = {}
        for module in modules:
            self.register(module)

    def register(self, module: KilnModule) -> None:
        """Add *module*, refusing any name, section or option it would share."""
        if module.name in self._modules:
            raise AppException("Module {!r} is registered twice", module.name)
        for other in self._modules.values():
            if module.section is not None and module.section == other.section:
                raise AppException(
                    "Modules {!r} and {!r} both claim the [{}] config section",
                    other.name,
                    module.name,
                    module.section,
                )
            shared = {o.flag for o in other.options()} & {
                o.flag for o in module.options()
            }
            for flag in sorted(shared):
                raise AppException(
                    "Modules {!r} and {!r} both declare the option --{}",
                    other.name,
                    module.name,
                    flag,
                )
        self._modules[module.name] = module

    @property
    def modules(self) -> tuple[KilnModule, ...]:
        """Every registered module, in registration order."""
        return tuple(self._modules.values())

    def for_archetype(self, archetype: Archetype) -> tuple[KilnModule, ...]:
        """The modules *archetype* enables, in the order its manifest lists them.

        Raises:
            AppException: The manifest names a module this kiln does not register.
        """
        unknown = [name for name in archetype.modules if name not in self._modules]
        if unknown:
            raise AppException(
                "Archetype {!r} names unregistered module(s) {} — this kiln registers {}",
                archetype.name,
                ", ".join(unknown),
                ", ".join(self._modules),
            )
        return tuple(self._modules[name] for name in archetype.modules)
