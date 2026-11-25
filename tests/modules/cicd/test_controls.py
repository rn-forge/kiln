"""The security control catalog."""

from __future__ import annotations

from rn_forge.kiln.modules.cicd import controls, registry

ALL = (
    "python-lib",
    "python-tool",
    "python-app",
    "python-web-api",
    "python-web-app",
    "node-lib",
)


def _cell(archetype: str, name: str) -> str:
    for line in controls.render_catalog(archetype).splitlines()[2:]:
        cell = line.strip("|").split(" | ")[0].strip()
        if cell == name or cell.startswith(f"{name} ("):
            return cell
    raise AssertionError(name)


def test_every_security_check_has_a_control() -> None:
    for c in registry.CHECKS:
        if c.security:
            assert any(c.name in k.checks for k in controls.CONTROLS), c.name


def test_control_checks_are_security_checks() -> None:
    security = {c.name for c in registry.CHECKS if c.security}
    for control in controls.CONTROLS:
        assert set(control.checks) <= security, control.name


def test_control_names_are_unique() -> None:
    names = [c.name for c in controls.CONTROLS]
    assert len(names) == len(set(names))


def test_catalog_lists_every_control_in_order() -> None:
    lines = controls.render_catalog("node-lib").splitlines()
    assert lines[0] == "| Control | Effect | Result from | Evidence |"
    assert len(lines) == 2 + len(controls.CONTROLS)
    for line, control in zip(lines[2:], controls.CONTROLS, strict=True):
        assert line.startswith(f"| {control.name}")
        assert line.count("|") == 5


def test_catalog_names_only_the_archetypes_checks() -> None:
    audit = "Dependency audit"
    assert (
        _cell("python-web-app", audit) == "Dependency audit (`pip-audit`, `pnpm-audit`)"
    )
    assert _cell("node-lib", audit) == "Dependency audit (`pnpm-audit`)"
    assert "pip-audit" not in controls.render_catalog("node-lib")
    assert _cell("python-tool", "Source scan") == "Source scan (ruff check and format)"
    for archetype in ALL:
        assert _cell(archetype, "Push protection") == "Push protection"
