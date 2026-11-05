"""The check registry: every CI check kiln renders, validates and documents."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from rn_forge.commons.lang.models import StrictModel

from rn_forge.kiln.modules.cicd.config import CiConfig, LicensePolicy

__all__ = [
    "CHECKS",
    "COLUMNS",
    "CiCheck",
    "Switch",
    "configured_names",
    "enabled",
    "for_archetype",
    "render_matrix",
]


class Switch(StrEnum):
    """How a check is turned on."""

    STANDARD = "standard"
    DERIVED = "derived"
    CONFIGURED = "configured"


@dataclass(frozen=True)
class CiCheck:
    """One row of the checks matrix."""

    name: str
    verb: str | None
    archetypes: frozenset[str]
    switch: Switch
    key_note: str
    default: bool = True
    cells: Mapping[str, str] = field(default_factory=dict[str, str])
    job: str | None = None
    gates: bool = False
    policy: type[StrictModel] | None = None


COLUMNS: tuple[tuple[str, str], ...] = (
    ("lib", "python-lib"),
    ("tool", "python-tool"),
    ("app", "python-app"),
    ("web-api", "python-web-api"),
    ("web-app", "python-web-app"),
    ("node-lib", "node-lib"),
)
"""The matrix's archetype columns: heading, archetype name."""

_ALL = frozenset(archetype for _, archetype in COLUMNS)
_PY = _ALL - {"node-lib"}
_CODE_NAMES = frozenset(
    {
        "lint-imports",
        "kiln doctor",
        "pip-audit",
        "pnpm-audit",
        "dependency-review",
        "verify-release",
        "ci-ok",
        "licenses",
        "secret-scan",
        "internal-ranges",
        "umbrella-release",
        "scorecard",
    }
)
_PLAIN_VERBS = frozenset({"action", "none"})


def _lib(*extra: str) -> frozenset[str]:
    return frozenset({"python-lib", *extra})


def _std(
    name: str,
    verb: str | None,
    archetypes: frozenset[str],
    note: str = "S",
    **cells: str,
) -> CiCheck:
    by_archetype = {
        dict(COLUMNS)[column.replace("_", "-")]: cell for column, cell in cells.items()
    }
    return CiCheck(name, verb, archetypes, Switch.STANDARD, note, cells=by_archetype)


CHECKS: tuple[CiCheck, ...] = (
    _std("ruff check and format", "lint", _PY),
    _std("pyright strict", "typecheck", _PY, lib="test"),
    _std("lint-imports", "lint", _PY),
    _std("Markdown and TOML formatting", "lint", _ALL),
    _std(
        "kiln doctor",
        "lint",
        _ALL,
        "S; `--full` per `[ci] doctor_full`, default `default-branch`",
    ),
    _std("zizmor, actionlint", "lint", _ALL),
    _std("pip-audit", "lint", _PY, "S; ignore list `[tasks.audit] ignore`"),
    _std("pnpm-audit", "{stack}:lint:audit", frozenset({"node-lib"})),
    _std(
        "Nx lint, typecheck, test, build",
        "`task node:*`, `task ci:affected`",
        frozenset({"python-web-app", "node-lib"}),
    ),
    _std("pytest", "test", _PY, lib="test"),
    CiCheck(
        "Services, smoke, suites",
        "ci:*",
        _lib(),
        Switch.STANDARD,
        "D: a package declares them",
    ),
    _std("Adapters check", "ci:adapters", _lib()),
    CiCheck(
        "Docs strict build",
        "docs:build",
        _ALL,
        Switch.STANDARD,
        'D: `[docs] profile = "mkdocs"`',
    ),
    _std("dependency-review", "action", _ALL),
    CiCheck(
        "Sonar",
        "`sonar` job",
        _ALL,
        Switch.STANDARD,
        "C: `[ci] sonar`, default `true`",
    ),
    CiCheck(
        "Release",
        "`release` job",
        _ALL,
        Switch.STANDARD,
        "C: `[ci] release`, default `tag-exists`; `pypi` for `python-lib`; "
        "`nx-dispatch` for `node-lib`; `none`",
        cells={"node-lib": "`release.yml`"},
    ),
    CiCheck(
        "verify-release",
        "ci:verify-release",
        _PY,
        Switch.STANDARD,
        "D: a release mode other than `none`",
    ),
    CiCheck(
        "Docs deploy",
        "`docs` job or `docs.yml`",
        _ALL,
        Switch.STANDARD,
        'D: `[docs] profile = "mkdocs"`',
        cells={
            "python-lib": "`ci.yml`",
            "python-tool": "`docs.yml`",
            "python-app": "`docs.yml`",
            "python-web-api": "`docs.yml`",
            "python-web-app": "`docs.yml`",
            "node-lib": "`ci.yml`",
        },
    ),
    _std("Package tarballs", "ci:package", frozenset({"node-lib"})),
    _std("ci-ok", None, _ALL),
    CiCheck(
        "licenses",
        "{stack}:lint:licenses",
        _ALL,
        Switch.CONFIGURED,
        "C: `[ci.checks] licenses`, default `true`; a table sets `deny` and `ignore`",
        policy=LicensePolicy,
    ),
    CiCheck(
        "secret-scan",
        "ci:lint:secrets",
        _ALL,
        Switch.CONFIGURED,
        "C: `[ci.checks] secret-scan`, default `true`",
        job="secret-scan",
        gates=True,
    ),
    CiCheck(
        "internal-ranges",
        "ci:requirements",
        frozenset({"python-lib", "node-lib"}),
        Switch.DERIVED,
        "D: two or more workspace members",
    ),
    CiCheck(
        "umbrella-release",
        "ci:release:umbrella",
        _ALL,
        Switch.CONFIGURED,
        "C: `[ci.checks] umbrella-release`, default `false`",
        default=False,
    ),
    CiCheck(
        "scorecard",
        None,
        _ALL,
        Switch.CONFIGURED,
        "C: `[ci.checks] scorecard`, default `false`; public repositories only",
        default=False,
        job="scorecard",
    ),
)
"""Every check, in the order the matrix lists them. Only the rows from `licenses`
on are switched by the registry; the earlier rows carry their page note."""


def configured_names() -> frozenset[str]:
    """The names a repository can switch in `[ci.checks]`."""
    return frozenset(c.name for c in CHECKS if c.switch is Switch.CONFIGURED)


def for_archetype(archetype: str) -> list[CiCheck]:
    """The checks *archetype* runs, in registry order."""
    return [c for c in CHECKS if archetype in c.archetypes]


def enabled(check: CiCheck, ci: CiConfig, archetype: str, members: int) -> bool:
    """Whether *check* runs for a repository of *archetype* with *members* packages."""
    if archetype not in check.archetypes:
        return False
    if check.switch is Switch.CONFIGURED:
        value = ci.checks.get(check.name, check.default)
        return True if isinstance(value, dict) else bool(value)
    if check.name == "internal-ranges":
        return archetype == "node-lib" or (archetype == "python-lib" and members >= 2)
    return True


def _name_cell(name: str) -> str:
    return f"`{name}`" if name in _CODE_NAMES else name


def _verb_cell(verb: str | None, stack: str) -> str:
    if verb is None:
        return "none"
    if "`" in verb or verb in _PLAIN_VERBS:
        return verb
    return f"`task {verb.format(stack=stack)}`"


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("--" for _ in header) + " |",
        *("| " + " | ".join(row) + " |" for row in rows),
    ]
    return "\n".join(lines)


def render_matrix(archetype: str | None) -> str:
    """The checks matrix as a Markdown table.

    Args:
        archetype: `None` for every archetype, one column each; or an archetype
            name for its rows only, with the verb's `{stack}` filled in.
    """
    if archetype is None:
        rows = [
            [
                _name_cell(c.name),
                _verb_cell(c.verb, "python"),
                *(
                    c.cells.get(a, "yes") if a in c.archetypes else ""
                    for _, a in COLUMNS
                ),
                c.key_note,
            ]
            for c in CHECKS
        ]
        header = ["Check", "Verb", *(h for h, _ in COLUMNS), "Switch and key"]
        return _table(header, rows)
    stack = "node" if archetype == "node-lib" else "python"
    rows = [
        [_name_cell(c.name), _verb_cell(c.verb, stack), c.key_note]
        for c in for_archetype(archetype)
    ]
    return _table(["Check", "Verb", "Switch and key"], rows)
