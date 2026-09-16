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
from rn_forge.kiln.modules.python.config import ArchetypeConfig

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
        """Workspace member directories, for a `python-lib`. Empty otherwise."""
        section = getattr(self.document, "archetype", None)
        if not isinstance(section, ArchetypeConfig):
            return ()
        return tuple(section.packages_for(self.archetype))

    def to_document(self) -> dict[str, Any]:
        """The config as a TOML-ready mapping, defaults included."""
        return self.document.model_dump(by_alias=True, exclude_none=True, mode="json")
