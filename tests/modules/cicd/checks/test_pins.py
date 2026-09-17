"""S4.3.4 — `ci-pins`: SHA-pinned actions, and a `permissions:` key on every job."""

from __future__ import annotations

from pathlib import Path

from rn_forge.kiln import checks

PINNED = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1"


def _codes(root: Path) -> list[str]:
    return sorted(f.code for f in checks.run(root, only="ci-pins"))


def test_s4_3_4_a_pinned_workflow_with_permissions_passes(repo) -> None:
    body = f"jobs:\n  a:\n    permissions:\n      contents: read\n    steps:\n      - uses: {PINNED}\n      - uses: ./.github/actions/setup\n"
    assert _codes(repo(**{".github__workflows__ci.yml": body})) == []


def test_s4_3_4_a_tag_ref_is_unpinned(repo) -> None:
    body = "jobs:\n  a:\n    permissions: {}\n    steps:\n      - uses: actions/checkout@v4 # v4\n"
    assert _codes(repo(**{".github__workflows__ci.yml": body})) == ["ci.unpinned"]


def test_s4_3_4_a_job_without_permissions_is_reported(repo) -> None:
    body = f"jobs:\n  a:\n    steps:\n      - uses: {PINNED}\n"
    assert _codes(repo(**{".github__workflows__ci.yml": body})) == ["ci.permissions"]


def test_s4_3_4_an_action_is_checked_for_pins(repo) -> None:
    body = "runs:\n  using: composite\n  steps:\n    - uses: astral-sh/setup-uv@main\n"
    assert _codes(repo(**{".github__actions__setup__action.yml": body})) == [
        "ci.unpinned"
    ]
