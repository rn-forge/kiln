"""`rn-forge-deps` — the archetype's rn-forge dependency contract.

Three rules, all read from `pyproject.toml`:

1. **Required.** Every distribution in the archetype's required set is a
   runtime dependency of at least one distributable in this repo.
2. **Allowed.** No `rn-forge-*` distribution outside the allowed set appears
   anywhere — dependencies, optional dependencies or dependency groups.
3. **Pinned, and in the published metadata.** Every rn-forge requirement is a
   PEP 508 direct URL naming a tag or a rev, not a `[tool.uv.sources]` entry
   (a local override that does not survive into a built wheel).

`rn-forge-kiln` is outside all three: it is the dev tool that runs this
check, not a library the repo is built on, and its own pin is a separate
`doctor` rule.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln import archetypes, documents
from rn_forge.kiln.archetypes import RN_FORGE_PREFIX
from rn_forge.kiln.config import KilnConfig

__all__ = ["CODE", "NAME", "check"]

NAME = "rn-forge-deps"
CODE = "deps"

# A PEP 508 requirement's distribution name: everything before the first extra,
# specifier, marker or whitespace. `rn-forge-django[codegen]>=0.2` → `rn-forge-django`.
REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
# A git URL carrying a ref: `git+https://host/org/repo@<ref>`, with the ref
# ending at the `#subdirectory=` fragment if there is one.
PINNED_GIT_URL = re.compile(r"^git\+[^@\s]+@[^#\s]+")
# A requirement naming a `[codegen]` extra, among possibly other extras.
CODEGEN_EXTRA = re.compile(r"^\s*[A-Za-z0-9][A-Za-z0-9._-]*\[[^\]]*\bcodegen\b[^\]]*\]")

KILN = "rn-forge-kiln"
"""The generator itself: a dev dependency the contract does not govern."""


def distribution(requirement: str) -> str:
    """The normalized distribution name a PEP 508 requirement names."""
    match = REQUIREMENT_NAME.match(requirement)
    return match.group(1).lower().replace("_", "-") if match else ""


def governed(name: str) -> bool:
    """Whether the contract applies to distribution *name*."""
    name = name.lower()
    return name.startswith(RN_FORGE_PREFIX) and name != KILN


def runtime_dependencies(document: dict[str, object]) -> list[str]:
    """`[project] dependencies` — what a consumer of this package would install."""
    return documents.strings(documents.table(document, "project").get("dependencies"))


def every_dependency(document: dict[str, object]) -> list[str]:
    """Runtime, optional and dependency-group requirements, flattened.

    A dependency group is still a dependency: a kit that a repo installs only
    to develop with is exactly the coupling kiln ADR-0002 is about.
    """
    found = list(runtime_dependencies(document))
    optional = documents.table(document, "project", "optional-dependencies")
    groups = documents.table(document, "dependency-groups")
    for group in (*optional.values(), *groups.values()):
        found.extend(documents.strings(group))
    return found


def _check_allowed(
    label: str, document: dict[str, object], allowed: tuple[str, ...]
) -> list[Finding]:
    permitted = {name.lower() for name in allowed}
    return [
        Finding(
            f"{CODE}.not-allowed",
            Severity.ERROR,
            f"depends on `{distribution(requirement)}`, which is not in this "
            f"archetype's allowed set {sorted(permitted)} — an rn-forge kit is "
            f"a subprocess, never a dependency",
            path=label,
        )
        for requirement in every_dependency(document)
        if governed(distribution(requirement))
        and distribution(requirement) not in permitted
    ]


def _check_direct_url(label: str, document: dict[str, object]) -> list[Finding]:
    """Every rn-forge requirement carries its own pinned source."""
    findings: list[Finding] = []
    for requirement in every_dependency(document):
        name = distribution(requirement)
        if not governed(name):
            continue
        url = requirement.partition(" @ ")[2].strip()
        if not url:
            findings.append(
                Finding(
                    f"{CODE}.not-direct",
                    Severity.ERROR,
                    f"`{name}` is declared without a direct URL — a "
                    f"[tool.uv.sources] override does not survive into a built "
                    f"wheel, so a consumer of this package could not resolve it",
                    path=label,
                )
            )
            continue
        if not PINNED_GIT_URL.match(url):
            findings.append(
                Finding(
                    f"{CODE}.unpinned",
                    Severity.ERROR,
                    f"`{name}` resolves to {url!r}, which names no tag or rev — "
                    f"pin it, or the build changes without the repo changing",
                    path=label,
                )
            )
    return findings


def _check_no_codegen_in_runtime(
    label: str, document: dict[str, object]
) -> list[Finding]:
    """A framework's `[codegen]` extra is a dev-only entry-point group, never a
    runtime dependency: kiln discovers generators in the environment it runs
    in, never the one the application ships (kiln ADR-0005)."""
    return [
        Finding(
            f"{CODE}.codegen-runtime",
            Severity.ERROR,
            f"`{distribution(requirement)}` declares its [codegen] extra in "
            f"[project] dependencies — move it to a dependency group",
            path=label,
        )
        for requirement in runtime_dependencies(document)
        if governed(distribution(requirement)) and CODEGEN_EXTRA.match(requirement)
    ]


def _check_no_shadowing_source(
    label: str, document: dict[str, object]
) -> list[Finding]:
    """A [tool.uv.sources] entry for an rn-forge package hides the real one.

    It would resolve locally and silently disagree with what the wheel says,
    which is the failure this whole rule exists to prevent.
    """
    return [
        Finding(
            f"{CODE}.shadowing-source",
            Severity.ERROR,
            f"[tool.uv.sources.{name}] overrides an rn-forge dependency — "
            f"remove it and pin the URL in `dependencies` instead",
            path=label,
        )
        for name in documents.table(document, "tool", "uv", "sources")
        if governed(name)
    ]


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Hold every `pyproject.toml` in the repo to the archetype's contract."""
    archetype = archetypes.for_config(config)

    findings: list[Finding] = []
    declared: set[str] = set()

    for relative in archetypes.pyproject_paths(config):
        label = relative.as_posix()
        path = root / relative
        if not path.exists():
            findings.append(
                Finding(
                    f"{CODE}.pyproject-missing",
                    Severity.ERROR,
                    "not found — the archetype expects it",
                    path=label,
                )
            )
            continue
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        findings.extend(
            _check_allowed(label, document, tuple(archetype.dependencies.allowed))
        )
        findings.extend(_check_direct_url(label, document))
        findings.extend(_check_no_shadowing_source(label, document))
        findings.extend(_check_no_codegen_in_runtime(label, document))
        declared.update(distribution(r) for r in runtime_dependencies(document))

    findings.extend(
        Finding(
            f"{CODE}.required-missing",
            Severity.ERROR,
            f"this archetype requires a dependency on `{name}`, and no "
            f"distributable in this repo declares one",
            path="pyproject.toml",
        )
        for name in archetype.dependencies.required
        if name.lower() not in declared
    )
    return findings
