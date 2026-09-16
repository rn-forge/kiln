"""The committed-state baseline fails when it should.

One test per rule `check_generated.py` enforced: the three artifact kinds, and
the three ways `state.json` itself can be wrong.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.kiln import checks
from rn_forge.kiln.modules.core.checks.generated import digest

BEGIN = "<!-- BEGIN rn-forge kiln -->"
END = "<!-- END rn-forge kiln -->"


def run(root: Path) -> list[str]:
    return [str(f) for f in checks.run(root, only="generated")]


def managed_entry(path: str, content: str) -> dict[str, object]:
    return {
        "path": path,
        "kind": "managed",
        "content_hash": digest(content),
    }


def block_entry(path: str, body: str) -> dict[str, object]:
    return {
        "path": path,
        "kind": "block",
        "begin_marker": BEGIN,
        "end_marker": END,
        "content_hash": digest(body),
    }


def test_a_matching_tree_passes(repo, write_state) -> None:
    root = repo(
        **{".editorconfig": "root = true\n", "CLAUDE.md": f"body\n{BEGIN}\nx\n{END}\n"}
    )
    write_state(
        {
            ".editorconfig": managed_entry(".editorconfig", "root = true\n"),
            "CLAUDE.md#rn-forge kiln": block_entry("CLAUDE.md", "x\n"),
            "README.md": {"path": "README.md", "kind": "seeded"},
        }
    )
    (root / "README.md").write_text("anything at all\n", encoding="utf-8")
    assert run(root) == []


def test_a_managed_file_that_drifted_is_reported(repo, write_state) -> None:
    root = repo(**{".editorconfig": "edited by hand\n"})
    write_state({".editorconfig": managed_entry(".editorconfig", "root = true\n")})
    reported = run(root)
    assert any("has drifted" in line and ".editorconfig" in line for line in reported)


def test_a_missing_managed_file_is_reported(repo, write_state) -> None:
    root = repo()
    write_state({".editorconfig": managed_entry(".editorconfig", "root = true\n")})
    assert any("managed artifact is missing" in line for line in run(root))


def test_a_missing_block_is_reported(repo, write_state) -> None:
    root = repo(**{"CLAUDE.md": "body with no fence\n"})
    write_state({"CLAUDE.md#rn-forge kiln": block_entry("CLAUDE.md", "x\n")})
    assert any("managed block" in line and "missing" in line for line in run(root))


def test_a_drifted_block_is_reported(repo, write_state) -> None:
    root = repo(**{"CLAUDE.md": f"body\n{BEGIN}\nedited\n{END}\n"})
    write_state({"CLAUDE.md#rn-forge kiln": block_entry("CLAUDE.md", "x\n")})
    assert any("has drifted" in line for line in run(root))


def test_an_indented_block_marker_still_matches(repo, write_state) -> None:
    """mkdocs.yml's nav block is indented; the markers compare stripped."""
    root = repo(**{"mkdocs.yml": f"nav:\n  {BEGIN}\n  - a\n  {END}\n"})
    write_state({"mkdocs.yml#rn-forge kiln": block_entry("mkdocs.yml", "  - a\n")})
    assert run(root) == []


def test_a_missing_seeded_file_is_reported(repo, write_state) -> None:
    root = repo()
    write_state({"README.md": {"path": "README.md", "kind": "seeded"}})
    assert any("seeded artifact is missing" in line for line in run(root))


def test_state_that_hashes_itself_is_reported(repo, write_state) -> None:
    root = repo()
    write_state(
        {
            "self": {
                "path": ".rn-forge/kiln/state.json",
                "kind": "managed",
                "content_hash": "0",
            }
        }
    )
    assert any("must not hash itself" in line for line in run(root))


def test_an_unknown_kind_is_reported(repo, write_state) -> None:
    root = repo()
    write_state({"x": {"path": "x", "kind": "conjured", "content_hash": "0"}})
    assert any("unknown kind" in line for line in run(root))


def test_an_unknown_schema_version_is_refused(repo, write_state) -> None:
    root = repo()
    write_state({}, schema_version="99")
    reported = run(root)
    assert any("99" in line and "schema_version" in line for line in reported)


def test_a_malformed_block_is_reported(repo, write_state) -> None:
    root = repo(**{"CLAUDE.md": f"body\n{BEGIN}\nx\n{BEGIN}\n{END}\n"})
    write_state({"CLAUDE.md#rn-forge kiln": block_entry("CLAUDE.md", "x\n")})
    assert any("malformed" in line for line in run(root))


def test_a_repo_with_no_state_is_not_a_kiln_repo(repo) -> None:
    assert any("not a kiln repo" in line for line in run(repo()))
