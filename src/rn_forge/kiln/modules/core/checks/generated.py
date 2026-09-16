"""`generated` — the working tree still matches the committed state baseline.

This check never renders: it checks the committed `.rn-forge/kiln/state.json`
against the bytes on disk. It cannot see whether a *newer* kiln would render
something different — that is `kiln doctor`'s job, not this one's.

Three artifact kinds, three questions:

- `managed` — the whole file is kiln's. Its SHA-256 must equal the recorded one.
- `block`   — kiln owns a fenced region inside a repo-owned file. The region
              must be present and its body's SHA-256 must equal the recorded one.
- `seeded`  — kiln wrote the file once and never touches it again. It must
              exist; its content is nobody's business here.
"""

from __future__ import annotations

import json
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.blocks import HTML_COMMENT, ManagedBlock
from rn_forge.commons.fs.hashing import ContentHash

from rn_forge.kiln.config import KilnConfig

__all__ = ["CODE", "NAME", "block_body", "check", "digest"]

NAME = "generated"
CODE = "artifact"

STATE_PATH = Path(".rn-forge/kiln/state.json")
SCHEMA_VERSION = "1"


def digest(content: str) -> str:
    """The hash kiln records for an artifact's content (a block's body, for a block)."""
    return ContentHash.of(content)


def block_body(text: str, begin_marker: str) -> str | None:
    """The body of the block *begin_marker* opens, or None if the block is absent.

    Read exactly as the generation engine reads it, so a freshly applied block
    hashes equal.

    Raises:
        AppException: The block's markers are malformed.
    """
    indent = begin_marker[: len(begin_marker) - len(begin_marker.lstrip())]
    marker = begin_marker.strip()
    if marker.startswith(HTML_COMMENT):
        name = marker.removeprefix(HTML_COMMENT).removesuffix("-->").strip()
        block = ManagedBlock(
            name.removeprefix("BEGIN").strip(), comment=HTML_COMMENT, indent=indent
        )
    else:
        name = marker.removeprefix("#").strip()
        block = ManagedBlock(name.removeprefix("BEGIN").strip(), indent=indent)
    return block.extract(text)


def _error(message: str, path: str) -> Finding:
    return Finding(f"{CODE}.drift", Severity.ERROR, message, path=path)


def _check_managed(root: Path, key: str, entry: dict[str, object]) -> list[Finding]:
    relative = str(entry["path"])
    path = root / relative
    if not path.exists():
        return [
            Finding(
                f"{CODE}.missing",
                Severity.ERROR,
                "managed artifact is missing — run `kiln apply`",
                path=relative,
            )
        ]
    actual = digest(_read(path))
    if actual != entry["content_hash"]:
        return [
            _error(
                f"managed artifact has drifted from the committed state "
                f"({actual} != {entry['content_hash']}) — run `kiln apply` or "
                f"revert the edit",
                relative,
            )
        ]
    return []


def _check_block(root: Path, key: str, entry: dict[str, object]) -> list[Finding]:
    relative = str(entry["path"])
    path = root / relative
    begin = str(entry["begin_marker"])
    if not path.exists():
        return [
            Finding(
                f"{CODE}.missing",
                Severity.ERROR,
                f"file holding managed block {key!r} is missing",
                path=relative,
            )
        ]
    try:
        body = block_body(_read(path), begin)
    except AppException as malformed:
        return [
            _error(
                f"managed block {begin!r} is malformed — {malformed.message}", relative
            )
        ]
    if body is None:
        return [
            Finding(
                f"{CODE}.missing",
                Severity.ERROR,
                f"managed block {begin!r} is missing — run `kiln apply`",
                path=relative,
            )
        ]
    actual = digest(body)
    if actual != entry["content_hash"]:
        return [
            _error(
                f"managed block {begin!r} has drifted "
                f"({actual} != {entry['content_hash']}) — run `kiln apply` or "
                f"revert the edit",
                relative,
            )
        ]
    return []


def _check_seeded(root: Path, key: str, entry: dict[str, object]) -> list[Finding]:
    relative = str(entry["path"])
    if not (root / relative).exists():
        return [
            Finding(
                f"{CODE}.seed-missing",
                Severity.ERROR,
                "seeded artifact is missing — run `kiln apply`",
                path=relative,
            )
        ]
    return []


def _read(path: Path) -> str:
    # newline="" keeps CRLF bytes as they are, which is how the engine hashes.
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


_KINDS = {"managed": _check_managed, "block": _check_block, "seeded": _check_seeded}


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Compare every recorded artifact against the tree."""
    del config  # the baseline is state.json's business, not config's
    state_path = root / STATE_PATH
    label = STATE_PATH.as_posix()

    if not state_path.exists():
        return [
            Finding(
                "state.missing",
                Severity.ERROR,
                "not found — this is not a kiln repo",
                path=label,
            )
        ]

    state = json.loads(state_path.read_text(encoding="utf-8"))
    declared = state.get("schema_version")
    if declared != SCHEMA_VERSION:
        return [
            Finding(
                "state.schema-version",
                Severity.ERROR,
                f"schema_version is {declared!r}, and this kiln understands "
                f"{SCHEMA_VERSION} — upgrade kiln and re-run `kiln apply`",
                path=label,
            )
        ]

    findings: list[Finding] = []
    for key, entry in sorted(state.get("entries", {}).items()):
        kind = entry.get("kind")
        if kind not in _KINDS:
            findings.append(
                Finding(
                    "state.unknown-kind",
                    Severity.ERROR,
                    f"entry {key!r} has unknown kind {kind!r}",
                    path=label,
                )
            )
            continue
        if Path(str(entry["path"])) == STATE_PATH:
            findings.append(
                Finding(
                    "state.self-hash",
                    Severity.ERROR,
                    f"state must not hash itself (entry {key!r})",
                    path=label,
                )
            )
            continue
        findings.extend(_KINDS[kind](root, key, entry))
    return findings
