"""The option catalog: every `config.toml` key, described, from the models.

`for_archetype` walks the model an archetype's config is validated against and
returns one `OptionSpec` per key. `render` writes a config as TOML with each
key's description above it.
"""

from __future__ import annotations

import re
import types
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Union, cast, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import to_jsonable_python
from rn_forge.commons.fs.documents import ConfigFormat, DocumentUtils
from rn_forge.commons.lang.types import JsonValue

from rn_forge.kiln import archetypes
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.config.schema import compose
from rn_forge.kiln.modules.registry import builtin

__all__ = ["OptionSpec", "for_archetype", "render"]

_UNTYPED = ("cli", "lifecycle")
_DEFAULT_SENTENCE = re.compile(r"(?:^|(?<=\s))Default:\s*(.*)\Z", re.DOTALL)
_KEY_LINE = re.compile(r'^([A-Za-z0-9_-]+|"[^"]*")\s*=')
_HEADER = re.compile(r"^(\[\[?)\s*(.*?)\s*\]\]?\s*$")


@dataclass(frozen=True, slots=True)
class OptionSpec:
    """One `config.toml` key, as the schema describes it."""

    path: str
    """The dotted key; a list of tables' keys are `<list>[].<key>`."""
    module: str
    """The owning module's name; `core` for root keys."""
    description: str
    """What the key means and what `kiln apply` changes when it changes."""
    choices: tuple[str, ...] | None = None
    """The allowed values of a `Literal`, else None."""
    default: JsonValue | None = None
    """The default as a JSON value; None when absent or resolved elsewhere."""
    default_note: str | None = None
    """For a `None` default, how it is resolved elsewhere."""


def for_archetype(name: str) -> tuple[OptionSpec, ...]:
    """Every option an *name* archetype's `config.toml` takes, in file order."""
    modules = builtin().for_archetype(archetypes.load(name))
    owners = {
        module.section: module.name for module in modules if module.section is not None
    }
    specs: list[OptionSpec] = []
    _walk(compose(modules), "", "core", owners, name, specs)
    return tuple(specs)


def render(config: KilnConfig, *, header: str) -> str:
    """*config* as TOML text: *header*, then each key under its description.

    `ci.release` and the archetype's `module`, when unset, are written
    commented out with the value they resolve to, so they keep following their
    default.
    """
    resolved: dict[str, Callable[[], str]] = {
        "ci.release": lambda: config.release,
        f"archetype.{config.archetype}.module": lambda: config.module,
    }
    commented: set[str] = set()
    document = _prune(
        config.document.model_dump(by_alias=True, mode="json"),
        "",
        resolved,
        commented,
    )
    body = DocumentUtils.dumps(document, ConfigFormat.TOML, multiline_arrays=True)
    index = {spec.path: spec for spec in for_archetype(config.archetype)}
    head = DocumentUtils.dumps({}, ConfigFormat.TOML, header=header)
    return f"{head}\n{_annotate(body, index, commented)}"


def _walk(
    model: type[BaseModel],
    prefix: str,
    module: str,
    owners: Mapping[str, str],
    archetype: str,
    specs: list[OptionSpec],
) -> None:
    for field_name, field in model.model_fields.items():
        key = field.alias or field_name
        if prefix == "archetype." and key != archetype:
            continue
        path = prefix + key
        owner = owners.get(key, module) if not prefix else module
        inner = _unwrap(field.annotation)
        item = _list_item(inner)
        table = item if item is not None else inner
        if key in _UNTYPED and not prefix:
            specs.append(_spec(path, owner, field, None))
            continue
        if isinstance(table, type) and issubclass(table, BaseModel):
            specs.append(_spec(path, owner, field, table))
            _walk(
                table,
                path + ("[]." if item is not None else "."),
                owner,
                owners,
                archetype,
                specs,
            )
        else:
            specs.append(_spec(path, owner, field, None))


def _spec(
    path: str, module: str, field: FieldInfo, table: type[BaseModel] | None
) -> OptionSpec:
    text = field.description or (table.__doc__ or "" if table else "")
    text = text.strip()
    note: str | None = None
    if found := _DEFAULT_SENTENCE.search(text):
        note = " ".join(found.group(1).split()).rstrip(".")
        text = text[: found.start()].rstrip()
    return OptionSpec(
        path=path,
        module=module,
        description=text,
        choices=_choices(field.annotation),
        default=_default(field) if table is None else None,
        default_note=note,
    )


def _unwrap(annotation: Any) -> Any:
    """*annotation* without `Annotated` and without `None` in a union."""
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    if get_origin(annotation) in (Union, types.UnionType):
        rest = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(rest) == 1:
            return _unwrap(rest[0])
    return annotation


def _list_item(annotation: Any) -> type[BaseModel] | None:
    if get_origin(annotation) is not list:
        return None
    item = _unwrap(get_args(annotation)[0])
    return item if isinstance(item, type) and issubclass(item, BaseModel) else None


def _choices(annotation: Any) -> tuple[str, ...] | None:
    inner = _unwrap(annotation)
    if get_origin(inner) is list:
        inner = _unwrap(get_args(inner)[0])
    if get_origin(inner) is Literal:
        return tuple(str(arg) for arg in get_args(inner))
    return None


def _default(field: FieldInfo) -> JsonValue | None:
    if field.is_required():
        return None
    value = field.get_default(call_default_factory=True)
    if isinstance(value, BaseModel):
        return None
    return to_jsonable_python(value)


def _prune(
    value: Any,
    path: str,
    resolved: Mapping[str, Callable[[], str]],
    commented: set[str],
) -> Any:
    """*value* without its `None` keys, except those *resolved* fills in."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in cast(dict[str, Any], value).items():
            child_path = f"{path}.{key}" if path else key
            if child is None:
                if child_path in resolved:
                    out[key] = resolved[child_path]()
                    commented.add(child_path)
                continue
            out[key] = _prune(child, child_path, resolved, commented)
        return out
    if isinstance(value, list):
        return [
            _prune(item, f"{path}[]", resolved, commented)
            for item in cast(list[Any], value)
        ]
    return value


def _annotate(body: str, index: Mapping[str, OptionSpec], commented: set[str]) -> str:
    """Put each key's description above it in the TOML *body*."""
    lines: list[str] = []
    table = ""
    in_list = False
    seen: set[str] = set()
    for line in body.splitlines():
        header = _HEADER.match(line)
        if header:
            table = _dotted(header.group(2))
            in_list = header.group(1) == "[["
            first = table not in seen
            seen.add(table)
            spec = index.get(table)
            if spec is not None and first:
                lines.extend(_comment(spec))
            lines.append(line)
            continue
        key = _KEY_LINE.match(line)
        if key is None:
            lines.append(line)
            continue
        path = _join(table, key.group(1).strip('"'), in_list=in_list)
        spec = index.get(path)
        if spec is not None:
            if lines and lines[-1] and not lines[-1].startswith("["):
                lines.append("")
            lines.extend(_comment(spec))
        lines.append(f"# {line}" if path in commented else line)
    return "\n".join(lines) + "\n"


def _join(table: str, key: str, *, in_list: bool) -> str:
    if not table:
        return key
    return f"{table}[].{key}" if in_list else f"{table}.{key}"


def _dotted(header: str) -> str:
    return ".".join(part.strip().strip('"') for part in header.split("."))


def _comment(spec: OptionSpec) -> list[str]:
    lines = spec.description.splitlines()
    if spec.choices:
        lines.append(
            "One of: " + ", ".join(f'"{choice}"' for choice in spec.choices) + "."
        )
    if spec.default is not None:
        lines.append(f"Default: {_literal(spec.default)}.")
    elif spec.default_note:
        lines.append(f"Default: {spec.default_note}.")
    return [f"# {line}" if line else "#" for line in lines]


def _literal(value: JsonValue) -> str:
    """*value* as TOML source."""
    if isinstance(value, dict):
        return "{}" if not value else str(value)
    text = DocumentUtils.dumps({"x": value}, ConfigFormat.TOML)
    return text.removeprefix("x = ").strip()
