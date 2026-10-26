"""`rn-forge-deps` — the archetype's rn-forge dependency contract.

Three rules, all read from `pyproject.toml`:

1. **Required.** Every distribution in the archetype's required set is a
   runtime dependency of at least one distributable in this repo.
2. **Allowed.** No `rn-forge-*` distribution outside the allowed set appears
   anywhere — dependencies, optional dependencies or dependency groups. A
   workspace member of this repo is exempt: it is this repo's own package, not
   an external kit.
3. **Pinned or ranged, and in the published metadata.** Every rn-forge
   requirement is a PEP 508 direct URL naming a tag or a rev, or a version range
   with a ceiling resolved from pykit's index, which the root then declares. It
   is never a `[tool.uv.sources]` entry (a local override that does not survive
   into a built wheel). A workspace member may carry a `{ workspace = true }`
   source and may be named bare in a dependency group, which never reaches a
   wheel; in `dependencies` it still needs the URL or a range, and a range on a
   member needs no index.

A fourth rule keeps kiln out of the lock: `rn-forge-kiln` in any dependency,
optional dependency or dependency group is an error, because kiln runs from
`[kiln] ref` in its own environment (F7.4). The root project's own
`[project] name` is not a dependency, so kiln's own repository passes.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.lang.collections import DictUtils, ListUtils

from rn_forge.kiln import archetypes
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

# The version specifier after a requirement's name and extras, up to a marker.
# `rn-forge-web[auth]>=0.2.1,<0.3; python_version>"3"` → `>=0.2.1,<0.3`.
SPECIFIER = re.compile(r"^\s*[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[^\]]*\])?\s*([^;@]*)")

KILN = "rn-forge-kiln"
"""The generator itself: never a dependency of the repo it runs beside."""


def distribution(requirement: str) -> str:
    """The normalized distribution name a PEP 508 requirement names."""
    match = REQUIREMENT_NAME.match(requirement)
    return match.group(1).lower().replace("_", "-") if match else ""


def _specifier(requirement: str) -> str:
    """The version specifier a requirement carries, or "" when it has none."""
    match = SPECIFIER.match(requirement)
    return match.group(1).strip() if match else ""


def _has_ceiling(specifier: str) -> bool:
    """Whether a clause of *specifier* caps the version: `<...` or `==...`."""
    return any(
        clause.strip().startswith(("<", "==")) for clause in specifier.split(",")
    )


def governed(name: str) -> bool:
    """Whether the contract applies to distribution *name*."""
    name = name.lower()
    return name.startswith(RN_FORGE_PREFIX) and name != KILN


def runtime_dependencies(document: dict[str, object]) -> list[str]:
    """`[project] dependencies` — what a consumer of this package would install."""
    return DictUtils.get_strings(document, "project.dependencies")


def workspace_members(config: KilnConfig, root: Path) -> frozenset[str]:
    """The normalized `[project] name` of each package under `config.packages`."""
    found: set[str] = set()
    for package in config.packages:
        path = root / package / "pyproject.toml"
        if not path.exists():
            continue
        name = DictUtils.get_mapping(DocumentUtils.read(path), "project").get("name")
        if isinstance(name, str):
            found.add(distribution(name))
    return frozenset(found)


def published_dependencies(document: dict[str, object]) -> list[str]:
    """Runtime and optional-dependency requirements — what a wheel carries."""
    found = list(runtime_dependencies(document))
    optional = DictUtils.get_mapping(document, "project.optional-dependencies")
    for group in optional.values():
        found.extend(ListUtils.as_strings(group))
    return found


def group_dependencies(document: dict[str, object]) -> list[str]:
    """Every dependency-group requirement, flattened."""
    found: list[str] = []
    for group in DictUtils.get_mapping(document, "dependency-groups").values():
        found.extend(ListUtils.as_strings(group))
    return found


def every_dependency(document: dict[str, object]) -> list[str]:
    """Published and dependency-group requirements, flattened.

    A dependency group is still a dependency: a kit that a repo installs only
    to develop with is exactly the coupling kiln ADR-0002 is about.
    """
    return [*published_dependencies(document), *group_dependencies(document)]


def _check_kiln_not_in_lock(label: str, document: dict[str, object]) -> list[Finding]:
    """`rn-forge-kiln` in any dependency list puts kiln's own tree in the lock."""
    lists: dict[str, list[str]] = {
        "dependencies": runtime_dependencies(document),
        **{
            f"optional-dependencies.{name}": ListUtils.as_strings(group)
            for name, group in DictUtils.get_mapping(
                document, "project.optional-dependencies"
            ).items()
        },
        **{
            f"dependency-groups.{name}": ListUtils.as_strings(group)
            for name, group in DictUtils.get_mapping(
                document, "dependency-groups"
            ).items()
        },
    }
    return [
        Finding(
            f"{CODE}.kiln-in-lock",
            Severity.ERROR,
            f"{KILN} is in {group}; kiln runs from [kiln] ref (F7.4), so remove it",
            path=label,
        )
        for group, requirements in lists.items()
        if any(distribution(r) == KILN for r in requirements)
    ]


def _check_allowed(
    label: str,
    document: dict[str, object],
    allowed: tuple[str, ...],
    members: frozenset[str],
) -> list[Finding]:
    permitted = {name.lower() for name in allowed} | members
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


def _check_source(
    label: str, document: dict[str, object], members: frozenset[str]
) -> tuple[list[Finding], bool]:
    """Every rn-forge requirement carries a pinned source or a bounded range.

    Returns the findings, and whether an accepted range named a distribution
    outside *members*, which is the case that needs the index.
    """
    findings: list[Finding] = []
    needs_index = False
    published = published_dependencies(document)
    grouped = [
        r for r in group_dependencies(document) if distribution(r) not in members
    ]
    for requirement in (*published, *grouped):
        name = distribution(requirement)
        if not governed(name):
            continue
        url = requirement.partition(" @ ")[2].strip()
        if url:
            if not PINNED_GIT_URL.match(url):
                findings.append(
                    Finding(
                        f"{CODE}.unpinned",
                        Severity.ERROR,
                        f"`{name}` resolves to {url!r}, which names no tag or rev "
                        f"— pin it, or the build changes without the repo changing",
                        path=label,
                    )
                )
            continue
        spec = _specifier(requirement)
        if spec and _has_ceiling(spec):
            needs_index = needs_index or name not in members
        elif spec:
            findings.append(
                Finding(
                    f"{CODE}.no-ceiling",
                    Severity.ERROR,
                    f"`{name}` is declared as {spec!r}, which has no ceiling — "
                    f"add the next breaking version, e.g. <0.8 (kiln ADR-0018)",
                    path=label,
                )
            )
        else:
            findings.append(
                Finding(
                    f"{CODE}.not-direct",
                    Severity.ERROR,
                    f"`{name}` is declared without a direct URL or a version "
                    f"range — a [tool.uv.sources] override does not survive into "
                    f"a built wheel, so a consumer of this package could not "
                    f"resolve it",
                    path=label,
                )
            )
    return findings, needs_index


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


def _is_workspace_source(name: str, source: object, members: frozenset[str]) -> bool:
    return (
        distribution(name) in members
        and isinstance(source, dict)
        and cast("dict[str, object]", source).get("workspace") is True
    )


def _check_no_shadowing_source(
    label: str, document: dict[str, object], members: frozenset[str]
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
        for name, source in DictUtils.get_mapping(document, "tool.uv.sources").items()
        if governed(name) and not _is_workspace_source(name, source, members)
    ]


def _declares_index(document: dict[str, object]) -> bool:
    """Whether `[[tool.uv.index]]` lists pykit's index."""
    return any(
        DictUtils.as_mapping(entry).get("url") == archetypes.PYKIT_INDEX
        for entry in DictUtils.get_list(document, "tool.uv.index")
    )


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Hold every `pyproject.toml` in the repo to the archetype's contract."""
    archetype = archetypes.for_config(config)

    findings: list[Finding] = []
    declared: set[str] = set()
    members = workspace_members(config, root)
    needs_index = False
    root_document: dict[str, object] = {}

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
        document = DocumentUtils.read(path)
        findings.extend(
            _check_allowed(
                label, document, tuple(archetype.dependencies.allowed), members
            )
        )
        findings.extend(_check_kiln_not_in_lock(label, document))
        source_findings, ranged = _check_source(label, document, members)
        findings.extend(source_findings)
        needs_index = needs_index or ranged
        if relative == Path("pyproject.toml"):
            root_document = document
        findings.extend(_check_no_shadowing_source(label, document, members))
        findings.extend(_check_no_codegen_in_runtime(label, document))
        declared.update(distribution(r) for r in runtime_dependencies(document))

    if needs_index and not _declares_index(root_document):
        findings.append(
            Finding(
                f"{CODE}.no-index",
                Severity.ERROR,
                f"an rn-forge requirement is a version range, and no "
                f"[[tool.uv.index]] names {archetypes.PYKIT_INDEX} — add it as "
                f'name = "rn-forge" (kiln ADR-0018)',
                path="pyproject.toml",
            )
        )

    if config.archetype == "python-lib" and not config.packages:
        return findings

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
