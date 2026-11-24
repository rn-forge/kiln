"""Models for the documentation areas declared in `docs/_areas.yml`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, cast

from pydantic import Field, model_validator
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.commons.lang.models import StrictModel

__all__ = ["Area", "AreasManifest", "load_areas"]


class Area(StrictModel):
    """One declared documentation area.

    Args:
        key: The directory name under `docs/`.
        title: The nav heading for the area; `key.title()` when absent.
        nav: ``"children"`` to list the area's pages, ``"index-only"`` to show
            only its `index.md`. ``"include"`` declares an area that is not a
            directory under `docs/`, and its nav is one `!include` entry per
            package. ``"work"`` lists the area's index, its epic list, its
            epics in ranges of ten with each epic's pages beneath it, and then
            the area's other pages.
        optional: The area may be absent without that being a finding.
        generated: The area's contents are produced by a generator (API
            reference output) — never checked, and only navigated if present.
    """

    key: str
    title: str
    nav: Literal["children", "index-only", "include", "work"] = "children"
    optional: bool = False
    generated: bool = False

    @model_validator(mode="before")
    @classmethod
    def _default_title(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        values = cast(dict[str, Any], data)
        key = values.get("key")
        if isinstance(key, str):
            return {"title": key.title(), **values}
        return values


class AreasManifest(StrictModel):
    """The shape of `docs/_areas.yml`."""

    version: int = 1
    areas: list[Area] = Field(default_factory=list[Area])


def load_areas(docs_root: str | Path) -> list[Area]:
    """Load `docs/_areas.yml`.

    Raises:
        AppException: The manifest is absent, is not a mapping, or declares an
            area that does not match :class:`Area`.
    """
    manifest = Path(docs_root) / "_areas.yml"
    if not manifest.is_file():
        raise AppException("{} does not exist", manifest)

    raw: Any = YamlUtils.read_file(manifest)
    if not isinstance(raw, dict):
        raise AppException("{}: expected a mapping at the top level", manifest)
    document = cast(dict[str, Any], raw)
    return AreasManifest.parse(document, source=str(manifest)).areas
