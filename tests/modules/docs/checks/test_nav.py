"""`docs-nav` fails when `mkdocs.yml`'s generated nav is stale."""

from __future__ import annotations

from rn_forge.kiln import checks
from rn_forge.kiln.modules.docs.checks import nav

MKDOCS = """\
site_name: example
nav:
  # BEGIN generated nav
  - Home: index.md
  # END generated nav
"""


def _site(repo, **extra: str):
    return repo(
        docs="mkdocs",
        **{
            "mkdocs.yml": MKDOCS,
            "docs/index.md": "# Example\n",
            "docs/_areas.yml": "areas:\n  - key: guides\n",
            "docs/guides/index.md": "# Guides\n",
            **extra,
        },
    )


def test_a_stale_nav_is_a_finding(repo) -> None:
    findings = checks.run(_site(repo), only=nav.NAME)
    assert [f.code for f in findings] == ["docs.nav-stale"]


def test_a_repo_without_an_mkdocs_site_is_not_checked(repo) -> None:
    assert checks.run(repo(docs="none"), only=nav.NAME) == []
