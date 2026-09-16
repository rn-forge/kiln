"""S4.2.1 — the module contract and its registry."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from rn_forge.commons.exceptions import AppException

from rn_forge.kiln.modules.base import ModuleRegistry, Option
from rn_forge.kiln.modules.registry import builtin

PYRIGHT = Path(sys.executable).parent / "pyright"

STUB = """
from collections.abc import Sequence
from pathlib import Path

from rn_forge.commons.findings import Finding
from rn_forge.tooling.generation import Artifact

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.base import ModuleRegistry, Option


class Stub:
    name = "stub"
    section: str | None = None
    config_model = None

    def options(self) -> Sequence[Option]:
        return ()
{artifacts}
    def checks(self, config: KilnConfig, root: Path) -> Sequence[Finding]:
        return ()


ModuleRegistry([Stub()])
"""

ARTIFACTS = """
    def artifacts(self, config: KilnConfig, root: Path) -> Sequence[Artifact]:
        return ()
"""


class Stub:
    def __init__(self, name: str, *flags: str, section: str | None = None) -> None:
        self.name = name
        self.section = section
        self.config_model = None
        self._flags = flags

    def options(self) -> Sequence[Option]:
        return tuple(Option(flag, f"{self.name}.{flag}", "") for flag in self._flags)

    def artifacts(self, config, root):
        return ()

    def checks(self, config, root):
        return ()


def _pyright(tmp_path: Path, source: str) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "stub_module.py"
    path.write_text(source, encoding="utf-8")
    return subprocess.run(
        [str(PYRIGHT), "--pythonpath", sys.executable, str(path)],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )


def test_s4_2_1_a_stub_module_that_implements_the_contract_registers() -> None:
    registry = ModuleRegistry([Stub("stub", "flag")])
    assert [module.name for module in registry.modules] == ["stub"]


def test_s4_2_1_a_complete_stub_typechecks(tmp_path: Path) -> None:
    result = _pyright(tmp_path, STUB.format(artifacts=ARTIFACTS))
    assert result.returncode == 0, result.stdout


def test_s4_2_1_a_stub_missing_a_member_fails_typecheck(tmp_path: Path) -> None:
    result = _pyright(tmp_path, STUB.format(artifacts=""))
    assert result.returncode != 0
    assert '"artifacts" is not present' in result.stdout


def test_s4_2_1_two_modules_declaring_one_option_fail_naming_both_and_the_option() -> (
    None
):
    with pytest.raises(AppException) as caught:
        ModuleRegistry([Stub("left", "shared"), Stub("right", "own", "shared")])
    message = caught.value.message
    assert "'left'" in message and "'right'" in message and "--shared" in message


def test_s4_2_1_two_modules_claiming_one_section_fail() -> None:
    with pytest.raises(AppException, match=r"\[docs\]"):
        ModuleRegistry([Stub("left", section="docs"), Stub("right", section="docs")])


def test_s4_2_1_every_shipped_module_registers_without_a_collision() -> None:
    assert [module.name for module in builtin().modules] == [
        "core",
        "python",
        "docs",
        "tasks",
        "cicd",
        "instructions",
    ]
