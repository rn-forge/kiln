"""The committed `.rn-forge/kiln/config.toml`, validated.

`KilnConfig` is what every module's artifacts and checks read. Loading one goes
through the config manager, so the file is validated against this kiln's
schema every time it is read.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rn_forge.kiln.modules.cicd import registry
from rn_forge.kiln.modules.cicd.config import CiConfig, resolve_release
from rn_forge.kiln.modules.core.config.schema import KilnPin, RootConfig
from rn_forge.kiln.modules.core.names import module_name
from rn_forge.kiln.modules.docs.config import DocsConfig
from rn_forge.kiln.modules.node.angular import WEB_PROJECT
from rn_forge.kiln.modules.python.config import (
    ArchetypeConfig,
    NodeLibConfig,
    WebAppConfig,
)
from rn_forge.kiln.modules.tasks.config import TasksConfig

if TYPE_CHECKING:
    from rn_forge.kiln.modules.tasks.surface import PublicTask

__all__ = ["CONFIG_PATH", "KilnConfig"]

CONFIG_PATH = Path(".rn-forge/kiln/config.toml")
"""Where a kiln repo's one committed input lives."""


@dataclass(frozen=True, slots=True)
class KilnConfig:
    """A validated config: the composed document, and typed reads of it."""

    document: RootConfig

    @classmethod
    def load(cls, root: Path) -> KilnConfig:
        """Read and validate *root*'s config.

        Raises:
            AppException: The file is missing, unparseable, from a newer kiln,
                or invalid — naming every failing key by its dotted path.
        """
        # The manager composes module schemas, and modules import this class.
        from rn_forge.kiln.modules.core.config.manager import ConfigManager

        return ConfigManager().load(root)

    @property
    def archetype(self) -> str:
        """The repo's shape and dependency set."""
        return self.document.repository.archetype

    @property
    def lifecycle(self) -> bool:
        """Whether the repo installs itself; the python-tool archetype always does."""
        return self.document.repository.lifecycle or self.archetype == "python-tool"

    @property
    def name(self) -> str:
        """The repository name."""
        return self.document.repository.name

    @property
    def owner(self) -> str:
        """The GitHub owner that holds the repository."""
        return self.document.repository.owner

    @property
    def ci(self) -> CiConfig:
        """The `[ci]` section, or its defaults."""
        section = getattr(self.document, "ci", None)
        return section if isinstance(section, CiConfig) else CiConfig()

    @property
    def docs(self) -> DocsConfig:
        """The `[docs]` section, or its defaults."""
        section = getattr(self.document, "docs", None)
        return section if isinstance(section, DocsConfig) else DocsConfig()

    @property
    def tasks(self) -> TasksConfig:
        """The `[tasks]` section, or its defaults."""
        section = getattr(self.document, "tasks", None)
        return section if isinstance(section, TasksConfig) else TasksConfig()

    @property
    def kiln_pin(self) -> KilnPin | None:
        """The `[kiln]` pin, or `None` when the repository declares none."""
        return getattr(self.document, "kiln", None)

    @property
    def archetype_section(self) -> ArchetypeConfig | None:
        """The `[archetype]` section, or `None` when the repository declares none."""
        section = getattr(self.document, "archetype", None)
        return section if isinstance(section, ArchetypeConfig) else None

    @property
    def docs_profile(self) -> str:
        """`mkdocs`, `external` or `none`."""
        return self.docs.profile

    @property
    def docs_site_dir(self) -> str:
        """Where `mkdocs` builds the site: `[docs] site_dir`, else mkdocs's own `site`."""
        return self.docs.site_dir or "site"

    @property
    def ci_provider(self) -> str:
        """`github`; `ado` is reserved."""
        return self.ci.provider

    @property
    def release(self) -> str:
        """The release mode: `[ci] release`, or the archetype's default.

        Raises:
            ValueError: the mode does not fit the archetype.
        """
        return resolve_release(self.ci, self.archetype)

    @property
    def licenses_enabled(self) -> bool:
        """Whether the registry's licences check runs for this repository."""
        return "licenses" in self.ci_checks

    @property
    def ci_checks(self) -> frozenset[str]:
        """The names of the registry's CI checks that run for this repository."""
        return registry.enabled_names(self.ci, self.archetype, len(self.packages))

    def ci_matrix(self, *, every_archetype: bool = False) -> str:
        """The CI checks matrix: this archetype's column, or every archetype's."""
        return registry.render_matrix(None if every_archetype else self.archetype)

    def public_tasks(self) -> list[PublicTask]:
        """Every task the repository's task files expose."""
        # tasks.surface imports this class, so a module-level import cycles.
        from rn_forge.kiln.modules.tasks.surface import public_tasks

        return public_tasks(self)

    @property
    def is_workspace(self) -> bool:
        """Whether the repository is a `python-lib` workspace."""
        return self.archetype == "python-lib"

    @property
    def is_web(self) -> bool:
        """Whether the repository has an API member: `python-web-api` or `python-web-app`."""
        return self.archetype in {"python-web-api", "python-web-app"}

    @property
    def is_web_app(self) -> bool:
        """Whether the repository is a `python-web-app`."""
        return self.archetype == "python-web-app"

    @property
    def is_node_lib(self) -> bool:
        """Whether the repository is a `node-lib`."""
        return self.archetype == "node-lib"

    @property
    def docs_packages(self) -> tuple[str, ...]:
        """The member directories the docs site covers: `packages` for `python-lib`."""
        return self.packages if self.is_workspace else ()

    @property
    def packages(self) -> tuple[str, ...]:
        """Workspace member directories: `packages` for `python-lib`, `(api_dir,)`
        for a web archetype, empty otherwise — so every per-member code path
        that already exists applies to a web archetype's one member."""
        section = self.archetype_section
        if section is None:
            return ()
        api_dir = self.api_dir
        if api_dir is not None:
            return (api_dir,)
        return tuple(section.packages_for(self.archetype))

    def module_for(self, package: str) -> str:
        """The import module of workspace member *package* (a path in `packages`)."""
        section = self.archetype_section
        if section is None:
            return module_name(Path(package).name)
        return section.module_for(self.archetype, package)

    @property
    def module(self) -> str:
        """The import module of a single-package repository: the declared one,
        else the repository name with `-` as `_`."""
        section = self.archetype_section
        declared = section.module_of(self.archetype) if section is not None else None
        return declared or module_name(self.name)

    @property
    def import_contracts(self) -> str:
        """`own` when a `python-lib` repo writes its own import contracts, else `kiln`."""
        section = self.archetype_section
        if section is None:
            return "kiln"
        return section.import_contracts_for(self.archetype)

    def _web_section(self) -> Any:
        section = self.archetype_section
        if section is None:
            return None
        return section.web_for(self.archetype)

    @property
    def backend(self) -> str | None:
        """The chosen backend framework, for a web archetype. `None` otherwise."""
        section = self._web_section()
        return section.backend if section is not None else None

    @property
    def frontend(self) -> str | None:
        """The chosen frontend, for `python-web-app`. `None` otherwise."""
        section = self._web_section()
        return section.frontend if isinstance(section, WebAppConfig) else None

    @property
    def release_group(self) -> str:
        """`independent` when a `node-lib` releases each project on its own, else `fixed`."""
        section = self.archetype_section
        node_lib = section.node_lib if section is not None else None
        if self.is_node_lib and isinstance(node_lib, NodeLibConfig):
            return node_lib.release_group
        return "fixed"

    @property
    def api_dir(self) -> str | None:
        """The API member's directory, for a web archetype. `None` otherwise."""
        section = self._web_section()
        return section.api_dir if section is not None else None

    @property
    def web_dir(self) -> str | None:
        """The frontend's directory, for `python-web-app`. `None` otherwise."""
        section = self._web_section()
        return section.web_dir if isinstance(section, WebAppConfig) else None

    @property
    def api_package(self) -> str | None:
        """The API member's distribution name, for a web archetype. `None` otherwise."""
        return f"{self.name}-api" if self.is_web else None

    @property
    def api_module(self) -> str | None:
        """The API member's import module, for a web archetype. `None` otherwise."""
        package = self.api_package
        return module_name(package) if package is not None else None

    @property
    def web_project(self) -> str | None:
        """The frontend's Nx project name, for `python-web-app`. `None` otherwise."""
        return WEB_PROJECT if self.web_dir else None

    def to_document(self) -> dict[str, Any]:
        """The config as a TOML-ready mapping, defaults included."""
        return self.document.model_dump(by_alias=True, exclude_none=True, mode="json")
