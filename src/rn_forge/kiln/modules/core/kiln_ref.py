"""The forms `[kiln] ref` takes, and resolving a branch or tag on kiln's remote."""

from __future__ import annotations

import re
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils

from rn_forge.kiln import archetypes
from rn_forge.kiln.modules.core import process

__all__ = ["REMOTE", "SHA", "TAG", "resolve", "target", "write_pin"]

TAG = re.compile(r"^v\d+\.\d+\.\d+$")
SHA = re.compile(r"^[0-9a-f]{40}$")

REMOTE = archetypes.KILN_GIT.removeprefix("git+")
"""The URL `git ls-remote` reads. Read it as `kiln_ref.REMOTE`, never import it by name."""


def resolve(name: str) -> str:
    """Return the commit SHA of the branch or tag *name* on `REMOTE`.

    An annotated tag resolves to the commit it points at.

    Raises:
        AppException: `kiln.ref-unknown`, nothing at `REMOTE` has that name; or
            git cannot read `REMOTE`.
    """
    refs = {
        line.split("\t")[1]: line.split("\t")[0]
        for line in (
            process.run(
                "git ls-remote",
                "git",
                "ls-remote",
                REMOTE,
                f"refs/heads/{name}",
                f"refs/tags/{name}",
                f"refs/tags/{name}^{{}}",
            ).stdout
            or ""
        ).splitlines()
        if "\t" in line
    }
    for ref in (f"refs/tags/{name}^{{}}", f"refs/tags/{name}", f"refs/heads/{name}"):
        if ref in refs:
            return refs[ref]
    raise AppException(f"kiln.ref-unknown: no branch or tag {name!r} at {REMOTE}")


def target(ref: str, track: str | None) -> tuple[str, str | None]:
    """Resolve a requested ref, or follow the current tracking branch."""
    ref = ref.strip()
    if not ref:
        if not track:
            raise AppException(
                "kiln.track-missing: no [kiln] track to follow "
                "— pass a branch, tag or SHA"
            )
        ref = str(track)
    if SHA.match(ref):
        return ref, None
    if TAG.match(ref):
        resolve(ref)
        return ref, None
    return resolve(ref), ref


def write_pin(config_path: Path, ref: str, track: str | None) -> str:
    """Write the ref and tracking branch, and return the previous ref."""
    document = DocumentUtils.read_document(config_path)
    if "kiln" not in document:
        document["kiln"] = {}
    table = document["kiln"]
    old = table.get("ref", archetypes.KILN_REF)
    table["ref"] = ref
    if track is None:
        table.pop("track", None)
    else:
        table["track"] = track
    DocumentUtils.write_document(config_path, document)
    return old
