"""`release-evidence` fails when the newest shipped release has no `security.md`."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import run_check

from rn_forge.kiln.modules.docs.checks import evidence

SWITCH = "\n[ci.checks]\nrelease-evidence = true\n"
SHIPPED = "# Release {n}\n\n|  |  |\n| -- | -- |\n| **Status** | {status} |\n"


def _root(repo, statuses: dict[int, str], on: bool = True, **files: str) -> Path:
    pages = {
        f"docs__releases__release-{n}__index.md": SHIPPED.format(n=n, status=s)
        + ("| **Finish Date** | 2026-02-02 |\n" if s == "shipped" else "")
        for n, s in statuses.items()
    }
    return repo(
        archetype="python-tool",
        docs="mkdocs",
        tail=SWITCH if on else "",
        **pages,
        **files,
    )


def test_newest_shipped_release_without_evidence_fails(repo) -> None:
    root = _root(repo, {1: "shipped", 2: "shipped", 3: "planned"})
    findings = run_check(evidence.NAME, root)
    assert [(f.code, f.path) for f in findings] == [
        ("docs.release-evidence-missing", "docs/releases/release-2/index.md")
    ]
    assert "release-2" in findings[0].message


def test_older_releases_need_no_evidence(repo) -> None:
    root = _root(
        repo,
        {1: "shipped", 2: "shipped"},
        **{"docs__releases__release-2__security.md": "# Security\n"},
    )
    assert run_check(evidence.NAME, root) == []


def test_evidence_check_is_off_by_default(repo) -> None:
    root = _root(repo, {1: "shipped"}, on=False)
    assert run_check(evidence.NAME, root) == []


def test_no_shipped_release_needs_no_evidence(repo) -> None:
    root = _root(repo, {1: "planned", 2: "in progress"})
    assert run_check(evidence.NAME, root) == []
