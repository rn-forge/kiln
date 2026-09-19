"""The dependency contract fails when it should.

A lint that has never rejected anything is a lint nobody has tested. Ported
from `tests/test_rn_forge_deps.py`, which ran the golden repo's committed
`check_rn_forge_deps.py` as a subprocess; the rules and their fixtures are the
same, and the check is now called directly (kiln ADR-0006).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rn_forge.kiln import checks

BASE_URL = "git+https://github.com/rn-forge/pykit@feature/upgrade"


def pinned(distribution: str) -> str:
    return f"{distribution} @ {BASE_URL}#subdirectory=packages/{distribution}"


# The python-tool archetype's whole required set — the fixtures below are
# checked as that archetype, so one missing any of the three would be testing
# the `required` rule rather than the one it means to.
REQUIRED_URLS = [
    pinned("rn-forge-commons"),
    pinned("rn-forge-cli"),
    pinned("rn-forge-tooling"),
]
PINNED_URL = REQUIRED_URLS[0]
UNPINNED_URL = (
    "rn-forge-commons @ git+https://github.com/rn-forge/pykit"
    "#subdirectory=packages/rn-forge-commons"
)
REQUIRED_BLOCK = ", ".join(f'"{url}"' for url in REQUIRED_URLS)

COMPLIANT = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = [{REQUIRED_BLOCK}]
"""

MISSING_REQUIRED = """
[project]
name = "example"
version = "0.1.0"
dependencies = []
"""

FORBIDDEN_KIT = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = [{REQUIRED_BLOCK}]

[dependency-groups]
dev = ["rn-forge-agentkit>=0.6.0"]
"""

UNPINNED = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = ["{UNPINNED_URL}", "{REQUIRED_URLS[1]}", "{REQUIRED_URLS[2]}"]
"""

# The exact shape ADR-0005 rejects: resolvable in the workspace, unresolvable
# for anyone who installs the built wheel.
SOURCE_OVERRIDE_ONLY = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = ["rn-forge-commons>=0.2.2", "{REQUIRED_URLS[1]}", "{REQUIRED_URLS[2]}"]

[tool.uv.sources]
rn-forge-commons = {{ git = "https://github.com/rn-forge/pykit", subdirectory = "packages/rn-forge-commons", tag = "rn-forge-commons-v0.2.2" }}
"""

EXTRA_ON_ALLOWED = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = [
  "rn-forge-commons[excel] @ {PINNED_URL.partition(" @ ")[2]}",
  "{REQUIRED_URLS[1]}",
  "{REQUIRED_URLS[2]}",
]
"""

# How a golden takes kiln: a dev dependency, from a path source.
KILN_FROM_PATH = f"""
[project]
name = "example"
version = "0.1.0"
dependencies = [{REQUIRED_BLOCK}]

[dependency-groups]
dev = ["rn-forge-kiln"]

[tool.uv.sources]
rn-forge-kiln = {{ path = "../kiln", editable = true }}
"""


def run(root: Path) -> list[str]:
    return [str(f) for f in checks.run(root, only="rn-forge-deps")]


WEB_REQUIRED_URLS = [
    pinned("rn-forge-commons"),
    pinned("rn-forge-cli"),
    pinned("rn-forge-web"),
    pinned("rn-forge-fastapi"),
]
WEB_REQUIRED_BLOCK = ", ".join(f'"{url}"' for url in WEB_REQUIRED_URLS)

WEB_COMPLIANT = f"""
[project]
name = "demo-api"
version = "0.1.0"
dependencies = [{WEB_REQUIRED_BLOCK}]
"""

WEB_MISSING_WEB = f"""
[project]
name = "demo-api"
version = "0.1.0"
dependencies = ["{WEB_REQUIRED_URLS[0]}", "{WEB_REQUIRED_URLS[1]}", "{WEB_REQUIRED_URLS[3]}"]
"""

WEB_OTHER_FRAMEWORK = f"""
[project]
name = "demo-api"
version = "0.1.0"
dependencies = [{WEB_REQUIRED_BLOCK}, "{pinned("rn-forge-django")}"]
"""

WEB_CODEGEN_RUNTIME = f"""
[project]
name = "demo-api"
version = "0.1.0"
dependencies = [
  "{WEB_REQUIRED_URLS[0]}",
  "{WEB_REQUIRED_URLS[1]}",
  "{WEB_REQUIRED_URLS[2]}",
  "rn-forge-fastapi[codegen] @ {WEB_REQUIRED_URLS[3].partition(" @ ")[2]}",
]
"""

WEB_CODEGEN_DEV_GROUP = f"""
[project]
name = "demo-api"
version = "0.1.0"
dependencies = [{WEB_REQUIRED_BLOCK}]

[dependency-groups]
dev = ["rn-forge-fastapi[codegen] @ {WEB_REQUIRED_URLS[3].partition(" @ ")[2]}"]
"""


def _web_root(tmp_path: Path, pyproject: str) -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "schema_version = 1\n\n"
        "[repository]\n"
        'name = "demo"\n'
        'archetype = "python-web-api"\n\n'
        '[archetype."python-web-api"]\n'
        'backend = "fastapi"\n',
        encoding="utf-8",
    )
    member = tmp_path / "apps" / "api" / "pyproject.toml"
    member.parent.mkdir(parents=True, exist_ok=True)
    member.write_text(pyproject, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.uv]\npackage = false\n[project]\nname = "demo"\n', encoding="utf-8"
    )
    return tmp_path


def test_s5_1_1_2_a_compliant_web_member_passes(tmp_path: Path) -> None:
    assert run(_web_root(tmp_path, WEB_COMPLIANT)) == []


def test_s5_1_1_2_a_member_lacking_rn_forge_web_is_refused(tmp_path: Path) -> None:
    reported = run(_web_root(tmp_path, WEB_MISSING_WEB))
    assert any("rn-forge-web" in line for line in reported)


def test_s5_1_1_2_a_member_naming_the_other_framework_is_refused(
    tmp_path: Path,
) -> None:
    reported = run(_web_root(tmp_path, WEB_OTHER_FRAMEWORK))
    assert any(
        "rn-forge-django" in line and "not in this archetype" in line
        for line in reported
    )


def test_s5_1_1_2_codegen_extra_in_runtime_dependencies_is_refused(
    tmp_path: Path,
) -> None:
    reported = run(_web_root(tmp_path, WEB_CODEGEN_RUNTIME))
    assert any("[codegen]" in line for line in reported)


def test_s5_1_1_2_codegen_extra_in_a_dev_group_is_accepted(tmp_path: Path) -> None:
    assert run(_web_root(tmp_path, WEB_CODEGEN_DEV_GROUP)) == []


def test_a_compliant_repo_passes(repo) -> None:
    assert run(repo(lifecycle=True, **{"pyproject.toml": COMPLIANT})) == []


def test_an_extra_on_an_allowed_distribution_is_still_allowed(repo) -> None:
    """`rn-forge-commons[excel]` is the same distribution, not a different one."""
    assert run(repo(lifecycle=True, **{"pyproject.toml": EXTRA_ON_ALLOWED})) == []


@pytest.mark.parametrize(
    ("pyproject", "expected"),
    [
        (MISSING_REQUIRED, "requires a dependency on `rn-forge-commons`"),
        (FORBIDDEN_KIT, "not in this archetype's allowed set"),
        (UNPINNED, "names no tag or rev"),
        (SOURCE_OVERRIDE_ONLY, "does not survive into a built wheel"),
    ],
    ids=["required", "allowed", "pinned", "source-override"],
)
def test_each_rule_rejects_its_violation(repo, pyproject: str, expected: str) -> None:
    reported = run(repo(lifecycle=True, **{"pyproject.toml": pyproject}))
    assert reported, "the rule accepted its own violation"
    assert any(expected in line for line in reported)
    assert all("pyproject.toml" in line for line in reported)


def test_a_missing_pyproject_is_a_finding(repo) -> None:
    reported = run(repo())
    assert any("not found" in line and "pyproject.toml" in line for line in reported)


def test_the_tool_alias_and_the_flag_reach_the_same_set(repo, tmp_path: Path) -> None:
    """`python-tool` is `python-app` + `lifecycle = true` (kiln ADR-0005)."""
    aliased = repo(archetype="python-tool", **{"pyproject.toml": COMPLIANT})
    assert run(aliased) == []


def test_an_app_may_not_take_the_tooling_layer(repo) -> None:
    """Without the flag, `rn-forge-tooling` is a layer nothing imports."""
    reported = run(repo(**{"pyproject.toml": COMPLIANT}))
    assert any("rn-forge-tooling" in line for line in reported)


def test_kiln_itself_is_outside_the_contract(repo) -> None:
    """kiln is the dev tool running the check; doctor's `kiln.pin` owns its source."""
    assert run(repo(lifecycle=True, **{"pyproject.toml": KILN_FROM_PATH})) == []
