"""`docs-generate` fails when `mkdocs.yml`'s derived nav is stale."""

from __future__ import annotations

from rn_forge.kiln import checks
from rn_forge.kiln.modules.docs.checks import derived

MKDOCS = """\
site_name: example
nav:
  # BEGIN derived nav
  - Home: index.md
  # END derived nav
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


def test_s13_1_1_1_a_stale_nav_is_a_finding(repo) -> None:
    findings = checks.run(_site(repo), only=derived.NAME)
    assert [f.code for f in findings] == ["docs.nav-stale"]
    assert "task docs:generate" in findings[0].message


def test_s13_1_1_1_a_repo_without_an_mkdocs_site_is_not_checked(repo) -> None:
    assert checks.run(repo(docs="none"), only=derived.NAME) == []
