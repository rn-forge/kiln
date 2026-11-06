"""Job lookup over a rendered `ci.yml` and its reusable `_*.yml` workflows."""

from __future__ import annotations

import copy
import re
from typing import Any

from rn_forge.commons.fs.documents import YamlUtils

_WORKFLOWS = ".github/workflows"
_LOCAL = "./.github/workflows/"
_INPUT = re.compile(r"(?<![\w.])inputs\.([\w-]+)")
_EXPRESSION = re.compile(r"^\$\{\{\s*(.*?)\s*\}\}$", re.DOTALL)
_CALLER_KEYS = ("uses", "with", "secrets")


def _bare(value: object) -> str:
    """A `with:` value as an expression body: `${{ x }}` becomes `x`."""
    text = str(value)
    match = _EXPRESSION.match(text)
    if match is None:
        return text
    body = match.group(1)
    return body if re.fullmatch(r"[\w.\-()\[\]*']+", body) else f"({body})"


def _fill(node: Any, values: dict[str, str]) -> Any:
    """Replace `inputs.<name>` by the caller's expression throughout `node`."""
    if isinstance(node, str):
        return _INPUT.sub(
            lambda m: values.get(m.group(1), m.group(0)),
            node,
        )
    if isinstance(node, list):
        return [_fill(item, values) for item in node]
    if isinstance(node, dict):
        return {key: _fill(item, values) for key, item in node.items()}
    return node


def _resolve(caller: dict[str, Any], files: dict[str, str]) -> dict[str, Any] | None:
    """The called job's body with the caller's `needs`, `if` and `permissions` laid over it."""
    uses = str(caller.get("uses", ""))
    if not uses.startswith(f"{_LOCAL}_"):
        return None
    path = f"{_WORKFLOWS}/{uses.removeprefix(_LOCAL)}"
    if path not in files:
        return None
    called = YamlUtils.load(files[path]).get("jobs") or {}
    (body,) = called.values()
    values = {
        k: _bare(v)
        for k, v in (caller.get("with") or {}).items()
        if not re.search(rf"(?<![\w.])inputs\.{re.escape(k)}(?![\w-])", str(v))
    }
    merged = _fill(copy.deepcopy(body), values)
    merged.update({k: v for k, v in caller.items() if k not in _CALLER_KEYS})
    return merged


def jobs(files: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Return the jobs of `ci.yml`, a caller of a rendered `_<stage>.yml` replaced by the job it calls.

    Args:
        files: The rendered file map, path to content.

    Returns:
        Job name to job body, in `ci.yml`'s order. A resolved job has the called
        job's body, its `inputs.<name>` read as the caller's `with:` expression
        (an input the caller passes through from its own `inputs.<name>` is left
        as it is),
        and the caller's own keys (`needs`, `if`, `permissions`) over it.
    """
    path = f"{_WORKFLOWS}/ci.yml"
    resolved: dict[str, dict[str, Any]] = {}
    for name, body in (YamlUtils.load(files[path]).get("jobs") or {}).items():
        resolved[name] = _resolve(body, files) or body
    return resolved
