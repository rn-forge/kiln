"""`ci-pins` — every action is pinned to a commit, and every job states its permissions.

Two rules, over every `*.yml` under `.github/workflows/` and `.github/actions/`:

1. A `uses:` names a 40-hex-character commit SHA after `@`, with the version in
   a trailing `# <version>` comment. A local action (`uses: ./…`) is exempt.
2. Every job under `jobs:` carries a `permissions:` key.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln import documents
from rn_forge.kiln.config import KilnConfig

__all__ = ["NAME", "check"]

NAME = "ci-pins"
UNPINNED = "ci.unpinned"
PERMISSIONS = "ci.permissions"

_DIRS = (Path(".github/workflows"), Path(".github/actions"))
_USES = re.compile(r"^\s*(?:- )?uses:\s*(\S+)(.*)$")
_PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
_VERSION_COMMENT = re.compile(r"^\s+#\s*\S+")


def _check_uses(label: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = _USES.match(line)
        if not match:
            continue
        ref, rest = match.groups()
        ref = ref.strip("\"'")
        if ref.startswith("./"):
            continue
        if not _PINNED.match(ref) or not _VERSION_COMMENT.match(rest):
            findings.append(
                Finding(
                    UNPINNED,
                    Severity.ERROR,
                    f"`uses: {ref}` is not pinned to a commit SHA with a `# <version>` comment",
                    path=label,
                    line=lineno,
                )
            )
    return findings


def _check_permissions(label: str, text: str) -> list[Finding]:
    jobs = documents.table(yaml.safe_load(text), "jobs")
    return [
        Finding(
            PERMISSIONS,
            Severity.ERROR,
            f"job `{name}` has no `permissions:` key",
            path=label,
        )
        for name, spec in jobs.items()
        if "permissions" not in documents.mapping(spec)
    ]


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Scan every workflow and action for an unpinned `uses:` or a job without permissions."""
    del config
    findings: list[Finding] = []
    for directory in _DIRS:
        if not (root / directory).is_dir():
            continue
        for path in sorted((root / directory).rglob("*.yml")):
            label = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8")
            findings.extend(_check_uses(label, text))
            findings.extend(_check_permissions(label, text))
    return findings
