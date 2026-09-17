"""The committed `.rn-forge/kiln/config.toml`, validated.

`KilnConfig` is what every module's artifacts and checks read. Loading one goes
through the config manager, so the file is validated against this kiln's
schema every time it is read.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rn_forge.kiln.modules.cicd.config import CiConfig
from rn_forge.kiln.modules.core.config.schema import RootConfig
from rn_forge.kiln.modules.docs.config import DocsConfig
from rn_forge.kiln.modules.python.config import ArchetypeConfig, WebAppConfig

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
        """Whether the repo installs itself."""
        return self.document.repository.lifecycle

    @property
    def name(self) -> str:
        """The repository name."""
        return self.document.repository.name

    @property
    def docs_profile(self) -> str:
        """`mkdocs`, `external` or `none`."""
        docs = getattr(self.document, "docs", None)
        return docs.profile if isinstance(docs, DocsConfig) else "none"

    @property
    def ci_provider(self) -> str:
        """`github`; `ado` is reserved."""
        ci = getattr(self.document, "ci", None)
        return ci.provider if isinstance(ci, CiConfig) else "github"

    @property
    def packages(self) -> tuple[str, ...]:
        """Workspace member directories: `packages` for `python-lib`, `(api_dir,)`
        for a web archetype, empty otherwise — so every per-member code path
        that already exists applies to a web archetype's one member."""
        section = getattr(self.document, "archetype", None)
        if not isinstance(section, ArchetypeConfig):
            return ()
        api_dir = self.api_dir
        if api_dir is not None:
            return (api_dir,)
        return tuple(section.packages_for(self.archetype))

    def _web_section(self) -> Any:
        section = getattr(self.document, "archetype", None)
        if not isinstance(section, ArchetypeConfig):
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
    def api_dir(self) -> str | None:
        """The API member's directory, for a web archetype. `None` otherwise."""
        section = self._web_section()
        return section.api_dir if section is not None else None

    @property
    def web_dir(self) -> str | None:
        """The frontend's directory, for `python-web-app`. `None` otherwise."""
        section = self._web_section()
        return section.web_dir if isinstance(section, WebAppConfig) else None

    def to_document(self) -> dict[str, Any]:
        """The config as a TOML-ready mapping, defaults included."""
        return self.document.model_dump(by_alias=True, exclude_none=True, mode="json")
