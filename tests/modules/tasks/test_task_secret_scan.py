"""`task ci:secret-scan`."""

from __future__ import annotations
import json
import pytest
from pathlib import Path
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.modules.core import cycle
from typing import cast
from tests.modules.tasks.support import (
    SIX_ARCHETYPES,
    _ci_rendered,
    _root,
    _secrets_root,
)


def _gitleaks_pin() -> dict[str, dict[str, str]]:
    from rn_forge.kiln.modules.cicd.artifacts import load_pins

    return cast("dict[str, dict[str, str]]", load_pins()["gitleaks"])


@pytest.mark.parametrize("archetype", SIX_ARCHETYPES)
def test_s15_3_2_1_task_renders_for_every_archetype(
    tmp_path: Path, archetype: str
) -> None:
    tasks = _ci_rendered(_secrets_root(tmp_path, archetype))
    assert tasks["secret-scan"]["cmds"] == [
        {"task": "secrets:install"},
        ".rn-forge/kiln/rendered/bin/gitleaks detect --source . --redact "
        "--no-banner --exit-code 1",
    ]
    assert "internal" not in tasks["secret-scan"]
    assert tasks["secrets:install"]["internal"] is True


def test_s15_3_2_2_install_verifies_the_sha(tmp_path: Path) -> None:
    install = _ci_rendered(_secrets_root(tmp_path, "python-tool"))["secrets:install"]
    assert install["status"] == ["test -x .rn-forge/kiln/rendered/bin/gitleaks"]
    (script,) = install["cmds"]
    pin = _gitleaks_pin()
    for uname, platform in (
        ("Linux-x86_64", "linux_x64"),
        ("Darwin-arm64", "darwin_arm64"),
    ):
        assert f"{uname})" in script
        assert pin[platform]["url"] in script
        assert pin[platform]["sha256"] in script
    assert 'platform="$(uname -s)-$(uname -m)"' in script
    assert 'curl -fsSL "$url"' in script
    assert "shasum -a 256 -c" in script
    assert "-C .rn-forge/kiln/rendered/bin gitleaks" in script
    assert 'echo "unsupported platform: $platform" >&2' in script
    assert script.index("unsupported platform") < script.index("curl")
    assert script.index("shasum -a 256 -c") < script.index("tar -xzf")


@pytest.mark.parametrize("archetype", SIX_ARCHETYPES)
def test_s15_3_2_3_off(tmp_path: Path, archetype: str) -> None:
    on_dir, off_dir = tmp_path / "on", tmp_path / "off"
    on_dir.mkdir()
    off_dir.mkdir()
    on = _secrets_root(on_dir, archetype)
    off = _secrets_root(off_dir, archetype, "\n[ci.checks]\nsecret-scan = false\n")
    tasks = _ci_rendered(off)
    assert "secret-scan" not in tasks
    assert "secrets:install" not in tasks
    assert "gitleaks" not in (off / "tasks/ci.yml").read_text(encoding="utf-8")
    on_lint = YamlUtils.load((on / "Taskfile.yml").read_text(encoding="utf-8"))
    off_lint = YamlUtils.load((off / "Taskfile.yml").read_text(encoding="utf-8"))
    assert on_lint["tasks"]["lint"] == off_lint["tasks"]["lint"]
    assert "secrets" not in json.dumps(off_lint["tasks"]["lint"])


def test_s15_4_2_1_task(tmp_path: Path) -> None:
    tasks = _ci_rendered(_applied(tmp_path / "lib", "python-lib"))
    assert tasks["internal-ranges"]["cmds"] == ["{{.DEVOPS}} requirements"]
    for archetype in ("python-tool", "python-app"):
        other = _ci_rendered(_applied(tmp_path / archetype, archetype))
        assert "internal-ranges" not in other


def test_s15_4_3_8_node_task(tmp_path: Path) -> None:
    tasks = _ci_rendered(_applied(tmp_path / "lib", "node-lib"))
    assert tasks["internal-ranges"]["cmds"] == [
        "set -o pipefail; pnpm ls -r --depth -1 --json"
        " | {{.DEVOPS}} requirements --stack node"
    ]
    assert {"task": "internal-ranges"} in tasks["validate"]["cmds"]
    for archetype in ("python-lib", "python-tool", "python-app"):
        other = _ci_rendered(_applied(tmp_path / archetype, archetype))
        assert {"task": "internal-ranges"} not in other.get("validate", {}).get(
            "cmds", []
        )


def _applied(tmp_path: Path, archetype: str) -> Path:
    tmp_path.mkdir()
    root = _root(tmp_path, archetype)
    cycle.apply(root, home=tmp_path / "home")
    return root
