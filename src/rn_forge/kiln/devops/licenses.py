"""The licence policy: which dependencies a deny list rejects."""

from __future__ import annotations

import fnmatch
import json
import re
from typing import Any

DEFAULT_DENY = ["GPL", "GPL-*", "AGPL", "AGPL-*", "UNKNOWN"]

_CLASSIFIERS = {
    "GNU General Public License (GPL)": "GPL",
    "GNU General Public License v2 (GPLv2)": "GPL-2.0",
    "GNU General Public License v2 or later (GPLv2+)": "GPL-2.0-or-later",
    "GNU General Public License v3 (GPLv3)": "GPL-3.0",
    "GNU General Public License v3 or later (GPLv3+)": "GPL-3.0-or-later",
    "GNU Affero General Public License v3": "AGPL-3.0",
    "GNU Affero General Public License v3 or later (AGPLv3+)": "AGPL-3.0-or-later",
    "GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0",
    "GNU Library or Lesser General Public License (LGPL)": "LGPL",
}
_BY_CLASSIFIER = {k.casefold(): v for k, v in _CLASSIFIERS.items()}
_SHORT = re.compile(r"^(A|L)?GPL[ -]?v?(\d)(\.0)?(\+| or later)?$", re.IGNORECASE)


def normalise(value: str) -> str:
    """Return the SPDX-style identifier for a producer's licence value.

    Args:
        value: One licence as the producer wrote it.

    Returns:
        The identifier, or `value` unchanged when it cannot be normalised.
    """
    text = value.strip()
    if text.casefold() in ("", "unknown"):
        return "UNKNOWN"
    known = _BY_CLASSIFIER.get(text.casefold())
    if known:
        return known
    match = _SHORT.match(text)
    if match:
        family = (match.group(1) or "").upper()
        later = "-or-later" if match.group(4) else ""
        return f"{family}GPL-{match.group(2)}.0{later}"
    return text


def _denied(licence: str, deny: list[str]) -> bool:
    patterns = [d.casefold() for d in deny]
    for part in licence.split(";"):
        identifier = normalise(part).casefold()
        if any(fnmatch.fnmatchcase(identifier, p) for p in patterns):
            return True
    return False


def _packages(data: Any, fmt: str) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    if fmt == "pip-licenses":
        for row in data:
            found.append((row["Name"], row["Version"], row["License"]))
    else:
        for licence, packages in data.items():
            for package in packages:
                for version in package["versions"]:
                    found.append((package["name"], version, licence))
    return found


def run(text: str, fmt: str, deny: list[str], ignore: list[str]) -> list[str]:
    """Return one `<name> <version> <licence>` line per denied package.

    Args:
        text: The producer's JSON output.
        fmt: `pip-licenses` or `pnpm`.
        deny: Patterns matched against each normalised licence.
        ignore: Package names that are never offenders.

    Raises:
        ValueError: The text is not the producer's JSON.
    """
    try:
        packages = _packages(json.loads(text), fmt)
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as error:
        raise ValueError(f"not {fmt} JSON: {error}") from error
    return [
        f"{name} {version} {licence}"
        for name, version, licence in packages
        if name not in ignore and _denied(licence, deny)
    ]
