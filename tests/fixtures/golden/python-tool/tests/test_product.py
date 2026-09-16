from rn_forge.commons.findings import Severity
from rn_forge.tooling.install import Link, ToolHome

from golden_tool.product import PRODUCT


def test_the_one_artifact_is_the_command_on_path():
    assert PRODUCT.artifacts() == (Link("bin/golden-tool", "bin/golden-tool"),)


def test_the_one_check_reports_the_home(tmp_path):
    (check,) = PRODUCT.checks()
    (finding,) = check(ToolHome("golden-tool", tmp_path))
    assert finding.code == "golden-tool.home"
    assert finding.severity is Severity.INFO
