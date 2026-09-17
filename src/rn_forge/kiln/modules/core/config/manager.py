"""Loading, validating and resolving `config.toml`.

`load` reads only the committed file. `resolve` builds a config from layers —
kiln's defaults, then a source, then flags — and `reresolve` rebuilds a
committed one from its recorded source, keeping every repo override.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.lang.collections import DictUtils
from rn_forge.commons.lang.types import JsonValue

from rn_forge.kiln import archetypes, documents
from rn_forge.kiln.config import CONFIG_PATH, KilnConfig
from rn_forge.kiln.modules.base import KilnModule, ModuleRegistry
from rn_forge.kiln.modules.core.config.schema import (
    SCHEMA_VERSION,
    RepositoryConfig,
    SourceConfig,
    compose,
)
from rn_forge.kiln.modules.core.config.sources import Fetched, Source, fetch
from rn_forge.kiln.modules.registry import builtin

__all__ = [
    "DEFAULTS_LAYER",
    "FLAGS_LAYER",
    "PROVENANCE_KEY",
    "REPO_LAYER",
    "SOURCE_LAYER",
    "ConfigManager",
    "Provenance",
    "Resolution",
]

DEFAULTS_LAYER = "defaults"
SOURCE_LAYER = "source"
FLAGS_LAYER = "flags"
REPO_LAYER = "repo"
"""The layer a repo override is attributed to."""

PROVENANCE_KEY = "config_provenance"
"""The `state.json` metadata key per-key provenance is recorded under."""

_STATE_PATH = Path(".rn-forge/kiln/state.json")
_UNLAYERED = ("schema_version", "source")


@dataclass(frozen=True, slots=True)
class Provenance:
    """Which layer last supplied a config key, and the value it supplied."""

    layer: str
    value: JsonValue


@dataclass(frozen=True, slots=True)
class Resolution:
    """A resolved config, where each key came from, and what the repo overrode."""

    config: KilnConfig
    provenance: dict[str, Provenance]
    """Every leaf key, by dotted path."""
    overrides: tuple[str, ...] = ()
    """Dotted paths whose committed value was kept over a layer's."""

    def provenance_metadata(self) -> dict[str, JsonValue]:
        """:attr:`provenance`, in the shape `state.json` records it."""
        return {
            path: {"layer": entry.layer, "value": entry.value}
            for path, entry in sorted(self.provenance.items())
        }


class ConfigManager:
    """Loads and resolves configs against the modules *registry* holds."""

    def __init__(self, registry: ModuleRegistry | None = None) -> None:
        self._registry = registry or builtin()

    def modules_for(self, config: KilnConfig) -> tuple[KilnModule, ...]:
        """The modules *config*'s archetype enables, in apply order."""
        return self._registry.for_archetype(archetypes.load(config.archetype))

    def load(self, root: Path) -> KilnConfig:
        """Read and validate *root*'s committed config.

        Raises:
            AppException: The file is missing or unparseable, or fails
                :meth:`validate`.
        """
        label = CONFIG_PATH.as_posix()
        return self.validate(_read_config(root), source=label)

    def validate(self, document: Mapping[str, Any], *, source: str) -> KilnConfig:
        """Validate *document* against this kiln's schema for its archetype.

        Raises:
            AppException: *document* declares a schema version other than this
                kiln's, names an unknown archetype, carries a section for a
                module its archetype does not enable, or fails the schema —
                in which case every failing key is named by its dotted path.
        """
        declared = document.get("schema_version")
        if isinstance(declared, int) and declared != SCHEMA_VERSION:
            if declared > SCHEMA_VERSION:
                raise AppException(
                    "{}: schema_version {} needs a newer kiln — this kiln "
                    "understands schema_version {}; upgrade kiln",
                    source,
                    declared,
                    SCHEMA_VERSION,
                )
            raise AppException(
                "{}: schema_version is {}, and this kiln understands {} — "
                "run `kiln config upgrade`",
                source,
                declared,
                SCHEMA_VERSION,
            )

        name = DictUtils.get(dict(document), "repository.archetype")
        if not isinstance(name, str):
            # No archetype to compose for; every module's section is allowed so
            # the report names what is actually wrong.
            compose(self._registry.modules).parse(document, source=source)
            raise AppException("{}: [repository] declares no archetype", source)

        archetype = archetypes.load(name)
        enabled = self._registry.for_archetype(archetype)
        disabled = [
            module
            for module in self._registry.modules
            if module not in enabled and module.section in document
        ]
        if disabled:
            raise AppException(
                "{}: {}",
                source,
                "; ".join(
                    f"[{module.section}] belongs to module {module.name!r}, "
                    f"which archetype {name!r} does not enable"
                    for module in disabled
                ),
            )
        foreign = [key for key in documents.table(document, "archetype") if key != name]
        if foreign:
            raise AppException(
                "{}: [archetype.{}] belongs to a different archetype than {!r}",
                source,
                foreign[0],
                name,
            )
        return KilnConfig(compose(enabled).parse(document, source=source))

    def resolve(
        self,
        *,
        flags: Mapping[str, Any],
        source: Source | None = None,
        base: Path | None = None,
    ) -> Resolution:
        """Resolve a new config: kiln's defaults, then *source*, then *flags*.

        Args:
            flags: Values given on the command line, as a nested mapping.
            source: The layer to resolve from, if any.
            base: What a relative source path resolves against; the working
                directory by default.

        Raises:
            AppException: The source cannot be read, or the result is invalid.
        """
        layers: list[tuple[str, Mapping[str, Any]]] = []
        fetched = fetch(source, base or Path.cwd()) if source else None
        if fetched:
            layers.append((SOURCE_LAYER, fetched.document))
        layers.append((FLAGS_LAYER, flags))
        return self._merge(layers, fetched)

    def reresolve(self, root: Path) -> Resolution:
        """Re-resolve *root*'s committed config from its recorded source.

        Values given as flags when the config was created are kept. A key whose
        committed value differs from what its layer last supplied — or that no
        layer supplied — is a repo override: its committed value wins, and it
        is listed in :attr:`Resolution.overrides`.

        Raises:
            AppException: The committed config is invalid, or its source cannot
                be read.
        """
        committed = _read_config(root)
        self.validate(committed, source=CONFIG_PATH.as_posix())
        recorded = _recorded_provenance(root)

        layers: list[tuple[str, Mapping[str, Any]]] = []
        fetched: Fetched | None = None
        if "source" in committed:
            record = SourceConfig.parse(committed["source"], source="[source]")
            fetched = fetch(Source(record.location, record.ref), root)
            layers.append((SOURCE_LAYER, fetched.document))

        flags: dict[str, Any] = {}
        for path, entry in recorded.items():
            if entry.layer == FLAGS_LAYER:
                DictUtils.set(flags, path, entry.value)
        layers.append((FLAGS_LAYER, flags))

        body = {k: v for k, v in committed.items() if k not in _UNLAYERED}
        overrides: dict[str, Any] = {}
        names: list[str] = []
        for path, value in DictUtils.flatten(body).items():
            was = recorded.get(path)
            if was is None or was.layer == REPO_LAYER or was.value != value:
                DictUtils.set(overrides, path, value)
                names.append(path)
        layers.append((REPO_LAYER, overrides))
        return self._merge(layers, fetched, tuple(names))

    def _merge(
        self,
        layers: Sequence[tuple[str, Mapping[str, Any]]],
        fetched: Fetched | None,
        overrides: tuple[str, ...] = (),
    ) -> Resolution:
        merged = DictUtils.merge_layers(
            (DEFAULTS_LAYER, self._defaults(layers)), *layers
        )
        document = merged.config
        if fetched:
            document["source"] = fetched.record.model_dump(exclude_none=True)
        config = self.validate(document, source="the resolved config")
        provenance = {
            path: Provenance(merged.provenance[path], cast(JsonValue, value))
            for path, value in DictUtils.flatten(document).items()
            if path in merged.provenance
        }
        return Resolution(config, provenance, overrides)

    def _defaults(
        self, layers: Sequence[tuple[str, Mapping[str, Any]]]
    ) -> dict[str, Any]:
        """kiln's layer: the schema version and every enabled section's defaults."""
        defaults: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "repository": {
                name: field.default
                for name, field in RepositoryConfig.model_fields.items()
                if not field.is_required()
            },
        }
        names = [
            DictUtils.get(dict(layer), "repository.archetype") for _, layer in layers
        ]
        name = next((n for n in reversed(names) if isinstance(n, str)), None)
        if name not in archetypes.shipped():
            return defaults  # validation reports the archetype
        for module in self._registry.for_archetype(archetypes.load(name)):
            if module.section is not None and module.config_model is not None:
                defaults[module.section] = module.config_model().model_dump(
                    by_alias=True, exclude_none=True, mode="json"
                )
        if name in {"python-web-api", "python-web-app"}:
            from rn_forge.kiln.modules.python.config import WebApiConfig, WebAppConfig

            model = WebApiConfig if name == "python-web-api" else WebAppConfig
            defaults["archetype"] = {
                name: model().model_dump(by_alias=True, exclude_none=True, mode="json")
            }
        return defaults


def _read_config(root: Path) -> dict[str, Any]:
    path = root / CONFIG_PATH
    label = CONFIG_PATH.as_posix()
    if not path.exists():
        raise AppException("{}: not found — this is not a kiln repo", label)
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as invalid:
        raise AppException("{}: is not valid TOML — {}", label, invalid) from invalid


def _recorded_provenance(root: Path) -> dict[str, Provenance]:
    path = root / _STATE_PATH
    if not path.is_file():
        return {}
    state = json.loads(path.read_text(encoding="utf-8"))
    recorded = documents.table(state, "metadata", PROVENANCE_KEY)
    return {
        key: Provenance(str(entry.get("layer")), cast(JsonValue, entry.get("value")))
        for key, entry in ((k, documents.mapping(v)) for k, v in recorded.items())
    }
