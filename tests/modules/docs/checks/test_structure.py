"""`docs-structure` holds a repo's docs tree to kiln's policy.

The mechanism is covered in `tests/modules/docs/test_docs.py`; this proves the
check reaches it, and that kiln's own docs pass the policy kiln ships.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.kiln import checks
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.checks import structure

ROOT = Path(__file__).resolve().parents[4]


def test_kiln_docs_pass_the_policy() -> None:
    assert [str(f) for f in checks.run(ROOT, only=structure.NAME)] == []


def test_a_repo_without_an_mkdocs_site_is_not_checked(repo) -> None:
    root = repo(docs="none")
    assert structure.check(KilnConfig.load(root), root) == []
