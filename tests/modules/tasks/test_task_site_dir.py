"""`[docs] site_dir` is honoured everywhere."""

from __future__ import annotations
import pytest
from pathlib import Path
from rn_forge.kiln.modules.core import cycle
from tests.modules.tasks.support import _load, _root


S16_7_1_WEB = """
schema_version = 1

[repository]
name = "demo"
owner = "rn-forge"
archetype = "python-web-app"

[docs]
profile = "mkdocs"
{site_dir}
[archetype."python-web-app"]
backend = "fastapi"
frontend = "angular"

[ci.hooks]
docs = ["./.github/actions/x"]
"""


S16_7_1_SKIP = (
    ".rn-forge/kiln/config.toml",
    ".rn-forge/kiln/backups",
    ".rn-forge/kiln/rendered",
    ".git",
)


def _s16_7_1_root(tmp_path: Path, archetype: str, site_dir: str) -> Path:
    line = f'site_dir = "{site_dir}"\n'
    if archetype == "python-web-app":
        config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text(S16_7_1_WEB.format(site_dir=line), encoding="utf-8")
        return tmp_path
    root = _root(tmp_path, archetype, extra=line)
    if archetype == "node-lib":
        config = root / ".rn-forge" / "kiln" / "config.toml"
        config.write_text(
            config.read_text(encoding="utf-8")
            + '\n[ci.hooks]\ndocs = ["./.github/actions/x"]\n',
            encoding="utf-8",
        )
    return root


@pytest.mark.parametrize(
    "archetype", ["python-tool", "python-lib", "node-lib", "python-web-app"]
)
def test_s16_7_1_1_no_default_literal_with_a_custom_site_dir(
    tmp_path: Path, archetype: str
) -> None:
    root = _s16_7_1_root(tmp_path, archetype, "out/site")
    cycle.apply(root, home=tmp_path / "home")
    leaks = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if not path.is_file() or any(
            rel == skip or rel.startswith(skip + "/") for skip in S16_7_1_SKIP
        ):
            continue
        if b".docs-site" in path.read_bytes():
            leaks.append(rel)
    assert leaks == []

    assert "out/site/" in _load(root, "tasks/docs.yml")["tasks"]["build"]["desc"]
    if archetype == "node-lib":
        site = _load(root, "tasks/ci.yml")["tasks"]["docs:site"]
        assert "{{.DEVOPS}} site-assemble out/site" in site["cmds"]
        assert "out/site" in site["desc"]
        text = (root / ".github/workflows/_docs.yml").read_text(encoding="utf-8")
        assert "path: out/site\n" in text
        steps = _load(root, ".github/workflows/_docs.yml")["jobs"]["docs"]["steps"]
        (hook,) = [s for s in steps if s.get("uses") == "./.github/actions/x"]
        assert hook["env"] == {"SITE_DIR": "out/site"}


def test_s16_7_1_3_empty_site_dir_means_mkdocs_default(tmp_path: Path) -> None:
    root = _s16_7_1_root(tmp_path, "node-lib", "")
    cycle.apply(root, home=tmp_path / "home")
    assert (
        "{{.DEVOPS}} site-assemble site"
        in _load(root, "tasks/ci.yml")["tasks"]["docs:site"]["cmds"]
    )
    assert "path: site\n" in (root / ".github/workflows/_docs.yml").read_text(
        encoding="utf-8"
    )
    assert "site/" in _load(root, "tasks/docs.yml")["tasks"]["build"]["desc"]
    assert ".docs-site" not in _load(root, "tasks/docs.yml")["tasks"]["build"]["desc"]
    assert "site_dir" not in (root / "mkdocs.yml").read_text(encoding="utf-8")


def test_s16_9_5_2_clean_removes_the_scratch_root(tmp_path: Path) -> None:
    root = _root(tmp_path / "default")
    cycle.apply(root, home=tmp_path / "home")
    cmds = _load(root, "tasks/workspace.yml")["tasks"]["clean"]["cmds"]
    assert any(c.startswith("rm -rf ") and ".tmp" in c.split() for c in cmds)

    custom = _root(
        tmp_path / "custom",
        extra='\n[tasks]\n[tasks.command_overrides]\n"workspace:clean" = "echo hi"\n',
    )
    cycle.apply(custom, home=tmp_path / "home")
    cmds = _load(custom, "tasks/workspace.yml")["tasks"]["clean"]["cmds"]
    assert cmds == ["echo hi"]
